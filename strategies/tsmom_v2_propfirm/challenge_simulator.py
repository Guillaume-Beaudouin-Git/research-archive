#!/usr/bin/env python
"""
Propr Challenge Simulator — TSMOM v2.

Simulates every possible weekly-start $5,000 Propr challenge attempt
from 2025-01-06 to 2025-11-03 using live-equivalent TSMOM v2 signal
and sizing logic.

Run: python -m strategies.tsmom_v2_propfirm.challenge_simulator
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Strategy imports with inline fallback ─────────────────────────────────────
try:
    from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance
    from strategies.tsmom_v2_propfirm.sizing import compute_vol_scalars, compute_positions
    from strategies.tsmom_v2_propfirm.config import VOL_LOOKBACK_DAYS
    print("  Using imported signal/sizing modules.")
except ImportError:
    print("  ImportError — using inline fallback implementations.")

    def compute_signal(prices: pd.DataFrame, lookback: int = 28) -> pd.DataFrame:  # type: ignore[misc]
        lr  = np.log(prices / prices.shift(1))
        cum = lr.rolling(lookback).sum().shift(1)
        sig = (cum > 0).astype(float)
        sig[cum.isna()] = np.nan
        return sig

    def apply_weekly_rebalance(signals: pd.DataFrame, rebalance_weekday: int = 0) -> pd.DataFrame:  # type: ignore[misc]
        mask = pd.Series(signals.index.dayofweek == rebalance_weekday, index=signals.index)
        return signals.where(mask).ffill()

    def compute_vol_scalars(lr: pd.DataFrame, vol_target: float, vol_lookback: int = 20) -> pd.DataFrame:  # type: ignore[misc]
        ann = lr.rolling(vol_lookback).std() * np.sqrt(365)
        return (vol_target / ann).shift(1).clip(0.1, 2.0)

    def compute_positions(signals: pd.DataFrame, vol_scalars: pd.DataFrame) -> pd.DataFrame:  # type: ignore[misc]
        return signals * vol_scalars

    VOL_LOOKBACK_DAYS: int = 20

# ── Constants ─────────────────────────────────────────────────────────────────
UNIVERSE = [
    "BTC-USD",  "ETH-USD",  "SOL-USD",  "AVAX-USD", "LINK-USD", "ARB-USD",
    "MATIC-USD","OP-USD",   "DOGE-USD", "ADA-USD",  "DOT-USD",  "UNI-USD",
    "LTC-USD",  "BCH-USD",
]
DATA_START = "2024-07-01"
DATA_END   = "2026-05-12"   # exclusive in yfinance → data through 2026-05-11
SIM_START  = "2025-01-06"
SIM_END    = "2025-11-03"
OUT_DIR    = Path(__file__).parent


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — DATA
# ─────────────────────────────────────────────────────────────────────────────

def download_data(universe: list[str], start: str, end: str) -> pd.DataFrame:
    """
    Download daily adjusted close prices from yfinance.
    Silently drops delisted / unavailable tickers (MATIC-USD, UNI-USD, etc.).
    Returns DataFrame: index=tz-naive date, columns=yfinance tickers.
    """
    print(f"Downloading price data ({start} → {end})...")
    raw = yf.download(
        tickers=universe, start=start, end=end,
        interval="1d", auto_adjust=True, progress=False,
    )
    closes = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
    if closes.index.tz is not None:
        closes.index = closes.index.tz_convert(None)

    closes = closes.dropna(axis=1, how="all")   # remove fully-NaN cols (delisted)
    closes = closes.ffill()                      # fill minor gaps

    dropped = [t for t in universe if t not in closes.columns]
    print(f"  Available : {len(closes.columns)} assets | Dropped : {dropped}")
    print(f"  Date range: {closes.index[0].date()} → {closes.index[-1].date()} "
          f"({len(closes)} days)")
    return closes


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — SIMULATE ONE CHALLENGE
# ─────────────────────────────────────────────────────────────────────────────

def _build_result(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    outcome: str,
    fail_reason: str | None,
    final_equity: float,
    equity_curve: list[float],
    peak_equity: float,
    trading_days_count: int,
) -> dict[str, Any]:
    """Assemble the result dict; compute max drawdown from equity curve."""
    arr = np.array(equity_curve)
    hwm = np.maximum.accumulate(arr)
    dd  = (arr - hwm) / hwm
    return {
        "start_date":         start_date,
        "end_date":           end_date,
        "outcome":            outcome,
        "fail_reason":        fail_reason,
        "final_equity":       round(final_equity, 2),
        "peak_equity":        round(peak_equity, 2),
        "max_drawdown_pct":   float(-dd.min()),
        "days_elapsed":       len(equity_curve) - 1,
        "trading_days_count": trading_days_count,
        "equity_curve":       equity_curve,
    }


def simulate_challenge(
    start_date: pd.Timestamp,
    prices: pd.DataFrame,
    initial_equity: float = 5000.0,
    profit_target_pct: float = 0.10,
    max_drawdown_pct: float = 0.06,
    daily_loss_limit_pct: float = 0.03,
    vol_target: float = 0.15,
    costs_per_leg: float = 0.00045,
) -> dict[str, Any]:
    """
    Simulate one Propr challenge attempt starting on start_date.

    Signal uses shift(1) throughout — strict no look-ahead.
    HWM is static at initial_equity (Propr static drawdown rule).
    Position sizes capped at 90 % of current equity at each rebalance.

    Each day order:
      1. MTM on carried positions (prev-close → today-close)
      2. If Monday: rebalance at today's close (pay costs, update positions)
      3. Daily loss check: (equity - eq_day_start) / eq_day_start
      4. Total DD check: equity vs static HWM
      5. Profit-target check
    """
    log_ret      = np.log(prices / prices.shift(1))
    signals      = compute_signal(prices)
    vol_scalars  = compute_vol_scalars(log_ret, vol_target, VOL_LOOKBACK_DAYS)
    pos_sizes    = compute_positions(signals, vol_scalars)
    weekly_sizes = apply_weekly_rebalance(pos_sizes)

    equity:    float             = initial_equity
    hwm:       float             = initial_equity
    positions: dict[str, float]  = {}           # {ticker: quantity}
    equity_curve: list[float]    = [initial_equity]
    peak:      float             = initial_equity
    rebal_count: int             = 0

    sim_dates = prices.index[prices.index >= start_date]

    for i, date in enumerate(sim_dates):
        eq_day_start = equity

        # ── 1. MTM on carried positions ────────────────────────────────────
        if i > 0 and positions:
            prev = sim_dates[i - 1]
            for ticker, qty in positions.items():
                if ticker not in prices.columns:
                    continue
                p_now  = prices.at[date, ticker]
                p_prev = prices.at[prev,  ticker]
                if not (pd.isna(p_now) or pd.isna(p_prev)):
                    equity += qty * (p_now - p_prev)

        # ── 2. Weekly rebalance on Mondays ────────────────────────────────
        if date.dayofweek == 0 and date in weekly_sizes.index:
            sizes_row = weekly_sizes.loc[date]
            target: dict[str, float] = {}

            for ticker in prices.columns:
                if ticker not in sizes_row.index:
                    continue
                sz = sizes_row[ticker]
                px = prices.at[date, ticker]
                if not pd.isna(sz) and sz > 0 and not pd.isna(px) and px > 0:
                    target[ticker] = equity * float(sz)

            # 90 % equity cap — same fix as live rebalance.py
            total_notional = sum(target.values())
            if total_notional > equity * 0.90:
                scale = equity * 0.90 / total_notional
                target = {k: v * scale for k, v in target.items()}

            # Costs: one leg × |Δnotional| per asset
            for ticker in set(positions) | set(target):
                if ticker not in prices.columns:
                    continue
                px = prices.at[date, ticker]
                if pd.isna(px) or px <= 0:
                    continue
                old_n = positions.get(ticker, 0.0) * px
                new_n = target.get(ticker, 0.0)
                equity -= abs(new_n - old_n) * costs_per_leg

            positions = {
                t: n / prices.at[date, t]
                for t, n in target.items()
                if prices.at[date, t] > 0
            }
            rebal_count += 1

        # ── 3. Daily loss limit ────────────────────────────────────────────
        if i > 0:
            if (equity - eq_day_start) / eq_day_start < -daily_loss_limit_pct:
                equity_curve.append(equity)   # include terminal equity in curve
                return _build_result(
                    start_date, date, "FAIL", "daily_limit",
                    equity, equity_curve, peak, rebal_count,
                )

        # ── 4. Total drawdown vs static HWM ──────────────────────────────
        if equity <= hwm * (1.0 - max_drawdown_pct):
            equity_curve.append(equity)
            return _build_result(
                start_date, date, "FAIL", "total_drawdown",
                equity, equity_curve, peak, rebal_count,
            )

        # ── 5. Profit target ──────────────────────────────────────────────
        if equity >= hwm * (1.0 + profit_target_pct):
            equity_curve.append(equity)
            return _build_result(
                start_date, date, "PASS", None,
                equity, equity_curve, peak, rebal_count,
            )

        if equity > peak:
            peak = equity
        equity_curve.append(equity)

    last_date = sim_dates[-1] if len(sim_dates) > 0 else start_date
    return _build_result(
        start_date, last_date, "INCOMPLETE", None,
        equity, equity_curve, peak, rebal_count,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — RUN ALL SIMULATIONS
# ─────────────────────────────────────────────────────────────────────────────

def run_all_simulations(
    prices: pd.DataFrame,
    vol_target: float = 0.15,
    verbose: bool = True,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Run simulate_challenge for every Monday start date in [SIM_START, SIM_END].
    Returns (summary_df, full_results_list).
    """
    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    if verbose:
        print(f"\nRunning {len(start_dates)} simulations "
              f"({start_dates[0].date()} → {start_dates[-1].date()})...")

    all_results: list[dict[str, Any]] = []
    for sd in start_dates:
        if verbose:
            print(f"  Simulating start_date {sd.date()}...")
        all_results.append(simulate_challenge(sd, prices, vol_target=vol_target))

    rows = [{k: v for k, v in r.items() if k != "equity_curve"} for r in all_results]
    return pd.DataFrame(rows), all_results


