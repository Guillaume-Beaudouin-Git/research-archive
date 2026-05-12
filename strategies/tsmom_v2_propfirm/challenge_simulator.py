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
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Run simulate_challenge for every Monday start date in [SIM_START, SIM_END].
    Returns (summary_df, full_results_list).
    """
    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    print(f"\nRunning {len(start_dates)} simulations "
          f"({start_dates[0].date()} → {start_dates[-1].date()})...")

    all_results: list[dict[str, Any]] = []
    for sd in start_dates:
        print(f"  Simulating start_date {sd.date()}...")
        all_results.append(simulate_challenge(sd, prices))

    rows = [{k: v for k, v in r.items() if k != "equity_curve"} for r in all_results]
    return pd.DataFrame(rows), all_results


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
    df, results = run_all_simulations(prices)
    print_summary(df)
    chart_path = OUT_DIR / "challenge_simulation.png"
    plot_equity_curves(results, chart_path)


if __name__ == "__main__":
    main()
