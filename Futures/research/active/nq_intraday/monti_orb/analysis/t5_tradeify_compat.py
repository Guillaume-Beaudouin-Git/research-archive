"""
T5 — Tradeify compatibility (trailing DD simulator).

Simulates Tradeify $25K eval challenge with 3 MNQ contracts (= 0.3 NQ equivalent).
Scale factor: 3 MNQ = 0.3 × NQ P&L (MNQ is 1/10 of NQ).

Tradeify eval config (from CLAUDE.md, confirmed 2026-05-25):
  Starting balance:  $25,000
  Trailing DD:       $1,000 (from peak)
  Daily DD:          not binding (no explicit daily limit for eval)
  Lock trigger:      $26,100 (capital + DD + $100 buffer)
  Profit target:     ~$1,500 (implied 6%)

Monte Carlo: 10,000 paths × bootstrap resampling from trade P&L distribution.
Sizing: 3 MNQ = 0.3 × NQ contract, so all NQ P&L × 0.3 for MNQ sizing.

Compares to iter_10 reference P(pass) ≈ 27% (from sizing_analysis.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    daily_returns,
)

# Tradeify eval config (confirmed 2026-05-25 — DO NOT revert)
TRADEIFY_START       = 25_000.0
TRADEIFY_TRAIL_DD    = 1_000.0   # trailing DD from peak
TRADEIFY_PROFIT_TGT  = 1_500.0   # approximate profit target
TRADEIFY_LOCK_THRESH = 26_100.0  # lock trigger (start + 1000 + 100 buffer)
TRADEIFY_MAX_DAYS    = 30        # max eval days

MNQ_SCALE  = 0.3   # 3 MNQ contracts = 0.3 NQ
MC_PATHS   = 10_000
SEED       = 42


def _simulate_eval(trade_pnl_mnq: np.ndarray, n_paths: int, seed: int) -> dict:
    """
    Bootstrap Monte Carlo for Tradeify eval.
    Each path: sample with replacement until profit target, bust, or max_days.
    """
    rng      = np.random.default_rng(seed)
    n_trades = len(trade_pnl_mnq)
    if n_trades == 0:
        return {"p_pass": 0.0, "p_bust": 0.0}

    n_pass = 0
    n_bust = 0
    days_to_pass_list: list[int] = []

    for _ in range(n_paths):
        equity = TRADEIFY_START
        peak   = equity
        day    = 0
        result = "timeout"

        while day < TRADEIFY_MAX_DAYS:
            # Sample 0 or 1 trade per day (Monti trades ~every day)
            daily = float(rng.choice(trade_pnl_mnq))
            equity += daily
            day    += 1

            if equity > peak:
                peak = equity

            # Check bust: trailing DD from peak
            if equity <= peak - TRADEIFY_TRAIL_DD:
                result = "bust"
                break

            # Check pass
            if equity >= TRADEIFY_START + TRADEIFY_PROFIT_TGT:
                result = "pass"
                days_to_pass_list.append(day)
                break

        if result == "pass":
            n_pass += 1
        elif result == "bust":
            n_bust += 1

    return {
        "p_pass":        n_pass / n_paths,
        "p_bust":        n_bust / n_paths,
        "p_timeout":     1 - n_pass / n_paths - n_bust / n_paths,
        "median_days":   int(np.median(days_to_pass_list)) if days_to_pass_list else None,
    }


def run(trades=None) -> dict:
    print("=" * 60)
    print("T5 — Tradeify $25K eval compatibility (3 MNQ = 0.3 NQ)")
    print("=" * 60)

    df = load_nq_1min()
    if trades is None:
        trades = monti_orb_signal(df)

    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")
    tl, dn = daily_returns(trades, sizing="fixed", n_contracts_fixed=1, rf_series=rf["dtb3"])

    if tl.empty:
        print("[T5] No trades")
        return {"test": "T5", "p_pass": None}

    # Per-trade P&L in MNQ units (0.3 × NQ)
    trade_pnl_nq   = tl["net_usd"].values
    trade_pnl_mnq  = trade_pnl_nq * MNQ_SCALE

    print(f"\nTrade count: {len(trade_pnl_mnq)}")
    print(f"MNQ P&L stats:  mean=${trade_pnl_mnq.mean():,.2f}  "
          f"std=${trade_pnl_mnq.std():,.2f}  "
          f"min=${trade_pnl_mnq.min():,.2f}  "
          f"max=${trade_pnl_mnq.max():,.2f}")

    # Worst single-day loss
    worst_day_mnq = float(dn.min()) * MNQ_SCALE
    print(f"Worst single day (MNQ): ${worst_day_mnq:,.2f}  "
          f"(vs Tradeify trail DD $1,000)")

    # DD distribution (equity curve from TRADEIFY_START)
    equity    = TRADEIFY_START + (dn * MNQ_SCALE).cumsum()
    dd_series = equity - equity.cummax()
    print(f"Max historical DD (MNQ): ${float(dd_series.min()):,.2f}")
    print(f"DD > $1,000 days: {int((dd_series < -TRADEIFY_TRAIL_DD).sum())}")

    # Monte Carlo
    print(f"\nRunning Monte Carlo ({MC_PATHS:,} paths)…")
    mc_all = _simulate_eval(trade_pnl_mnq, MC_PATHS, SEED)

    # Also simulate including no-trade days (all daily net including zeros)
    daily_all = (dn * MNQ_SCALE).values
    mc_daily = _simulate_eval(daily_all, MC_PATHS, SEED + 1)

    print(f"\nMC (trade-based resampling):")
    print(f"  P(pass):    {mc_all['p_pass']:.1%}")
    print(f"  P(bust):    {mc_all['p_bust']:.1%}")
    print(f"  P(timeout): {mc_all['p_timeout']:.1%}")
    if mc_all["median_days"]:
        print(f"  Median days to pass: {mc_all['median_days']}")

    print(f"\nMC (daily resampling, includes no-trade days):")
    print(f"  P(pass):    {mc_daily['p_pass']:.1%}")
    print(f"  P(bust):    {mc_daily['p_bust']:.1%}")

    ref_iter10 = 0.27
    print(f"\niter_10 reference P(pass): {ref_iter10:.1%}")
    if mc_all["p_pass"] > ref_iter10:
        print(f"[T5] Monti ORB has HIGHER eval pass rate than iter_10")
    else:
        print(f"[T5] Monti ORB has LOWER eval pass rate than iter_10")

    result = {
        "test":                 "T5",
        "worst_day_mnq_usd":    round(float(worst_day_mnq), 2),
        "max_hist_dd_mnq":      round(float(dd_series.min()) * MNQ_SCALE, 2),
        "mc_trade_p_pass":      round(mc_all["p_pass"], 4),
        "mc_trade_p_bust":      round(mc_all["p_bust"], 4),
        "mc_daily_p_pass":      round(mc_daily["p_pass"], 4),
        "mc_daily_p_bust":      round(mc_daily["p_bust"], 4),
        "iter10_ref_p_pass":    ref_iter10,
        "better_than_iter10":   bool(mc_all["p_pass"] > ref_iter10),
    }
    return result


if __name__ == "__main__":
    run()