# ─────────────────────────────────────────────────────────────────────────────
# VOL TARGET SWEEP — Steps 1-6
# ─────────────────────────────────────────────────────────────────────────────

VOL_TARGETS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25]
CHALLENGE_FEE = 60.0   # $ per attempt


def _sweep_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute all summary metrics for one vol_target's 44-sim DataFrame."""
    n = len(df)
    pass_m  = df["outcome"] == "PASS"
    fail_m  = df["outcome"] == "FAIL"

    pass_count = int(pass_m.sum())
    fail_count = int(fail_m.sum())
    pass_rate  = pass_count / n
    fail_rate  = fail_count / n

    fail_daily = int((df["fail_reason"] == "daily_limit").sum())
    fail_total = int((df["fail_reason"] == "total_drawdown").sum())

    # avg days (None if no sims of that outcome)
    avg_pass = float(df.loc[pass_m, "days_elapsed"].mean()) if pass_m.any() else None
    avg_fail = float(df.loc[fail_m, "days_elapsed"].mean()) if fail_m.any() else None

    median_dd = float(df["max_drawdown_pct"].median())

    exp_fee = (CHALLENGE_FEE / pass_rate) if pass_rate > 0 else float("inf")

    # Daily breach analysis:
    # Each sim that ends on "daily_limit" had exactly 1 breach.
    # Sims that fail on total_dd or PASS had 0 daily breaches (the limit wasn't hit).
    total_breaches      = fail_daily
    avg_breaches_per    = total_breaches / n
    pct_zero_breaches   = (n - total_breaches) / n * 100.0

    # Speed-safety score: pass_rate × (1 / avg_days_to_pass)
    score = (pass_rate / avg_pass) if (pass_rate > 0 and avg_pass and avg_pass > 0) else 0.0

    return {
        "pass_count":           pass_count,
        "fail_count":           fail_count,
        "pass_rate":            pass_rate,
        "fail_rate":            fail_rate,
        "fail_daily":           fail_daily,
        "fail_total_dd":        fail_total,
        "avg_days_pass":        avg_pass,
        "avg_days_fail":        avg_fail,
        "median_max_dd":        median_dd,
        "exp_fee":              exp_fee,
        "total_breaches":       total_breaches,
        "avg_breaches_per_sim": avg_breaches_per,
        "pct_zero_breaches":    pct_zero_breaches,
        "score":                score,
    }


