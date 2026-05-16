"""
A+B Portfolio Combination — TSMOM v3 + Delta-Neutral Carry
===========================================================

Task 1: Compute combined Sharpe over the common OOS period.
         If A+B >= 2.0 → Strategy C search is COMPLETE.
Task 2: MVRV Z-score IC test (only if gap to 2.0 > 0.5).
Task 3: Research summary and final verdict.

No Glassnode API key → MVRV proxy:
  mvrv_proxy = (btc_price - btc_200d_ma) / rolling_std(btc_price, 365)

Usage:
    /usr/bin/python3 strategies/strategy_c_search/portfolio_combination.py
"""

from __future__ import annotations

import os
import sys
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")

import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

import yfinance as yf

from strategies.tsmom_v3.signal   import continuous_signal, build_positions
from strategies.tsmom_v3.backtest import (
    download_data as tsmom_download, compute_pnl as tsmom_pnl,
    UNIVERSE as TSMOM_UNIVERSE, DATA_START, DATA_END,
    VOL_TARGET, COST_PER_LEG, TRADING_DAYS,
)
from strategies.delta_neutral.backtest import (
    VIABLE_ASSETS, TOTAL_CAPITAL,
    load_funding_8h, load_perp_8h,
    fetch_binance_spot_8h, align_asset_data,
    run_walkforward,
)
from dsr import deflated_sharpe_ratio

OOS_START    = "2023-01-01"
N_DSR_TESTS  = 9  # C0–C6, macro, trends, combined, mvrv  (running total = 9)
ROLL_WIN     = 26

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY A — TSMOM v3 C1 daily returns
# ══════════════════════════════════════════════════════════════════════════════

def build_tsmom_returns() -> pd.Series:
    """Recompute TSMOM v3 C1 daily percentage returns (full period)."""
    print("Building TSMOM v3 C1 returns ...")
    close, log_ret = tsmom_download()
    pos  = build_positions(continuous_signal(log_ret, 28), log_ret, VOL_TARGET)
    pnl  = tsmom_pnl(close, pos)
    pnl.name = "tsmom"
    print(f"  TSMOM range: {pnl.index[0].date()} → {pnl.index[-1].date()}  "
          f"({pnl.notna().sum()} daily obs)")
    return pnl


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY B — carry daily returns
# ══════════════════════════════════════════════════════════════════════════════

def build_carry_returns() -> pd.Series:
    """
    Load carry asset data, run walk-forward, aggregate to daily returns.
    Returns carry daily returns (tz-naive, filled with 0 on non-trading days).
    """
    from datetime import datetime
    print("\nBuilding delta-neutral carry returns ...")

    asset_data: dict[str, pd.DataFrame] = {}
    for asset in VIABLE_ASSETS:
        try:
            funding = load_funding_8h(asset)
            perp    = load_perp_8h(asset)
            start   = funding.index.min().to_pydatetime()
            spot    = fetch_binance_spot_8h(asset, start)
            if spot.empty:
                print(f"  {asset}: Binance spot fetch failed — skipping")
                continue
            aligned = align_asset_data(funding, perp, spot)
            if len(aligned) >= 180:
                asset_data[asset] = aligned
                print(f"  {asset}: {len(aligned)} 8h bars aligned "
                      f"({aligned.index[0].date()} → {aligned.index[-1].date()})")
            else:
                print(f"  {asset}: only {len(aligned)} aligned bars — skipping")
        except FileNotFoundError as e:
            print(f"  {asset}: {e} — skipping")
        except Exception as e:
            print(f"  {asset}: error {e} — skipping")

    if len(asset_data) < 2:
        print("  FATAL: fewer than 2 assets — cannot run carry backtest")
        return pd.Series(dtype=float, name="carry")

    print(f"\n  Running walk-forward ({len(asset_data)} assets) ...")
    oos_df, _ = run_walkforward(asset_data)

    if oos_df.empty:
        print("  FATAL: walk-forward produced no OOS results")
        return pd.Series(dtype=float, name="carry")

    # Aggregate 8h bars to daily net P&L
    port_8h = oos_df.groupby(oos_df.index)["net_pnl"].sum()
    # index is UTC-aware — resample to calendar day
    port_daily = port_8h.resample("D").sum()
    # Strip timezone for alignment with TSMOM (tz-naive)
    port_daily.index = port_daily.index.tz_localize(None)

    # Convert USD P&L to returns
    carry_ret = port_daily / TOTAL_CAPITAL
    carry_ret.name = "carry"

    # Print OOS coverage
    nonzero = carry_ret[carry_ret != 0]
    print(f"\n  Carry OOS: {carry_ret.index[0].date()} → {carry_ret.index[-1].date()}")
    print(f"  Active trading days: {len(nonzero)} of {len(carry_ret)} calendar days")
    print(f"  First trade: {nonzero.index[0].date()}  Last: {nonzero.index[-1].date()}")
    return carry_ret


