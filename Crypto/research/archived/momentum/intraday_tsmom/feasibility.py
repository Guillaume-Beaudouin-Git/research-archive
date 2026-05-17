#!/usr/bin/env python
"""
Feasibility check — Intraday TSMOM on 4h crypto bars.
Reference : Zarattini, Pagani & Barbon (SFI WP 25-80, 2025)
            Nguyen "AdaptiveTrend" (arXiv 2602.11708, 2026)

Steps:
  1. Data  — yfinance 4h native; 1h→4h resample if unavailable
  2. Signal — sign(close[t] - close[t-lookback]), long-only binary
  3. Raw edge — Welch t-test signal=1 vs signal=0 forward returns
  4. Backtest — vol-scaled, costs 0.09% RT on signal changes
  5. Correlation — vs TSMOM v2 28-day daily
  6. Verdict

Run : python strategies/intraday_tsmom/feasibility.py
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────
ASSETS        = ["BTC-USD", "ETH-USD", "SOL-USD"]
LABELS        = ["BTC",     "ETH",     "SOL"]
LOOKBACKS     = [10, 20, 42]          # bars  (×4h = 40h, 80h, 168h)
COST_RT       = 0.0009                # 0.09% round-trip (HL taker ×2)
VOL_TARGET    = 0.15                  # 15% annualised vol target
VOL_LB        = 20                    # bars for realised-vol window
BARS_PER_YEAR = 365 * 6               # 24h crypto: 6 × 4h bars per day
TSMOM_V2_LB   = 28                    # daily lookback for TSMOM v2
OUT_DIR       = Path(__file__).parent


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — DATA
# ─────────────────────────────────────────────────────────────────────────────

def _get_4h_closes(ticker: str) -> pd.Series:
    """
    Download 4h closes for one ticker.
    Primary  : yfinance interval='4h' period='2y'  (~4 340 bars, ~2 years).
    Fallback : interval='1h' period='730d' resampled to 4h.
    NOTE: yfinance 4h history is capped at ~2 years regardless of period string.
          For longer history an alternative data source would be required.
    Returns tz-naive Close series.
    """
    t = yf.Ticker(ticker)
    df = t.history(period="2y", interval="4h")

    if len(df) < 500:
        # Fallback: 1h resampled to 4h
        df1h = t.history(period="730d", interval="1h")
        df = df1h["Close"].resample("4h").last().to_frame("Close").dropna()

    s = df["Close"]
    if s.index.tz is not None:
        s.index = s.index.tz_convert(None)
    return s


def download_data(assets: list[str], labels: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Download 4h closes and daily closes for all assets.
    Returns (closes_4h, closes_daily) — columns are labels, index tz-naive.
    """
    print("\n── STEP 1: DATA ─────────────────────────────────────────────")

    c4h: dict[str, pd.Series] = {}
    cd:  dict[str, pd.Series] = {}

    for ticker, label in zip(assets, labels):
        s4 = _get_4h_closes(ticker)
        c4h[label] = s4
        print(f"  {label:4s} 4h : {len(s4):5d} bars | NaNs: {s4.isna().sum()} "
              f"| {s4.index[0].date()} → {s4.index[-1].date()}")

        sd = yf.Ticker(ticker).history(period="2y", interval="1d")["Close"]
        if sd.index.tz is not None:
            sd.index = sd.index.tz_convert(None)
        cd[label] = sd

    closes_4h = pd.DataFrame(c4h).dropna(how="all")
    closes_d  = pd.DataFrame(cd).dropna(how="all")
    print(f"  Daily  : {closes_d.shape}  | {closes_d.index[0].date()} → "
          f"{closes_d.index[-1].date()}")
    return closes_4h, closes_d


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — SIGNAL
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(closes: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """
    Binary long-only TSMOM signal.
    signal[t] = 1 if close[t] > close[t - lookback] else 0.
    """
    return (closes > closes.shift(lookback)).astype(float)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — RAW SIGNAL EXISTENCE CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_raw_edge(closes: pd.DataFrame, lookbacks: list[int]) -> pd.DataFrame:
    """
    Welch t-test: mean(fwd_ret | signal=1) > mean(fwd_ret | signal=0)?
    fwd_ret[t] = close[t+1]/close[t] - 1  (signal at t predicts next-bar return).
    No look-ahead: signal[t] uses only close[t] and earlier.
    """
    print("\n── STEP 3: RAW SIGNAL EXISTENCE CHECK ──────────────────────")
    fwd = closes.pct_change().shift(-1)   # forward 1-bar return

    rows = []
    for lb in lookbacks:
        sig_df = compute_signal(closes, lb)
        for col in closes.columns:
            sig = sig_df[col].dropna()
            fwd_c = fwd[col].dropna()
            idx = sig.index.intersection(fwd_c.index)
            sig, fwd_c = sig.loc[idx], fwd_c.loc[idx]

            r1 = fwd_c[sig == 1.0]
            r0 = fwd_c[sig == 0.0]
            if min(len(r1), len(r0)) < 30:
                continue

            t_stat, p_val = stats.ttest_ind(r1, r0, equal_var=False, alternative="greater")
            rows.append({
                "asset":    col,
                "lookback": lb,
                "n_signal": len(r1),
                "mean_r1":  r1.mean(),
                "mean_r0":  r0.mean(),
                "t_stat":   t_stat,
                "p_value":  p_val,
                "hit_rate": float((r1 > 0).mean()),
            })

    df = pd.DataFrame(rows)
    header = (f"  {'asset':>5} {'lb':>4} {'n':>5} {'mean_r1':>9} "
              f"{'mean_r0':>9} {'t_stat':>7} {'p_val':>6} {'hit_rt':>7}")
    print(header)
    for _, row in df.iterrows():
        flag = " *" if row.t_stat > 1.5 else ""
        print(f"  {row.asset:>5} {row.lookback:>4.0f} {row.n_signal:>5.0f} "
              f"{row.mean_r1:>9.5f} {row.mean_r0:>9.5f} "
              f"{row.t_stat:>7.2f} {row.p_value:>6.3f} {row.hit_rate:>7.3f}{flag}")
    return df


def _pick_best_lookback(results: pd.DataFrame) -> tuple[bool, int]:
    """Returns (proceed, best_lookback). Proceed if t_stat > 1.5 on ≥2 combos."""
    passing = results[results["t_stat"] > 1.5]
    n_pass = len(passing)
    print(f"\n  Combinations with t-stat > 1.5 : {n_pass} / {len(results)}")
    if n_pass < 2:
        return False, -1
    best = int(passing.groupby("lookback")["t_stat"].mean().idxmax())
    print(f"  Best lookback (avg t-stat)      : {best} bars ({best * 4}h)")
    return True, best


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — QUICK BACKTEST
# ─────────────────────────────────────────────────────────────────────────────

def _vol_scale(rets: pd.Series) -> pd.Series:
    """Rolling realised-vol scalar targeting 15% annualised vol (capped at 3×)."""
    rv = rets.rolling(VOL_LB).std() * np.sqrt(BARS_PER_YEAR)
    return (VOL_TARGET / rv.replace(0, np.nan)).clip(upper=3.0)


def run_backtest(closes: pd.DataFrame, lookback: int) -> dict:
    """
    Vol-scaled TSMOM backtest on 4h bars.
    Execution: signal at close[t] → position during bar t+1 (1-bar lag).
    Uses close-to-close returns (standard academic approximation for feasibility).
    Cost: 0.09% RT applied at each signal transition, weighted by position size.
    Returns metrics dict including portfolio return series.
    """
    print(f"\n── STEP 4: BACKTEST  lookback={lookback} bars ({lookback * 4}h) ──────────")

    asset_rets: list[pd.Series] = []
    tpy_list:   list[float]     = []
    hold_list:  list[float]     = []

    for col in closes.columns:
        c       = closes[col].dropna()
        cc_ret  = c.pct_change()
        signal  = compute_signal(closes[[col]], lookback)[col].reindex(c.index).fillna(0)
        vscal   = _vol_scale(cc_ret)

        # 1-bar lag: position at bar t based on signal at bar t-1
        pos     = (signal * vscal).shift(1).fillna(0)
        gross   = cc_ret * pos

        # Costs: COST_RT on signal transitions (entry + exit), scaled by position size
        sig_flip = signal.diff().abs().fillna(0) > 0.5
        cost     = sig_flip.shift(1).fillna(False).astype(float) * COST_RT * pos.abs()

        net = (gross - cost).dropna()
        asset_rets.append(net.rename(col))

        years    = len(c) / BARS_PER_YEAR
        tpy_list.append(sig_flip.sum() / max(years, 1e-3))

        run, runs = 0, []
        for s in signal:
            if s == 1:
                run += 1
            elif run > 0:
                runs.append(run)
                run = 0
        hold_list.append(float(np.mean(runs)) if runs else 0.0)

    port    = pd.concat(asset_rets, axis=1).mean(axis=1).dropna()
    ann_ret = port.mean() * BARS_PER_YEAR
    ann_vol = port.std()  * np.sqrt(BARS_PER_YEAR)
    sharpe  = ann_ret / ann_vol if ann_vol > 0 else 0.0
    cum     = (1 + port).cumprod()
    max_dd  = ((cum - cum.cummax()) / cum.cummax()).min()

    print(f"  Ann. return     : {ann_ret:.2%}")
    print(f"  Ann. Sharpe     : {sharpe:.2f}")
    print(f"  Max drawdown    : {max_dd:.2%}")
    print(f"  Trades/yr (avg) : {np.mean(tpy_list):.0f}")
    print(f"  Avg hold (bars) : {np.mean(hold_list):.1f} ({np.mean(hold_list)*4:.0f}h)")

    return {
        "annual_return":    ann_ret,
        "sharpe":           sharpe,
        "max_dd":           max_dd,
        "trades_per_year":  float(np.mean(tpy_list)),
        "avg_holding_bars": float(np.mean(hold_list)),
        "port_rets":        port,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — CORRELATION WITH TSMOM v2
# ─────────────────────────────────────────────────────────────────────────────

def correlation_analysis(port_rets_4h: pd.Series, closes_d: pd.DataFrame) -> float:
    """
    Pearson correlation between intraday TSMOM daily P&L and TSMOM v2 daily P&L.
    TSMOM v2: 28-day lookback on daily closes, vol-scaled, equal-weight 3-asset.
    Saves rolling 90-day correlation chart as PNG.
    Returns Pearson r (NaN if insufficient overlap).
    """
    print("\n── STEP 5: CORRELATION WITH TSMOM v2 ───────────────────────")

    # TSMOM v2 daily P&L (28-day, long-only, vol-scaled)
    v2_list: list[pd.Series] = []
    for col in closes_d.columns:
        c   = closes_d[col].dropna()
        sig = (c > c.shift(TSMOM_V2_LB)).astype(float)
        ret = c.pct_change()
        rv  = ret.rolling(20).std() * np.sqrt(252)
        pos = (sig * (VOL_TARGET / rv.replace(0, np.nan)).clip(upper=3)).shift(1)
        v2_list.append((ret * pos).rename(col))

    v2_port = pd.concat(v2_list, axis=1).mean(axis=1).dropna()
    v2_port.index = pd.to_datetime(v2_port.index)
    if v2_port.index.tz is not None:
        v2_port.index = v2_port.index.tz_convert(None)

    # Aggregate 4h P&L to daily (sum intrabar returns)
    intra = port_rets_4h.copy()
    intra.index = pd.to_datetime(intra.index)
    if intra.index.tz is not None:
        intra.index = intra.index.tz_convert(None)
    intra_d = intra.resample("1D").sum()
    intra_d = intra_d[intra_d != 0].dropna()   # drop flat days

    common = intra_d.index.intersection(v2_port.index)
    if len(common) < 60:
        print(f"  Only {len(common)} overlapping days — skipping correlation")
        return float("nan")

    a, b = intra_d.loc[common], v2_port.loc[common]
    r, p = stats.pearsonr(a.values, b.values)

    # Rolling 90-day correlation
    comb   = pd.DataFrame({"intra": a, "v2": b})
    roll_r = comb["intra"].rolling(90).corr(comb["v2"])

    fig, ax = plt.subplots(figsize=(10, 4))
    roll_r.plot(ax=ax, color="steelblue", lw=1.5, label="Rolling 90d Pearson r")
    ax.axhline(0.5, color="red",    ls="--", lw=1, label="High corr threshold (0.50)")
    ax.axhline(0.3, color="orange", ls="--", lw=1, label="Low corr threshold  (0.30)")
    ax.axhline(0,   color="black",  ls="-",  lw=0.5)
    ax.set_title("Rolling 90-day Correlation: Intraday TSMOM 4h vs TSMOM v2 Daily")
    ax.set_ylabel("Pearson r")
    ax.legend(fontsize=8)
    fig.tight_layout()
    chart_path = OUT_DIR / "intraday_tsmom_correlation.png"
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"  Pearson r       : {r:.3f}  (p={p:.3f}, n={len(common)} days)")
    print(f"  Chart saved     : {chart_path}")
    flag = ("HIGH CORRELATION — likely redundant with TSMOM v2" if r > 0.5 else
            "LOW CORRELATION — potential diversifier"            if r < 0.3 else
            "MODERATE CORRELATION")
    print(f"  Assessment      : {flag}")
    return float(r)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    raw_df: pd.DataFrame,
    best_lb: int,
    bt: dict | None,
    corr: float | None,
    raw_passed: bool,
) -> None:
    """Structured feasibility summary."""
    sep = "=" * 55
    print(f"\n{sep}")
    print("FEASIBILITY REPORT — Intraday TSMOM 4h")
    print(sep)

    if not raw_passed:
        best_t = raw_df["t_stat"].max() if not raw_df.empty else float("nan")
        print(f"Raw signal exists    : NO  (max t-stat = {best_t:.2f} < 1.5)")
        print(f"Verdict              : SKIP")
        print(f"Reason               : No raw predictive edge detected before costs.")
        print(sep)
        return

    best_t = raw_df[raw_df["lookback"] == best_lb]["t_stat"].max()
    print(f"Raw signal exists    : YES (best t-stat = {best_t:.2f})")
    print(f"Best lookback        : {best_lb} bars ({best_lb * 4}h)")

    if bt:
        print(f"Sharpe after costs   : {bt['sharpe']:.2f}")
        print(f"Max drawdown         : {bt['max_dd']:.1%}")
        print(f"Annual return        : {bt['annual_return']:.1%}")
        print(f"Trades/year (avg)    : {bt['trades_per_year']:.0f}")
        print(f"Avg holding (bars)   : {bt['avg_holding_bars']:.1f} bars  "
              f"({bt['avg_holding_bars'] * 4:.0f}h)")

    corr_val = corr if (corr is not None and not np.isnan(corr)) else None
    if corr_val is not None:
        print(f"Correlation w/ TSMOM : {corr_val:.2f}")

    # Verdict
    verdict, note = "SKIP", ""
    if bt:
        s = bt["sharpe"]
        if s < 0.3:
            verdict = "SKIP"
            note    = "costs destroy edge — Sharpe < 0.3 after 0.09% RT"
        elif s < 0.7:
            verdict = "WEAK"
            note    = "marginal edge; OOS walk-forward required before trading"
        elif corr_val is not None and corr_val > 0.5:
            verdict = "WEAK"
            note    = "good Sharpe but high correlation limits diversification value"
        else:
            verdict = "PROMISING"
            note    = ("Next steps: walk-forward OOS validation, expand to full "
                       "14-asset universe, add funding-rate costs, size optimisation.")

    print(f"Verdict              : {verdict}")
    if note:
        print(f"Note                 : {note}")
    print(sep)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # Step 1 — Data
    closes_4h, closes_d = download_data(ASSETS, LABELS)

    # Step 2 — Signal description
    print("\n── STEP 2: SIGNAL ───────────────────────────────────────────")
    print(f"  Rule      : long if close[t] > close[t - lookback] else flat")
    print(f"  Lookbacks : {LOOKBACKS} bars  →  "
          f"{[lb * 4 for lb in LOOKBACKS]}h  "
          f"({[f'{lb*4/24:.1f}d' for lb in LOOKBACKS]})")

    # Step 3 — Raw edge check
    raw_df = check_raw_edge(closes_4h, LOOKBACKS)
    proceed, best_lb = _pick_best_lookback(raw_df)

    if not proceed:
        print("\n  t-stat < 1.5 for all combos — no raw edge found, stopping.")
        print_verdict(raw_df, -1, None, None, False)
        return

    print(f"\n  ✓ Raw edge confirmed — proceeding to backtest (lookback={best_lb}).")

    # Step 4 — Backtest
    bt = run_backtest(closes_4h, best_lb)

    # Step 5 — Correlation
    corr = correlation_analysis(bt["port_rets"], closes_d)

    # Step 6 — Verdict
    print_verdict(raw_df, best_lb, bt, corr, True)


if __name__ == "__main__":
    main()