def run_vol_sweep(
    prices: pd.DataFrame,
    vol_targets: list[float] = VOL_TARGETS,
) -> dict[float, tuple[pd.DataFrame, list[dict[str, Any]]]]:
    """
    Run all 44 simulations for each vol_target.
    Returns {vol_target: (summary_df, results_list)}.
    """
    sweep: dict[float, tuple[pd.DataFrame, list[dict[str, Any]]]] = {}
    for vt in vol_targets:
        print(f"vol_target={vt:.2f}: running 44 sims...", flush=True)
        df, results = run_all_simulations(prices, vol_target=vt, verbose=False)
        sweep[vt] = (df, results)
    return sweep


def print_sweep_table(
    sweep: dict[float, tuple[pd.DataFrame, list[dict[str, Any]]]],
) -> float:
    """
    Print the vol_target sweep summary table.
    Returns the recommended vol_target (highest score).
    """
    rows: list[dict[str, Any]] = []
    for vt, (df, _) in sweep.items():
        m = _sweep_metrics(df)
        rows.append({"vol_t": vt, **m})

    print("\n" + "=" * 110)
    print("VOL TARGET SWEEP — Propr Starter Challenge")
    print("=" * 110)
    hdr = (
        f"{'vol_t':>6} | {'Pass%':>6} | {'Fail%':>6} | "
        f"{'Daily':>6} | {'TotalDD':>8} | "
        f"{'AvgDaysPass':>12} | {'AvgDaysFail':>12} | "
        f"{'MedianDD':>9} | {'ExpFee':>8} | {'Score':>7}"
    )
    print(hdr)
    print("-" * 110)

    best_score = -1.0
    best_vt    = VOL_TARGETS[0]

    for r in rows:
        vt      = r["vol_t"]
        pass_p  = f"{r['pass_rate']*100:.0f}%"
        fail_p  = f"{r['fail_rate']*100:.0f}%"
        daily   = str(r["fail_daily"])
        total_d = str(r["fail_total_dd"])
        adp     = f"{r['avg_days_pass']:.0f}d" if r["avg_days_pass"] else "—"
        adf     = f"{r['avg_days_fail']:.0f}d" if r["avg_days_fail"] else "—"
        mdd     = f"-{r['median_max_dd']*100:.1f}%"
        ef      = f"${r['exp_fee']:.0f}" if r["exp_fee"] < 1e9 else "∞"
        score   = f"{r['score']:.4f}"
        print(
            f"{vt:>6.2f} | {pass_p:>6} | {fail_p:>6} | "
            f"{daily:>6} | {total_d:>8} | "
            f"{adp:>12} | {adf:>12} | "
            f"{mdd:>9} | {ef:>8} | {score:>7}"
        )
        if r["score"] > best_score:
            best_score = r["score"]
            best_vt    = vt

    print("-" * 110)

    best_m = _sweep_metrics(sweep[best_vt][0])
    adp_str = f"{best_m['avg_days_pass']:.0f}" if best_m["avg_days_pass"] else "?"

    print(f"\nRECOMMENDED VOL TARGET: {best_vt:.2f}")
    print(
        f"Reason: highest speed-safety score ({best_score:.4f} = "
        f"{best_m['pass_rate']*100:.0f}% pass rate × "
        f"1/{adp_str}d avg-to-pass), balancing win probability and time-to-target."
    )
    print(f"\n  At this vol_target:")
    print(f"    Pass rate          : {best_m['pass_rate']*100:.0f}%")
    adp_weeks = f"{best_m['avg_days_pass']/7:.1f}" if best_m["avg_days_pass"] else "?"
    print(f"    Avg days to pass   : {adp_str} days (~{adp_weeks} weeks)")
    ef_str = f"${best_m['exp_fee']:.0f}" if best_m["exp_fee"] < 1e9 else "∞"
    print(f"    Expected fee cost  : {ef_str} to get one PASS")
    print(f"    Daily breaches     : {best_m['total_breaches']} total across 44 sims")
    print(f"    Sims with 0 breach : {best_m['pct_zero_breaches']:.0f}% (cleanest runs)")

    return best_vt


def print_regime_analysis(
    df: pd.DataFrame,
    vol_target: float,
) -> None:
    """
    Step 5: Per-simulation table for the recommended vol_target,
    grouped PASS (ascending days) then FAIL (fail_reason, days).
    Also prints monthly pass rates.
    """
    print(f"\n{'='*75}")
    print(f"REGIME ANALYSIS — vol_target={vol_target:.2f}")
    print(f"{'='*75}")

    pass_df = df[df["outcome"] == "PASS"].sort_values("days_elapsed")
    fail_df = df[df["outcome"] == "FAIL"].sort_values(["fail_reason", "days_elapsed"])
    inc_df  = df[df["outcome"] == "INCOMPLETE"]
    ordered = pd.concat([pass_df, fail_df, inc_df])

    header = (
        f"  {'start_date':>12} {'outcome':>10} {'days':>6} "
        f"{'final_equity':>12} {'max_dd':>8} {'fail_reason':>14}"
    )
    print(header)
    print("-" * 75)
    for _, row in ordered.iterrows():
        fr = row["fail_reason"] if pd.notna(row["fail_reason"]) else "-"
        print(
            f"  {str(row['start_date'].date()):>10} {row['outcome']:>10} "
            f"{int(row['days_elapsed']):>6} "
            f"${row['final_equity']:>10,.2f} "
            f"{-row['max_drawdown_pct']:>7.1%} "
            f"{fr:>14}"
        )
    print("-" * 75)

    # Monthly pass rate
    print(f"\n  Monthly pass rates (by challenge start month):")
    df2 = df.copy()
    df2["month"] = df2["start_date"].dt.to_period("M")
    for month, grp in df2.groupby("month"):
        n_m    = len(grp)
        n_pass = (grp["outcome"] == "PASS").sum()
        pct    = n_pass / n_m * 100
        bar    = "█" * n_pass + "░" * (n_m - n_pass)
        print(f"    {month}: {n_pass}/{n_m} sims → {pct:.0f}% PASS  [{bar}]")