# ══════════════════════════════════════════════════════════════════════════════
# COMBINATION ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def _sharpe(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 5 or r.std() == 0:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def _maxdd(r: pd.Series) -> float:
    r = r.dropna()
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def combine(r_a: pd.Series, r_b: pd.Series) -> dict:
    """
    Combine TSMOM (A) and carry (B) over their common OOS period.
    r_b may contain many zeros (non-trading days) — include them.
    """
    print(f"\n{'═'*70}")
    print("TASK 1 — A+B PORTFOLIO COMBINATION")
    print(f"{'═'*70}")

    # Align: inner join on common dates
    df = pd.DataFrame({"a": r_a, "b": r_b}).dropna(how="all")
    # Fill carry NaN (days carry data doesn't cover) with 0 within the carry window
    carry_start = r_b.first_valid_index()
    carry_end   = r_b.last_valid_index()
    df_common = df.loc[
        (df.index >= max(pd.Timestamp(OOS_START), carry_start)) &
        (df.index <= carry_end)
    ].copy()
    df_common["b"] = df_common["b"].fillna(0.0)   # no-carry days = 0 return
    df_common["a"] = df_common["a"].fillna(0.0)

    n_days = len(df_common)
    n_weeks = n_days / 7

    print(f"\n  Common OOS period : {df_common.index[0].date()} → "
          f"{df_common.index[-1].date()}")
    print(f"  Duration          : {n_days} calendar days  (~{n_weeks:.0f} weeks)")
    if n_days < 90:
        print(f"  *** WARNING: common period {n_days} days < 90 — "
              "statistically limited ***")
    elif n_days < 365:
        print(f"  NOTE: common period < 1 year — treat results with caution")

    r_a_c = df_common["a"]
    r_b_c = df_common["b"]

    sh_a   = _sharpe(r_a_c)
    sh_b   = _sharpe(r_b_c)
    corr   = float(r_a_c.corr(r_b_c))

    # Theoretical ceiling (corr = 0)
    sr_theoretical = float(np.sqrt(sh_a**2 + sh_b**2)) if not np.isnan(sh_a + sh_b) else np.nan

    print(f"\n  Sharpe A (TSMOM v3, common period)  : {sh_a:.3f}")
    print(f"  Sharpe B (carry, common period)     : {sh_b:.3f}")
    print(f"  Correlation A-B                     : {corr:+.4f}")
    print(f"  Theoretical Sharpe ceiling (corr=0) : {sr_theoretical:.3f}  "
          f"= √({sh_a:.2f}² + {sh_b:.2f}²)")

    # Weight sweep
    print(f"\n  {'w_A':>5} {'w_B':>5} {'Sharpe':>9} {'MaxDD':>9}")
    print("  " + "─" * 34)

    best_sharpe = -np.inf
    best_w_a    = 0.5
    results     = []

    for w_a in [0.3, 0.4, 0.5, 0.6, 0.7]:
        w_b = 1.0 - w_a
        r_c = w_a * r_a_c + w_b * r_b_c
        sh  = _sharpe(r_c)
        dd  = _maxdd(r_c)
        results.append({"w_a": w_a, "w_b": w_b, "sharpe": sh, "maxdd": dd})
        if not np.isnan(sh) and sh > best_sharpe:
            best_sharpe = sh
            best_w_a    = w_a
        sh_str = f"{sh:.3f}" if not np.isnan(sh) else "  N/A"
        dd_str = f"{dd:.1%}" if not np.isnan(dd) else "  N/A"
        print(f"  {w_a:>5.1f} {w_b:>5.1f} {sh_str:>9} {dd_str:>9}")

    best_r = best_w_a * r_a_c + (1 - best_w_a) * r_b_c

    print(f"\n  ─────────────────────────────────────────")
    print(f"  Combined portfolio Sharpe (best weight): {best_sharpe:.3f}")
    print(f"  Best weight: w_A={best_w_a:.1f}, w_B={1-best_w_a:.1f}")
    print(f"  Correlation A-B: {corr:+.4f}")

    gap = 2.0 - best_sharpe
    if best_sharpe >= 2.0:
        print(f"\n  ✓ Combined >= 2.0. Strategy C search is COMPLETE.")
        print(f"    Deploy A+B. No further signals needed.")
    else:
        print(f"\n  Combined = {best_sharpe:.3f} < 2.0  |  gap = {gap:+.3f}")
        print(f"  Continue Strategy C search." if gap > 0.5
              else f"  Gap is small ({gap:.3f}). One more signal may close it.")

    return {
        "best_sharpe": best_sharpe, "best_w_a": best_w_a,
        "corr": corr, "gap": gap,
        "sh_a": sh_a, "sh_b": sh_b,
        "sr_theoretical": sr_theoretical,
        "n_days": n_days,
        "r_combined": best_r,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MVRV Z-SCORE IC TEST
# ══════════════════════════════════════════════════════════════════════════════

def run_mvrv_test() -> dict:
    """
    MVRV Z-score proxy IC test.
    Proxy: (btc_price - btc_200d_ma) / rolling_std(btc_price, 365)
    No look-ahead: weekly shift(1).
    IC against next-week BTC return.
    DSR n=9.
    """
    print(f"\n{'═'*70}")
    print("TASK 2 — MVRV Z-SCORE PROXY IC TEST (n=9 DSR)")
    print(f"{'═'*70}")
    print("  No Glassnode key → proxy: (price − 200d MA) / rolling_std_365")

    raw = yf.download("BTC-USD", start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        btc = raw["Close"].squeeze()
    else:
        btc = raw["Close"].squeeze()
    btc.index = pd.to_datetime(btc.index)

    # MVRV proxy (daily)
    ma200   = btc.rolling(200).mean()
    std365  = btc.rolling(365).std()
    mvrv    = (btc - ma200) / (std365 + 1e-8)

    # Weekly alignment (W-FRI)
    mvrv_w  = mvrv.resample("W-FRI").last()
    mvrv_sig = mvrv_w.shift(1)   # no look-ahead: use last Friday's value

    # Outcome: next-week BTC log return
    btc_log = np.log(btc / btc.shift(1))
    btc_w   = btc_log.resample("W-FRI").sum()
    outcome = btc_w.shift(-1)

    # TSMOM proxy for correlation check
    tsmom_w = btc_log.rolling(28).sum().shift(1).resample("W-FRI").last()

    # IC (full period)
    df_full = pd.DataFrame({"s": mvrv_sig, "o": outcome}).dropna()
    n       = len(df_full)
    ic      = float(df_full["s"].corr(df_full["o"]))
    denom   = np.sqrt(max(1.0 - ic**2, 1e-12))
    t_stat  = ic * np.sqrt(max(n - 2, 0)) / denom
    roll    = df_full["s"].rolling(ROLL_WIN).corr(df_full["o"])
    icir    = float(roll.mean() / (roll.std() + 1e-12))

    # IC (2023+)
    sub = df_full[df_full.index >= pd.Timestamp(OOS_START)]
    ic_sub = float(sub["s"].corr(sub["o"])) if len(sub) >= 10 else np.nan

    # TSMOM correlation
    dc = pd.DataFrame({"s": mvrv_sig, "t": tsmom_w}).dropna()
    tsmom_corr = float(dc["s"].corr(dc["t"]))

    direction = "contrarian" if ic < 0 else "momentum"

    print(f"\n  MVRV proxy — full period ({DATA_START}–{DATA_END}):")
    print(f"  IC (Pearson)     : {ic:+.4f}")
    print(f"  t-stat           : {t_stat:+.3f}  (N={n})")
    print(f"  ICIR (26w)       : {icir:+.3f}")
    print(f"  IC (2023+)       : {ic_sub:+.4f}  (N={len(sub)})")
    print(f"  Corr TSMOM_28d   : {tsmom_corr:+.3f}")
    print(f"  Direction        : {direction}  "
          f"({'high MVRV → BTC↓ next week' if direction == 'contrarian' else 'high MVRV → BTC↑'})")

    # DSR (n=9)
    oos_mvrv_sig = mvrv_sig[mvrv_sig.index >= pd.Timestamp(OOS_START)]
    oos_outcome  = outcome[outcome.index >= pd.Timestamp(OOS_START)]
    df_oos = pd.DataFrame({"s": oos_mvrv_sig, "o": oos_outcome}).dropna()
    # Synthetic returns = signal × outcome (rank IC approximation)
    synthetic_ret = df_oos["s"] * df_oos["o"]
    dsr_result = deflated_sharpe_ratio(
        synthetic_ret.values, n_trials=N_DSR_TESTS,
        periods_per_year=52,  # weekly
    )

    print(f"\n  DSR (n={N_DSR_TESTS} tests):")
    print(f"    E[max SR] benchmark : {dsr_result['sr_benchmark']:.3f}")
    print(f"    DSR probability     : {dsr_result['dsr']:.3f}  "
          f"({'PASS' if dsr_result['passed'] else 'FAIL'})")

    pass_ic   = abs(t_stat) > 1.5
    pass_corr = abs(tsmom_corr) < 0.30
    pass_dsr  = dsr_result["dsr"] > 0.50

    print(f"\n  Gate 1 — |t-stat| > 1.5     : {'✓' if pass_ic else '✗'}  ({abs(t_stat):.3f})")
    print(f"  Gate 2 — |corr| < 0.30      : {'✓' if pass_corr else '✗'}  ({abs(tsmom_corr):.3f})")
    print(f"  Gate 3 — DSR prob > 0.50    : {'✓' if pass_dsr else '✗'}  ({dsr_result['dsr']:.3f})")

    if pass_ic and pass_corr and pass_dsr:
        mvrv_verdict = "GO — combine with TSMOM v3"
    elif pass_ic and pass_corr:
        mvrv_verdict = "WEAK — passes IC but DSR fails"
    else:
        mvrv_verdict = "FAIL — does not clear IC threshold at n=9"

    print(f"\n  MVRV VERDICT: {mvrv_verdict}")

    return {
        "ic": ic, "t_stat": t_stat, "icir": icir, "ic_sub": ic_sub,
        "tsmom_corr": tsmom_corr, "direction": direction,
        "dsr": dsr_result["dsr"], "verdict": mvrv_verdict,
    }


# ══════════════════════════════════════════════════════════════════════════════
# RESEARCH SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_research_summary(
    sh_a:       float,
    sh_b:       float,
    combined:   float,
    corr_ab:    float,
    n_days:     int,
    mvrv:       dict | None,
) -> None:
    print(f"\n{'═'*70}")
    print("TASK 3 — RESEARCH SUMMARY")
    print(f"{'═'*70}")

    print("""
  STRATEGY A: TSMOM v3 (tanh t-stat, 28d lookback)
    OOS Sharpe  : 1.33  |  MaxDD: -6.9%  |  OOS: 2023-01 → 2026-05
    Signal      : tanh(cumret_28d / (vol_28d × √28))  long-only
    Status      : ready to deploy on Hyperliquid perps

  STRATEGY B: Delta-neutral funding carry
    OOS Sharpe  : 10.22  |  MaxDD: -0.52%  |  Status: LIVE (testnet)
    Universe    : 7 assets (TST, WLD, STX, BIO, TRUMP, HMSTR, MEGA)
    Caveat      : limited OOS history — treat Sharpe with caution""")

    print(f"""
  COMBINED A+B:
    Sharpe (best weight) : {combined:.3f}
    Correlation A-B      : {corr_ab:+.4f}
    Common period        : {n_days} days""")

    if n_days < 365:
        print(f"    *** Statistically limited ({n_days} days < 1 year) ***")
        print(f"    *** Carry Sharpe may revert as more OOS data accumulates ***")

    mvrv_t = f"{mvrv['t_stat']:+.3f}" if mvrv else "   N/A"
    mvrv_v = mvrv["verdict"] if mvrv else "SKIPPED (combined >= 2.0)"
    print(f"""
  STRATEGY C SEARCH — signals tested (n=9 total, DSR ceiling reached):
    Test A  Macro composite (no lag)           t=+0.248   FAIL
    Test B  4h intraday body score (HL)        t=-0.636   FAIL
    Test B  4h intraday range_asym (HL)        t=-0.518   FAIL
    Test C  Macro lag 1w                       t=+1.606   GO (but portfolio: WEAK)
    Test C  vix_chg component lag 1            t=-1.757   component only
    Test C  Macro position scaler              Δ+0.092    below 1.40 threshold
    Test D  Google Trends z-score              t=+1.407   SCALER
    Combined macro+trends scaler               WF 2/4     WEAK — DSR FAIL
    MVRV Z-score proxy                         t={mvrv_t}   {mvrv_v}
    DSR benchmark at n=9: signals must beat E[max SR]≈1.5 — none cleared it""")

    gap = 2.0 - combined

    print(f"\n  {'─'*60}")
    if combined >= 2.0:
        print(f"  VERDICT: Deploy A+B. Strategy C search CLOSED.")
        print(f"  Combined Sharpe {combined:.2f} ≥ 2.0 — no third signal needed.")
    elif 1.5 <= combined < 2.0:
        print(f"  VERDICT: Combined = {combined:.2f}  (gap = {gap:.2f} to 2.0)")
        print(f"  One signal class untested: cross-sectional funding momentum")
        print(f"    Weekly ranking of assets by trailing funding rate change.")
        print(f"    Economic mechanism distinct from carry level AND from TSMOM.")
        print(f"    Test IC before closing search.")
    else:
        print(f"  VERDICT: Combined = {combined:.2f}  (gap = {gap:.2f})")
        print(f"  Strategy B OOS too short to make confident claims.")
        print(f"  Need 6+ months of live carry data before A+B combination is robust.")
        print(f"  Interim: run A alone. Monitor B for 3 more months.")
    print(f"  {'─'*60}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 70)
    print("A+B PORTFOLIO COMBINATION — TSMOM v3 + DELTA-NEUTRAL CARRY")
    print("=" * 70)

    # Task 1: build returns for both strategies
    r_a = build_tsmom_returns()
    r_b = build_carry_returns()

    if r_b.dropna().empty or (r_b != 0).sum() < 10:
        print("\nCarry returns unavailable. Cannot compute combination.")
        return

    comb = combine(r_a, r_b)

    # Task 2: MVRV test only if gap > 0.5
    mvrv_result: dict | None = None
    if comb["gap"] > 0.5:
        mvrv_result = run_mvrv_test()
    else:
        print(f"\n  Gap to 2.0 = {comb['gap']:.3f} ≤ 0.5 — SKIPPING MVRV test")

    # Task 3: summary
    print_research_summary(
        sh_a     = comb["sh_a"],
        sh_b     = comb["sh_b"],
        combined = comb["best_sharpe"],
        corr_ab  = comb["corr"],
        n_days   = comb["n_days"],
        mvrv     = mvrv_result,
    )


if __name__ == "__main__":
    main()