def plot_vol_sweep(
    sweep: dict[float, tuple[pd.DataFrame, list[dict[str, Any]]]],
    best_vt: float,
    save_path: Path,
) -> None:
    """
    Two-subplot chart:
      Left : pass rate % (bar chart, best highlighted green)
      Right: expected fee cost to get one PASS (line chart)
    """
    vts      = sorted(sweep.keys())
    metrics  = [_sweep_metrics(sweep[vt][0]) for vt in vts]
    pass_pct = [m["pass_rate"] * 100 for m in metrics]
    exp_fees = [min(m["exp_fee"], 1200) for m in metrics]   # cap at $1200 for legibility
    scores   = [m["score"] for m in metrics]

    colors = ["#2ecc71" if vt == best_vt else "#3498db" for vt in vts]
    labels = [f"{vt:.2f}" for vt in vts]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
    fig.suptitle(
        "Vol Target Sweep — Propr Starter Challenge ($5K, 3% daily, 6% total DD)",
        fontsize=13, fontweight="bold",
    )

    # Left: pass rate bar chart
    bars = ax1.bar(labels, pass_pct, color=colors, edgecolor="white", linewidth=0.5)
    ax1.set_xlabel("Vol Target")
    ax1.set_ylabel("Pass Rate (%)")
    ax1.set_title("Pass Rate by Vol Target")
    for bar, pct in zip(bars, pass_pct):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            f"{pct:.0f}%",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
        )
    # Mark best
    best_idx = vts.index(best_vt)
    ax1.annotate(
        "★ best",
        xy=(best_idx, pass_pct[best_idx]),
        xytext=(best_idx, pass_pct[best_idx] + 5),
        ha="center", fontsize=9, color="#27ae60", fontweight="bold",
    )
    ax1.set_ylim(0, max(pass_pct) * 1.25)

    # Right: expected fee line chart
    valid_fees = [(vt, fee) for vt, fee in zip(vts, exp_fees) if fee < 1200]
    if valid_fees:
        vts_f, fees_f = zip(*valid_fees)
        ax2.plot([f"{v:.2f}" for v in vts_f], fees_f,
                 color="#e74c3c", marker="o", linewidth=2, markersize=6)
    ax2.axhline(CHALLENGE_FEE, color="gray", linestyle="--", linewidth=1.2,
                label=f"Single attempt (${CHALLENGE_FEE:.0f})")
    ax2.set_xlabel("Vol Target")
    ax2.set_ylabel("Expected Fee Cost ($)")
    ax2.set_title("Expected Total Fee Cost\nto Get One PASS")
    ax2.legend(fontsize=8)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nVol sweep chart saved → {save_path}")


# ─────────────────────────────────────────────────────────────────────────────
# REGIME FILTER — Steps 1–6
# ─────────────────────────────────────────────────────────────────────────────

HL_DATA_DIR       = Path(__file__).parent.parent / "cs_carry" / "data"
REGIME_VOL_TARGET = 0.15
REGIME_THRESHOLDS = [0.0, 0.20, 0.35, 0.50, 0.60, 0.70, 0.80]
TODAY_DATE        = "2026-05-11"


def _load_btc_funding() -> "pd.Series | None":
    """Load cached BTC hourly funding from strategies/cs_carry/data/BTC_hl_funding.csv."""
    cache = HL_DATA_DIR / "BTC_hl_funding.csv"
    if not cache.exists():
        return None
    df = pd.read_csv(cache, index_col=0, parse_dates=True)
    s  = df.iloc[:, 0]
    idx = pd.DatetimeIndex(s.index)
    s.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    return s.sort_index()


def compute_regime_score(
    prices_df: pd.DataFrame,
    date: pd.Timestamp,
    btc_funding: "pd.Series | None" = None,
) -> dict[str, Any]:
    """
    Compute regime indicators and composite score at `date`.
    All indicators use data strictly up to and including `date` (no look-ahead).

    Returns dict with individual booleans, floats, and composite regime_score ∈ [0, 1].
    """
    btc_col = "BTC-USD" if "BTC-USD" in prices_df.columns else prices_df.columns[0]
    btc = prices_df.loc[:date, btc_col].dropna()

    _null: dict[str, Any] = {
        "btc_above_ma50": False, "btc_above_ma20": False,
        "btc_ma_slope": 0.0, "realized_vol_20d": 0.0,
        "vol_percentile": 0.5, "avg_funding_7d": None,
        "regime_score": 0.0,
        "_ma50_pass": False, "_vol_pass": False, "_fund_pass": False,
    }
    if len(btc) < 52:
        return _null

    close_t = float(btc.iloc[-1])
    ma_ser  = btc.rolling(20).mean()
    ma50    = float(btc.rolling(50).mean().iloc[-1])
    ma20    = float(ma_ser.iloc[-1])
    ma20_5a = float(ma_ser.iloc[-6]) if len(btc) >= 25 else ma20

    btc_above_ma50 = bool(close_t > ma50)
    btc_above_ma20 = bool(close_t > ma20)
    btc_ma_slope   = (ma20 - ma20_5a) / ma20_5a if ma20_5a != 0.0 else 0.0

    # ── Volatility regime ────────────────────────────────────────────────────
    daily_ret       = btc.pct_change().dropna()
    roll_vol        = daily_ret.rolling(20).std() * np.sqrt(252)
    realized_vol_20d = float(roll_vol.iloc[-1]) if not pd.isna(roll_vol.iloc[-1]) else 0.0
    hist_vols       = roll_vol.iloc[-252:].dropna()
    vol_percentile  = float((hist_vols < realized_vol_20d).mean()) if len(hist_vols) >= 20 else 0.5

    # ── Funding sentiment (optional) ─────────────────────────────────────────
    avg_funding_7d: float | None = None
    if btc_funding is not None:
        date_utc = date.tz_localize("UTC") if date.tzinfo is None else date.tz_convert("UTC")
        window   = btc_funding.loc[
            (btc_funding.index >= date_utc - pd.Timedelta(days=7)) &
            (btc_funding.index <= date_utc)
        ]
        if len(window) >= 24:
            avg_funding_7d = float(window.mean())

    # ── Composite score ──────────────────────────────────────────────────────
    score = 0.0
    if btc_above_ma50:                                       score += 0.35
    if btc_above_ma20:                                       score += 0.25
    if btc_ma_slope > 0:                                     score += 0.20
    if vol_percentile < 0.60:                                score += 0.10
    if avg_funding_7d is not None and avg_funding_7d > 0.0001:
        score += 0.10
    elif avg_funding_7d is None:
        score += 0.05   # neutral when funding data unavailable

    ma50_pass  = btc_above_ma50
    vol_pass   = vol_percentile < 0.60
    fund_pass  = (avg_funding_7d is not None and avg_funding_7d > 0.0001) or (avg_funding_7d is None)

    return {
        "btc_above_ma50":   btc_above_ma50,
        "btc_above_ma20":   btc_above_ma20,
        "btc_ma_slope":     btc_ma_slope,
        "realized_vol_20d": realized_vol_20d,
        "vol_percentile":   vol_percentile,
        "avg_funding_7d":   avg_funding_7d,
        "regime_score":     score,
        "_ma50_pass":       ma50_pass,
        "_vol_pass":        vol_pass,
        "_fund_pass":       fund_pass,
    }


def run_regime_sweep(
    prices: pd.DataFrame,
    thresholds: list[float] = REGIME_THRESHOLDS,
    vol_target: float = REGIME_VOL_TARGET,
) -> tuple[list[dict[str, Any]], pd.DataFrame, pd.DataFrame]:
    """
    Step 1+2: Compute regime scores for all 44 Monday starts, run one set of
    44 baseline sims (vol_target=0.15), then filter by each threshold.

    Returns (threshold_results, scores_df, baseline_df_indexed).
    Reusing baseline results for every threshold avoids redundant simulation.
    """
    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    btc_funding = _load_btc_funding()
    print(f"  Funding data: {'HL cache' if btc_funding is not None else 'not available (using neutral score)'}")

    # ── Compute regime scores ────────────────────────────────────────────────
    print(f"Computing regime scores for {len(start_dates)} dates...", flush=True)
    scores: dict[pd.Timestamp, dict[str, Any]] = {
        sd: compute_regime_score(prices, sd, btc_funding)
        for sd in start_dates
    }
    scores_df = pd.DataFrame.from_dict(scores, orient="index")
    scores_df.index.name = "start_date"

    # ── Run baseline 44 sims once ────────────────────────────────────────────
    print(f"Running baseline 44 sims (vol_target={vol_target})...", flush=True)
    base_df_raw, _ = run_all_simulations(prices, vol_target=vol_target, verbose=False)
    base_df = base_df_raw.copy()
    base_df["start_date"] = pd.to_datetime(base_df["start_date"])
    base_df = base_df.set_index("start_date")

    # ── Threshold sweep ──────────────────────────────────────────────────────
    threshold_results: list[dict[str, Any]] = []
    for thr in thresholds:
        eligible = [sd for sd, s in scores.items() if s["regime_score"] >= thr]
        n_elig   = len(eligible)

        if n_elig == 0:
            threshold_results.append({
                "threshold": thr, "n_eligible": 0,
                "pass_rate_cond": 0.0, "pass_rate_uncond": 0.0,
                "avg_days_pass": None, "exp_fee": float("inf"),
                "wait_weeks": float("inf"),
            })
            continue

        sub       = base_df.loc[base_df.index.isin(eligible)]
        n_pass    = int((sub["outcome"] == "PASS").sum())
        pass_cond = n_pass / n_elig
        pass_unc  = n_pass / 44.0

        pass_sub  = sub[sub["outcome"] == "PASS"]
        avg_days  = float(pass_sub["days_elapsed"].mean()) if len(pass_sub) > 0 else None
        exp_fee   = (CHALLENGE_FEE / pass_cond) if pass_cond > 0 else float("inf")
        wait_wks  = 44.0 / n_elig   # avg Mondays between eligible windows

        threshold_results.append({
            "threshold":        thr,
            "n_eligible":       n_elig,
            "pass_rate_cond":   pass_cond,
            "pass_rate_uncond": pass_unc,
            "avg_days_pass":    avg_days,
            "exp_fee":          exp_fee,
            "wait_weeks":       wait_wks,
        })

    return threshold_results, scores_df, base_df


def print_regime_sweep_table(
    threshold_results: list[dict[str, Any]],
    scores_df: pd.DataFrame,
    base_df: pd.DataFrame,
) -> float:
    """
    Step 4: Print the regime threshold sweep table and individual indicator analysis.
    Returns the recommended threshold.
    """
    print("\n" + "=" * 95)
    print("REGIME FILTER SWEEP — Propr Challenge Pass Rate")
    print("=" * 95)
    hdr = (
        f"{'Threshold':>10} | {'Eligible':>9} | {'Pass%(cond)':>12} | "
        f"{'Pass%(uncond)':>14} | {'AvgDaysPass':>12} | {'ExpFee':>8} | {'Wait(wks)':>10}"
    )
    print(hdr)
    print("-" * 95)

    best_thr   = 0.0
    best_score = 0.0   # maximize pass_rate_cond / wait_weeks tradeoff

    for r in threshold_results:
        thr  = r["threshold"]
        n    = f"{r['n_eligible']}/44"
        pc   = f"{r['pass_rate_cond']*100:.0f}%" if r["n_eligible"] > 0 else "—"
        pu   = f"{r['pass_rate_uncond']*100:.0f}%"
        adp  = f"{r['avg_days_pass']:.0f}d" if r["avg_days_pass"] else "—"
        ef   = f"${r['exp_fee']:.0f}" if r["exp_fee"] < 1e9 else "∞"
        ww   = f"{r['wait_weeks']:.1f}" if r["wait_weeks"] < 1e9 else "∞"
        print(f"{thr:>10.2f} | {n:>9} | {pc:>12} | {pu:>14} | {adp:>12} | {ef:>8} | {ww:>10}")

        # Score: conditional pass rate improvement vs baseline, penalised by wait
        # want best (pass_rate_cond - baseline) × (1 / wait_weeks)
        baseline_cond = threshold_results[0]["pass_rate_cond"]
        improvement   = r["pass_rate_cond"] - baseline_cond
        s = improvement / r["wait_weeks"] if r["n_eligible"] > 0 and r["wait_weeks"] > 0 else 0.0
        if s > best_score and r["n_eligible"] >= 5:
            best_score = s
            best_thr   = thr

    print("-" * 95)

    # Individual indicator analysis (Step 3)
    print("\nINDIVIDUAL INDICATORS:")

    def _indicator_stats(mask: pd.Series, label: str) -> None:
        eligible_dates = scores_df[mask].index
        n_elig = len(eligible_dates)
        if n_elig == 0:
            print(f"  {label:<24}: 0/44 eligible → n/a")
            return
        sub    = base_df.loc[base_df.index.isin(eligible_dates)]
        n_pass = int((sub["outcome"] == "PASS").sum())
        pct    = n_pass / n_elig * 100
        print(f"  {label:<24}: {n_elig:>2}/44 eligible → {pct:.0f}% pass rate ({n_pass}/{n_elig} PASS)")

    _indicator_stats(scores_df["_ma50_pass"],               "MA50 only")
    _indicator_stats(scores_df["_vol_pass"],                "Vol<60th only")
    _indicator_stats(scores_df["_fund_pass"],               "Funding only")
    _indicator_stats(scores_df["_ma50_pass"] & scores_df["_vol_pass"],               "MA50 + Vol")
    _indicator_stats(scores_df["_ma50_pass"] & scores_df["_vol_pass"] & scores_df["_fund_pass"], "All three")

    # Recommendation
    best_r      = next(r for r in threshold_results if r["threshold"] == best_thr)
    base_r      = threshold_results[0]
    lift        = best_r["pass_rate_cond"] - base_r["pass_rate_cond"]
    ef_str      = f"${best_r['exp_fee']:.0f}" if best_r["exp_fee"] < 1e9 else "∞"
    adp_str     = f"{best_r['avg_days_pass']:.0f}" if best_r["avg_days_pass"] else "?"

    print(f"\nRECOMMENDATION:")
    print(f"  Use regime filter threshold = {best_thr:.2f}")
    print(f"  Expected conditional pass rate : {best_r['pass_rate_cond']*100:.0f}%")
    print(f"  Expected wait between windows  : ~{best_r['wait_weeks']:.1f} weeks")
    print(f"  Expected total fee to pass     : {ef_str}")
    print()
    if lift > 0.05:
        weeks_to_break_even = best_r["wait_weeks"]
        baseline_fee = f"${base_r['exp_fee']:.0f}" if base_r["exp_fee"] < 1e9 else "∞"
        print(
            f"  Economic reasoning: The {best_thr:.0%} threshold lifts conditional pass rate "
            f"by {lift:.0%} (from {base_r['pass_rate_cond']*100:.0f}% → "
            f"{best_r['pass_rate_cond']*100:.0f}%), reducing expected fee from "
            f"{baseline_fee} to {ef_str} per PASS. The ~{best_r['wait_weeks']:.1f}-week average "
            f"wait between eligible starts is worthwhile given the dramatically lower cost per "
            f"funded account — roughly {(1/best_r['pass_rate_cond']):.1f} attempts vs "
            f"{(1/base_r['pass_rate_cond']):.1f} at baseline."
        )
    else:
        print(
            f"  Economic reasoning: The regime filter provides minimal lift at this threshold "
            f"({lift:+.0%} pass rate improvement). Calendar regime is predictive but the 44-sim "
            f"sample may be too small for a robust threshold. Monitor live outcomes before relying "
            f"on this filter operationally."
        )
    return best_thr


def plot_regime_calendar(
    prices: pd.DataFrame,
    scores_df: pd.DataFrame,
    base_df: pd.DataFrame,
    best_thr: float,
    save_path: Path,
) -> None:
    """
    Step 5: BTC price with green/red week backgrounds, PASS/FAIL markers,
    regime_score for each Monday, and a current-regime vertical line.
    """
    btc_col  = "BTC-USD" if "BTC-USD" in prices.columns else prices.columns[0]
    btc_full = prices[btc_col].dropna()

    # Restrict to plot window
    plot_start = pd.Timestamp("2025-01-01")
    plot_end   = pd.Timestamp(TODAY_DATE)
    btc        = btc_full.loc[plot_start:plot_end]

    fig, (ax_price, ax_score) = plt.subplots(
        2, 1, figsize=(16, 9), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.06},
    )
    fig.suptitle(
        f"TSMOM v2 — Regime Filter Launch Calendar  (threshold = {best_thr:.2f})",
        fontsize=13, fontweight="bold",
    )

    # ── Coloured week backgrounds ────────────────────────────────────────────
    monday_dates = pd.date_range(start=plot_start, end=plot_end, freq="W-MON")
    for i, mon in enumerate(monday_dates):
        week_end = mon + pd.Timedelta(days=6)
        rs  = scores_df.loc[mon, "regime_score"] if mon in scores_df.index else None
        col = ("#d5f5e3" if (rs is not None and rs >= best_thr) else "#fadbd8")
        ax_price.axvspan(mon, min(week_end, plot_end), facecolor=col, alpha=0.35, linewidth=0)
        ax_score.axvspan(mon, min(week_end, plot_end), facecolor=col, alpha=0.35, linewidth=0)

    # ── BTC price ─────────────────────────────────────────────────────────────
    ax_price.plot(btc.index, btc.values, color="#2c3e50", lw=1.4, zorder=3)
    ax_price.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax_price.set_ylabel("BTC Price (USD)", fontsize=10)
    ax_price.grid(True, alpha=0.2)

    # ── PASS / FAIL markers ───────────────────────────────────────────────────
    for sd, row in base_df.iterrows():
        if sd < plot_start or sd > plot_end:
            continue
        btc_price_at_sd = btc.loc[sd] if sd in btc.index else None
        if btc_price_at_sd is None:
            continue
        if row["outcome"] == "PASS":
            ax_price.scatter(sd, btc_price_at_sd, marker="*", s=160,
                             color="#27ae60", zorder=5, linewidths=0)
        else:
            ax_price.scatter(sd, btc_price_at_sd, marker="x", s=60,
                             color="#c0392b", zorder=5, linewidths=1.5)

    # ── Regime score bar chart ────────────────────────────────────────────────
    plot_scores = scores_df[scores_df.index.isin(monday_dates)]
    bar_colors  = ["#27ae60" if s >= best_thr else "#e74c3c"
                   for s in plot_scores["regime_score"]]
    ax_score.bar(plot_scores.index, plot_scores["regime_score"],
                 width=4, color=bar_colors, alpha=0.8, zorder=3)
    ax_score.axhline(best_thr, color="navy", lw=1.2, linestyle="--",
                     label=f"Threshold ({best_thr:.2f})")
    ax_score.set_ylim(0, 1.05)
    ax_score.set_ylabel("Regime\nScore", fontsize=9)
    ax_score.legend(fontsize=8, loc="upper right")
    ax_score.grid(True, alpha=0.2)

    # ── Today vertical line ───────────────────────────────────────────────────
    today_ts   = pd.Timestamp(TODAY_DATE)
    today_rs   = compute_regime_score(prices, today_ts, _load_btc_funding())
    go_label   = "GO" if today_rs["regime_score"] >= best_thr else "WAIT"
    for ax in (ax_price, ax_score):
        ax.axvline(today_ts, color="purple", lw=1.5, linestyle="--", zorder=6)
    ax_price.annotate(
        f"Today ({TODAY_DATE})\nscore={today_rs['regime_score']:.2f} [{go_label}]",
        xy=(today_ts, btc.iloc[-1]),
        xytext=(today_ts - pd.Timedelta(days=50), btc.iloc[-1] * 1.04),
        fontsize=8, color="purple", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="purple", lw=1),
    )

    # ── Legend ────────────────────────────────────────────────────────────────
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_h = [
        Patch(facecolor="#d5f5e3", alpha=0.7, label=f"Regime GO (score≥{best_thr:.2f})"),
        Patch(facecolor="#fadbd8", alpha=0.7, label="Regime WAIT"),
        Line2D([0],[0], marker="*", color="w", markerfacecolor="#27ae60", markersize=10, label="PASS sim"),
        Line2D([0],[0], marker="x", color="#c0392b", markersize=7, lw=0, label="FAIL sim", markeredgewidth=1.5),
    ]
    ax_price.legend(handles=legend_h, fontsize=8, loc="upper left", framealpha=0.9)

    ax_score.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %Y"))
    plt.setp(ax_score.xaxis.get_majorticklabels(), rotation=30, ha="right")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nRegime calendar saved → {save_path}")


def print_current_regime(
    prices: pd.DataFrame,
    best_thr: float,
) -> None:
    """Step 6: Print today's regime check and launch recommendation."""
    today    = pd.Timestamp(TODAY_DATE)
    funding  = _load_btc_funding()
    r        = compute_regime_score(prices, today, funding)

    btc_col  = "BTC-USD" if "BTC-USD" in prices.columns else prices.columns[0]
    btc_now  = float(prices.loc[:today, btc_col].dropna().iloc[-1])
    btc_hist = prices.loc[:today, btc_col].dropna()
    ma50_val = float(btc_hist.rolling(50).mean().iloc[-1])
    ma20_val = float(btc_hist.rolling(20).mean().iloc[-1])

    go = r["regime_score"] >= best_thr

    print(f"\n{'='*60}")
    print(f"CURRENT REGIME ({TODAY_DATE}):")
    print(f"{'='*60}")
    print(f"  BTC above MA50   : {'YES' if r['btc_above_ma50'] else 'NO'} "
          f"(BTC=${btc_now:,.0f}, MA50=${ma50_val:,.0f})")
    print(f"  BTC above MA20   : {'YES' if r['btc_above_ma20'] else 'NO'} "
          f"(MA20=${ma20_val:,.0f})")
    slope_pct = r["btc_ma_slope"] * 100
    print(f"  MA20 slope       : {slope_pct:+.2f}% (last 5 days)")
    vp = r["vol_percentile"]
    vv = r["realized_vol_20d"]
    print(f"  Realized vol 20d : {vv:.0%} ({vp:.0%} percentile vs past year)")
    if r["avg_funding_7d"] is not None:
        print(f"  Funding 7d avg   : {r['avg_funding_7d']:+.6f} per hour")
    else:
        print(f"  Funding 7d avg   : n/a (cache not found)")
    print(f"  Regime score     : {r['regime_score']:.2f} / 1.00")
    print()
    print(f"  → LAUNCH: {'YES ✓' if go else 'NO ✗'}  (threshold = {best_thr:.2f})")
    print()
    if go:
        print(f"  Implication: Current BTC regime is trending and within normal volatility — "
              f"favorable conditions for TSMOM v2 momentum to generate returns above the 3% daily limit.")
    else:
        missing = []
        if not r["btc_above_ma50"]:     missing.append("BTC below 50-day MA")
        if not r["btc_above_ma20"]:     missing.append("BTC below 20-day MA")
        if r["btc_ma_slope"] <= 0:      missing.append("downward MA slope")
        if r["vol_percentile"] >= 0.60: missing.append("elevated volatility")
        print(f"  Implication: Current regime is unfavorable ({', '.join(missing) if missing else 'composite score too low'}) — "
              f"daily limit breach probability is elevated; recommend waiting for trend confirmation before starting a challenge.")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — ANALYSIS & OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Print structured simulation summary."""
    pass_m = df["outcome"] == "PASS"
    fail_m = df["outcome"] == "FAIL"
    inc_m  = df["outcome"] == "INCOMPLETE"
    n = len(df)

    print("\n" + "=" * 60)
    print("CHALLENGE SIMULATION RESULTS — TSMOM v2 on Propr $5,000")
    print("=" * 60)
    print(f"Total simulations    : {n}")
    print(f"PASS                 : {pass_m.sum():>3d}  ({pass_m.sum()/n:.0%})")
    print(f"FAIL                 : {fail_m.sum():>3d}  ({fail_m.sum()/n:.0%})")
    print(f"  → daily limit      : {(df['fail_reason']=='daily_limit').sum():>3d}")
    print(f"  → total drawdown   : {(df['fail_reason']=='total_drawdown').sum():>3d}")
    print(f"INCOMPLETE           : {inc_m.sum():>3d}  ({inc_m.sum()/n:.0%})")

    if pass_m.any():
        print(f"\nAvg days to PASS     : {df.loc[pass_m,'days_elapsed'].mean():.1f} days")
    if fail_m.any():
        print(f"Avg days to FAIL     : {df.loc[fail_m,'days_elapsed'].mean():.1f} days")
    print(f"Median peak equity   : ${df['peak_equity'].median():>8,.2f}")
    print(f"Median max drawdown  : -{df['max_drawdown_pct'].median():.1%}")

    if pass_m.any():
        best = df.loc[pass_m].loc[df.loc[pass_m, "days_elapsed"].idxmin()]
        print(f"\nBest start date  : {best['start_date'].date()} "
              f"(passed in {int(best['days_elapsed'])} days, "
              f"peak ${best['peak_equity']:,.0f})")
    if fail_m.any():
        worst = df.loc[fail_m].loc[df.loc[fail_m, "max_drawdown_pct"].idxmax()]
        print(f"Worst start date : {worst['start_date'].date()} "
              f"(failed in {int(worst['days_elapsed'])} days, "
              f"-{worst['max_drawdown_pct']:.1%} DD)")

    # Per-simulation table
    print("\n" + "-" * 75)
    hdr = f"{'start_date':>12} {'outcome':>10} {'days':>6} {'final_equity':>12} {'max_dd':>8} {'fail_reason':>14}"
    print(hdr)
    print("-" * 75)
    for _, row in df.iterrows():
        fr = row["fail_reason"] if pd.notna(row["fail_reason"]) else "-"
        print(f"  {str(row['start_date'].date()):>10} {row['outcome']:>10} "
              f"{int(row['days_elapsed']):>6} "
              f"${row['final_equity']:>10,.2f} "
              f"{-row['max_drawdown_pct']:>7.1%} "
              f"{fr:>14}")
    print("-" * 75)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — EQUITY CURVES PLOT
# ─────────────────────────────────────────────────────────────────────────────

def plot_equity_curves(results: list[dict[str, Any]], save_path: Path) -> None:
    """
    One equity curve per simulation. PASS=green, FAIL=red, INCOMPLETE=orange.
    Dashed reference lines at $5,500 (target) and $4,700 (max drawdown).
    X-axis: days elapsed; Y-axis: account equity in USDC.
    """
    color_map = {"PASS": "#2ecc71", "FAIL": "#e74c3c", "INCOMPLETE": "#f39c12"}
    alpha_map = {"PASS": 0.55, "FAIL": 0.55, "INCOMPLETE": 0.45}
    counts    = {k: sum(1 for r in results if r["outcome"] == k)
                 for k in ("PASS", "FAIL", "INCOMPLETE")}

    fig, ax = plt.subplots(figsize=(14, 7))

    for r in results:
        curve = r["equity_curve"]
        ax.plot(
            range(len(curve)), curve,
            color=color_map[r["outcome"]],
            alpha=alpha_map[r["outcome"]],
            lw=0.9,
        )

    ax.axhline(5500, color="#27ae60", ls="--", lw=1.6, zorder=5)
    ax.axhline(4700, color="#c0392b", ls="--", lw=1.6, zorder=5)
    ax.axhline(5000, color="#7f8c8d", ls=":",  lw=1.0, zorder=5)

    legend_handles = [
        Line2D([0],[0], color=color_map["PASS"],       lw=2,   label=f"PASS ({counts['PASS']})"),
        Line2D([0],[0], color=color_map["FAIL"],       lw=2,   label=f"FAIL ({counts['FAIL']})"),
        Line2D([0],[0], color=color_map["INCOMPLETE"], lw=2,   label=f"INCOMPLETE ({counts['INCOMPLETE']})"),
        Line2D([0],[0], color="#27ae60", ls="--", lw=1.5, label="Profit target ($5,500)"),
        Line2D([0],[0], color="#c0392b", ls="--", lw=1.5, label="Max drawdown  ($4,700)"),
        Line2D([0],[0], color="#7f8c8d", ls=":",  lw=1.0, label="Starting equity ($5,000)"),
    ]
    ax.legend(handles=legend_handles, fontsize=9, loc="upper left", framealpha=0.9)

    ax.set_xlabel("Days elapsed since challenge start", fontsize=11)
    ax.set_ylabel("Account equity (USDC)", fontsize=11)
    ax.set_title(
        "TSMOM v2 — Propr Challenge Simulations\n"
        "(all Monday starts, 2025-01-06 to 2025-11-03)",
        fontsize=13,
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nChart saved → {save_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    prices = download_data(UNIVERSE, DATA_START, DATA_END)

    # ── Vol target sweep ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("VOL TARGET SWEEP")
    print("=" * 60)
    sweep   = run_vol_sweep(prices, VOL_TARGETS)
    best_vt = print_sweep_table(sweep)

    best_df, best_results = sweep[best_vt]
    print_regime_analysis(best_df, best_vt)

    sweep_chart = OUT_DIR / "vol_target_sweep.png"
    plot_vol_sweep(sweep, best_vt, sweep_chart)

    # ── Regime filter analysis ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("REGIME FILTER ANALYSIS")
    print("=" * 60)
    thr_results, scores_df, base_df = run_regime_sweep(prices)
    best_thr = print_regime_sweep_table(thr_results, scores_df, base_df)

    cal_path = OUT_DIR / "regime_calendar.png"
    plot_regime_calendar(prices, scores_df, base_df, best_thr, cal_path)

    print_current_regime(prices, best_thr)

    # ── Original single-run summary (vol_target=0.15) ──────────────────────
    print("\n" + "=" * 60)
    print("ORIGINAL SIMULATION (vol_target=0.15)")
    print("=" * 60)
    df_orig, results_orig = run_all_simulations(prices, vol_target=0.15, verbose=True)
    print_summary(df_orig)
    chart_path = OUT_DIR / "challenge_simulation.png"
    plot_equity_curves(results_orig, chart_path)


if __name__ == "__main__":
    main()
