#!/usr/bin/env python
"""
Breakout Challenge Simulator — TSMOM v2.

2-step challenge:
  Phase 1: +10% profit target, 10% max DD, 5% daily limit
  Phase 2: +5%  profit target, 10% max DD, 5% daily limit
  Capital: $10,000 (Explorer), $100 fee, 80% profit split

Run: python -m strategies.tsmom_v2_propfirm.breakout_simulator
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

warnings.filterwarnings("ignore")

# ── Import from existing modules ──────────────────────────────────────────────
from strategies.tsmom_v2_propfirm.challenge_simulator import (
    download_data,
    run_all_simulations as run_propr_simulations,
    SIM_START, SIM_END, UNIVERSE, DATA_START, DATA_END,
)

try:
    from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance
    from strategies.tsmom_v2_propfirm.sizing import compute_vol_scalars, compute_positions
    from strategies.tsmom_v2_propfirm.config import VOL_LOOKBACK_DAYS
except ImportError:
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
OUT_DIR         = Path(__file__).parent
BREAKOUT_FEE    = 100.0    # $ per attempt
PROPR_FEE       = 60.0
PROPR_CAPITAL   = 5_000.0
BREAKOUT_CAPITAL = 10_000.0
PROFIT_SPLIT    = 0.80

BREAKOUT_VOL_TARGETS = [0.10, 0.15, 0.20, 0.25, 0.30]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — SIMULATE ONE BREAKOUT CHALLENGE
# ─────────────────────────────────────────────────────────────────────────────

def _dd_from_curve(curve: list[float]) -> float:
    """Max drawdown (as positive fraction) from an equity list."""
    if len(curve) < 2:
        return 0.0
    arr  = np.array(curve)
    peak = np.maximum.accumulate(arr)
    return float(-((arr - peak) / peak).min())


def simulate_breakout_challenge(
    start_date: pd.Timestamp,
    prices: pd.DataFrame,
    initial_equity: float = 10_000.0,
    phase1_target_pct: float = 0.10,
    phase2_target_pct: float = 0.05,
    max_drawdown_pct: float = 0.10,
    daily_loss_limit_pct: float = 0.05,
    vol_target: float = 0.15,
    costs_per_leg: float = 0.00045,
) -> dict[str, Any]:
    """
    Simulate one Breakout 2-step challenge starting on start_date.

    Phase 1: equity = initial_equity, target = +10%, fail at -10% DD or -5% daily.
    Phase 2: equity resets to initial_equity (positions carried), target = +5%,
             same DD/daily limits. Starts on the day after Phase 1 passes.

    Returns a result dict with per-phase stats and equity curves.
    """
    log_ret      = np.log(prices / prices.shift(1))
    signals      = compute_signal(prices)
    vol_scalars  = compute_vol_scalars(log_ret, vol_target, VOL_LOOKBACK_DAYS)
    pos_sizes    = compute_positions(signals, vol_scalars)
    weekly_sizes = apply_weekly_rebalance(pos_sizes)

    sim_dates = prices.index[prices.index >= start_date]
    n         = len(sim_dates)

    phase            = 1
    equity: float    = initial_equity
    hwm: float       = initial_equity
    positions: dict[str, float] = {}

    equity_curve_p1: list[float] = [initial_equity]
    equity_curve_p2: list[float] = []

    p1_outcome        = "INCOMPLETE"
    p1_days           = 0
    p1_peak           = initial_equity
    p1_daily_breaches = 0
    p2_outcome        = "NOT_REACHED"
    p2_days           = 0
    p2_daily_breaches = 0
    p2_start_i: int   = -1

    for i, date in enumerate(sim_dates):

        # ── Phase 2 equity reset at first Phase 2 day ────────────────────────
        if phase == 2 and i == p2_start_i:
            equity = initial_equity
            hwm    = initial_equity

        eq_day_start = equity

        # ── 1. MTM on carried positions ───────────────────────────────────────
        if i > 0 and positions:
            prev = sim_dates[i - 1]
            for ticker, qty in positions.items():
                if ticker not in prices.columns:
                    continue
                p_now  = prices.at[date, ticker]
                p_prev = prices.at[prev,  ticker]
                if not (pd.isna(p_now) or pd.isna(p_prev)):
                    equity += qty * (p_now - p_prev)

        # ── 2. Weekly rebalance on Mondays ────────────────────────────────────
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

            total_notional = sum(target.values())
            if total_notional > equity * 0.90:
                scale  = equity * 0.90 / total_notional
                target = {k: v * scale for k, v in target.items()}

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

        # ── 3. Daily loss limit ────────────────────────────────────────────────
        if i > 0 and eq_day_start != 0:
            if (equity - eq_day_start) / eq_day_start < -daily_loss_limit_pct:
                if phase == 1:
                    p1_daily_breaches = 1
                    equity_curve_p1.append(equity)
                    return _build_breakout_result(
                        start_date, "FAIL", "daily_limit", i,
                        p1_peak, equity_curve_p1,
                        "NOT_REACHED", None, 0, [], i,
                    )
                else:
                    p2_daily_breaches = 1
                    equity_curve_p2.append(equity)
                    return _build_breakout_result(
                        start_date, "PASS", None, p1_days,
                        p1_peak, equity_curve_p1,
                        "FAIL", "daily_limit", i - p2_start_i, equity_curve_p2,
                        i,
                    )

        # ── 4. Total drawdown vs HWM ──────────────────────────────────────────
        if equity <= hwm * (1.0 - max_drawdown_pct):
            if phase == 1:
                equity_curve_p1.append(equity)
                return _build_breakout_result(
                    start_date, "FAIL", "total_drawdown", i,
                    p1_peak, equity_curve_p1,
                    "NOT_REACHED", None, 0, [], i,
                )
            else:
                equity_curve_p2.append(equity)
                return _build_breakout_result(
                    start_date, "PASS", None, p1_days,
                    p1_peak, equity_curve_p1,
                    "FAIL", "total_drawdown", i - p2_start_i, equity_curve_p2,
                    i,
                )

        # ── 5. Profit target ──────────────────────────────────────────────────
        target_pct = phase1_target_pct if phase == 1 else phase2_target_pct
        if equity >= hwm * (1.0 + target_pct):
            if phase == 1:
                p1_days = i
                p1_peak = max(p1_peak, equity)
                equity_curve_p1.append(equity)
                # Check if Phase 2 can start
                if i + 1 >= n:
                    return _build_breakout_result(
                        start_date, "PASS", None, p1_days,
                        p1_peak, equity_curve_p1,
                        "NOT_REACHED", None, 0, [], i,
                    )
                # Transition to Phase 2 (next iteration resets equity/hwm)
                phase      = 2
                p2_start_i = i + 1
                equity_curve_p2 = [initial_equity]
                continue   # skip end-of-loop appends
            else:
                p2_days = i - p2_start_i
                equity_curve_p2.append(equity)
                return _build_breakout_result(
                    start_date, "PASS", None, p1_days,
                    p1_peak, equity_curve_p1,
                    "PASS", None, p2_days, equity_curve_p2,
                    i,
                )

        if equity > p1_peak and phase == 1:
            p1_peak = equity

        if phase == 1:
            equity_curve_p1.append(equity)
        else:
            equity_curve_p2.append(equity)

    # ── Ran out of data ───────────────────────────────────────────────────────
    if phase == 1:
        p1_outcome = "INCOMPLETE"
        p1_days    = n
        equity_curve_p1.append(equity)
        return _build_breakout_result(
            start_date, "INCOMPLETE", None, n,
            p1_peak, equity_curve_p1,
            "NOT_REACHED", None, 0, [], n,
        )
    else:
        p2_days = n - p2_start_i
        equity_curve_p2.append(equity)
        return _build_breakout_result(
            start_date, "PASS", None, p1_days,
            p1_peak, equity_curve_p1,
            "INCOMPLETE", None, p2_days, equity_curve_p2,
            n,
        )


def _build_breakout_result(
    start_date: pd.Timestamp,
    p1_outcome: str,
    p1_fail_reason: str | None,
    p1_days: int,
    p1_peak: float,
    ec_p1: list[float],
    p2_outcome: str,
    p2_fail_reason: str | None,
    p2_days: int,
    ec_p2: list[float],
    total_days: int,
) -> dict[str, Any]:
    """Assemble result dict with derived statistics."""
    p1_max_dd = _dd_from_curve(ec_p1)
    p2_max_dd = _dd_from_curve(ec_p2) if ec_p2 else 0.0

    overall = "FULL_PASS" if (p1_outcome == "PASS" and p2_outcome == "PASS") else "FAIL"

    return {
        "start_date":           start_date,
        "phase1_outcome":       p1_outcome,
        "phase1_fail_reason":   p1_fail_reason,
        "phase1_days":          p1_days,
        "phase1_peak_equity":   round(p1_peak, 2),
        "phase1_max_dd":        p1_max_dd,
        "phase1_daily_breaches": 1 if p1_fail_reason == "daily_limit" else 0,
        "phase2_outcome":       p2_outcome,
        "phase2_fail_reason":   p2_fail_reason,
        "phase2_days":          p2_days,
        "phase2_max_dd":        p2_max_dd,
        "phase2_daily_breaches": 1 if p2_fail_reason == "daily_limit" else 0,
        "overall_outcome":      overall,
        "total_days":           total_days,
        "equity_curve_p1":      ec_p1,
        "equity_curve_p2":      ec_p2,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — RUN ALL 44 SIMULATIONS
# ─────────────────────────────────────────────────────────────────────────────

def run_all_breakout_sims(
    prices: pd.DataFrame,
    vol_target: float = 0.15,
    verbose: bool = True,
) -> list[dict[str, Any]]:
    """Run simulate_breakout_challenge for all 44 Monday start dates."""
    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    if verbose:
        print(f"  Running {len(start_dates)} sims "
              f"({start_dates[0].date()} → {start_dates[-1].date()})...", flush=True)
    return [simulate_breakout_challenge(sd, prices, vol_target=vol_target)
            for sd in start_dates]


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — VOL TARGET SWEEP
# ─────────────────────────────────────────────────────────────────────────────

def _breakout_sweep_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute sweep statistics for one vol_target's 44 simulations."""
    n = len(results)

    p1_passes  = [r for r in results if r["phase1_outcome"] == "PASS"]
    p2_reached = [r for r in results if r["phase2_outcome"] != "NOT_REACHED"]
    p2_passes  = [r for r in results if r["phase2_outcome"] == "PASS"]
    full_passes = [r for r in results if r["overall_outcome"] == "FULL_PASS"]

    p1_rate   = len(p1_passes) / n
    p2_rate   = len(p2_passes) / len(p2_reached) if p2_reached else 0.0
    full_rate = len(full_passes) / n

    avg_days_p1  = float(np.mean([r["phase1_days"] for r in p1_passes]))  if p1_passes  else None
    avg_days_p2  = float(np.mean([r["phase2_days"] for r in p2_passes]))  if p2_passes  else None
    avg_total    = float(np.mean([r["total_days"]   for r in full_passes])) if full_passes else None

    breaches_p1  = sum(r["phase1_daily_breaches"] for r in results)
    breaches_p2  = sum(r["phase2_daily_breaches"] for r in p2_reached)

    exp_fee = (BREAKOUT_FEE / full_rate) if full_rate > 0 else float("inf")

    return {
        "n":              n,
        "p1_pass_count":  len(p1_passes),
        "p2_pass_count":  len(p2_passes),
        "full_pass_count": len(full_passes),
        "p1_pass_rate":   p1_rate,
        "p2_pass_rate":   p2_rate,
        "full_pass_rate": full_rate,
        "avg_days_p1":    avg_days_p1,
        "avg_days_p2":    avg_days_p2,
        "avg_total_days": avg_total,
        "breaches_p1":    breaches_p1,
        "breaches_p2":    breaches_p2,
        "exp_fee":        exp_fee,
    }


def run_breakout_vol_sweep(
    prices: pd.DataFrame,
    vol_targets: list[float] = BREAKOUT_VOL_TARGETS,
) -> dict[float, list[dict[str, Any]]]:
    """Run all 44 simulations for each vol_target. Returns {vol_target: results_list}."""
    sweep: dict[float, list[dict[str, Any]]] = {}
    for vt in vol_targets:
        print(f"Breakout sim vol={vt:.2f}: running 44 sims...", flush=True)
        sweep[vt] = run_all_breakout_sims(prices, vol_target=vt, verbose=False)
    return sweep


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — DIRECT COMPARISON WITH PROPR
# ─────────────────────────────────────────────────────────────────────────────

def _propr_metrics(vol_target: float = 0.15) -> dict[str, Any]:
    """Baseline Propr metrics (hardcoded from sweep results)."""
    # These match the challenge_simulator.py vol_sweep output
    PROPR = {
        0.10: {"pass_rate": 0.20, "avg_days_pass": 16.0, "fail_daily": 31, "exp_fee": 293},
        0.15: {"pass_rate": 0.34, "avg_days_pass": 27.5, "fail_daily": 26, "exp_fee": 176},
        0.20: {"pass_rate": 0.34, "avg_days_pass": 25.0, "fail_daily": 28, "exp_fee": 176},
        0.25: {"pass_rate": 0.34, "avg_days_pass": 25.0, "fail_daily": 28, "exp_fee": 176},
        0.30: {"pass_rate": 0.34, "avg_days_pass": 25.0, "fail_daily": 28, "exp_fee": 176},
    }
    return PROPR.get(vol_target, PROPR[0.15])


def print_comparison_table(
    breakout_sweep: dict[float, list[dict[str, Any]]],
    vol_target: float = 0.15,
) -> None:
    """Step 4: Side-by-side Propr vs Breakout comparison."""
    propr = _propr_metrics(vol_target)
    bm    = _breakout_sweep_metrics(breakout_sweep[vol_target])

    propr_pass_rate  = propr["pass_rate"]
    propr_avg_days   = propr["avg_days_pass"]
    propr_fail_daily = propr["fail_daily"]
    propr_exp_fee    = propr["exp_fee"]
    propr_payout     = PROPR_CAPITAL * 0.10 * PROFIT_SPLIT        # $400
    propr_roi        = propr_payout / propr_exp_fee

    bo_pass_rate  = bm["full_pass_rate"]
    bo_avg_days   = bm["avg_total_days"] or 0.0
    bo_fail_daily = bm["breaches_p1"] + bm["breaches_p2"]
    bo_exp_fee    = bm["exp_fee"]
    # Breakout payout = 80% of (Phase1 profit + Phase2 profit) minimum
    bo_payout     = (BREAKOUT_CAPITAL * (0.10 + 0.05)) * PROFIT_SPLIT  # $1200
    bo_roi        = bo_payout / bo_exp_fee if bo_exp_fee < 1e9 else 0.0

    print("\n" + "=" * 65)
    print(f"BREAKOUT vs PROPR — Direct Comparison (vol_target={vol_target})")
    print("=" * 65)
    rows = [
        ("Capital",            "$5,000",         "$10,000"),
        ("Challenge fee",      "$60",            "$100"),
        ("Profit split",       "80%",            "80%"),
        ("Max daily limit",    "3%",             "5%"),
        ("Max total DD",       "6%",             "10%"),
        ("Profit target",      "10% (1-step)",   "10%+5% (2-step)"),
        ("Pass rate",          f"{propr_pass_rate:.0%}", f"{bo_pass_rate:.0%}"),
        ("Avg days to pass",   f"{propr_avg_days:.0f}d", f"{bo_avg_days:.0f}d"),
        ("Daily limit fails",  f"{propr_fail_daily}/44", f"{bo_fail_daily}/44"),
        ("Expected fee to pass", f"${propr_exp_fee:.0f}", f"${bo_exp_fee:.0f}" if bo_exp_fee < 1e9 else "∞"),
        ("Min payout (1 pass)", f"${propr_payout:.0f} (80%×$500)", f"${bo_payout:.0f} (80%×$1500)"),
        ("Expected ROI on fees", f"{propr_roi:.2f}×",  f"{bo_roi:.2f}×" if bo_roi > 0 else "—"),
    ]
    print(f"  {'Metric':<25} | {'Propr Starter':>15} | {'Breakout Explorer':>17}")
    print(f"  {'-'*25}-+-{'-'*15}-+-{'-'*17}")
    for label, propr_val, bo_val in rows:
        print(f"  {label:<25} | {propr_val:>15} | {bo_val:>17}")
    print(f"  {'-'*63}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — CALENDAR & PHASE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def print_calendar_analysis(
    results: list[dict[str, Any]],
    vol_target: float,
) -> None:
    """Step 5: Monthly pass rates and Phase 2 funnel analysis."""
    print(f"\n{'='*65}")
    print(f"CALENDAR ANALYSIS — Breakout (vol_target={vol_target:.2f})")
    print(f"{'='*65}")

    # Monthly pass rates
    print("\n  Monthly pass rates (by challenge start month):")
    by_month: dict[str, list[dict]] = {}
    for r in results:
        key = r["start_date"].strftime("%Y-%m")
        by_month.setdefault(key, []).append(r)

    for month, sims in sorted(by_month.items()):
        n_m     = len(sims)
        n_p1    = sum(1 for r in sims if r["phase1_outcome"] == "PASS")
        n_full  = sum(1 for r in sims if r["overall_outcome"] == "FULL_PASS")
        pct_p1  = n_p1 / n_m * 100
        pct_fp  = n_full / n_m * 100
        bar_p1  = "█" * n_p1 + "░" * (n_m - n_p1)
        print(f"    {month}: P1={n_p1}/{n_m} ({pct_p1:.0f}%) FULL={n_full}/{n_m} ({pct_fp:.0f}%)  [{bar_p1}]")

    # Phase funnel
    n       = len(results)
    n_p1    = sum(1 for r in results if r["phase1_outcome"] == "PASS")
    n_p2r   = sum(1 for r in results if r["phase2_outcome"] != "NOT_REACHED")
    n_p2p   = sum(1 for r in results if r["phase2_outcome"] == "PASS")
    n_full  = sum(1 for r in results if r["overall_outcome"] == "FULL_PASS")

    print(f"\n  Phase funnel (all {n} sims):")
    print(f"    Phase 1 started   : {n:>3} ({n/n:.0%})")
    print(f"    Phase 1 PASS      : {n_p1:>3} ({n_p1/n:.0%})")
    print(f"    Phase 2 reached   : {n_p2r:>3} ({n_p2r/n:.0%})")
    print(f"    Phase 2 PASS      : {n_p2p:>3} ({n_p2p/n:.0%}  of all | "
          f"{n_p2p/n_p2r:.0%} of reached)" if n_p2r else "    Phase 2 PASS      :   0")
    print(f"    FULL PASS         : {n_full:>3} ({n_full/n:.0%})")

    # P1-pass but P2-fail starts
    p1p_p2f = [r for r in results if r["phase1_outcome"] == "PASS" and r["phase2_outcome"] == "FAIL"]
    if p1p_p2f:
        print(f"\n  Phase 1 PASS → Phase 2 FAIL ({len(p1p_p2f)} sims):")
        for r in sorted(p1p_p2f, key=lambda r: r["start_date"]):
            fr = r["phase2_fail_reason"] or "-"
            print(f"    {r['start_date'].date()}  P1 passed in {r['phase1_days']:>3}d  "
                  f"P2 failed in {r['phase2_days']:>3}d ({fr})")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — EQUITY CURVE PLOT
# ─────────────────────────────────────────────────────────────────────────────

def plot_breakout_simulation(
    breakout_sweep: dict[float, list[dict[str, Any]]],
    save_path: Path,
    vol_target_plot: float = 0.15,
) -> None:
    """Step 6: 3-subplot chart."""
    vts     = sorted(breakout_sweep.keys())
    results = breakout_sweep[vol_target_plot]

    fig, axes = plt.subplots(3, 1, figsize=(14, 14),
                             gridspec_kw={"height_ratios": [3, 2, 2], "hspace": 0.35})
    fig.suptitle(
        f"Breakout Challenge Simulator — TSMOM v2 (vol_target={vol_target_plot})",
        fontsize=13, fontweight="bold",
    )

    # ── Top: equity curves ────────────────────────────────────────────────────
    ax = axes[0]
    color_map = {"FULL_PASS": "#2ecc71", "P1_PASS_P2_FAIL": "#f39c12", "P1_FAIL": "#e74c3c"}
    count_map = {"FULL_PASS": 0, "P1_PASS_P2_FAIL": 0, "P1_FAIL": 0}

    for r in results:
        ec_p1 = r["equity_curve_p1"]
        ec_p2 = r["equity_curve_p2"]
        if r["overall_outcome"] == "FULL_PASS":
            key   = "FULL_PASS"
            color = color_map["FULL_PASS"]
        elif r["phase1_outcome"] == "PASS":
            key   = "P1_PASS_P2_FAIL"
            color = color_map["P1_PASS_P2_FAIL"]
        else:
            key   = "P1_FAIL"
            color = color_map["P1_FAIL"]
        count_map[key] += 1

        # Plot P1 curve; P2 continues on the time axis after P1
        x1 = range(len(ec_p1))
        ax.plot(x1, ec_p1, color=color, alpha=0.50, lw=0.9)
        if ec_p2:
            x2 = range(len(ec_p1) - 1, len(ec_p1) - 1 + len(ec_p2))
            # Draw P2 reset as a dotted drop at Phase 1→2 boundary
            ax.plot([len(ec_p1) - 1, len(ec_p1) - 1],
                    [ec_p1[-1], ec_p2[0]], color=color, alpha=0.4, lw=0.7, ls=":")
            ax.plot(x2, ec_p2, color=color, alpha=0.50, lw=0.9)

    ax.axhline(11000, color="#27ae60", ls="--", lw=1.5, zorder=5)
    ax.axhline(10500, color="#2980b9", ls="--", lw=1.5, zorder=5)
    ax.axhline(9000,  color="#c0392b", ls="--", lw=1.5, zorder=5)
    ax.axhline(10000, color="#7f8c8d", ls=":",  lw=1.0, zorder=5)

    legend_h = [
        Line2D([0],[0], color=color_map["FULL_PASS"],       lw=2, label=f"FULL PASS ({count_map['FULL_PASS']})"),
        Line2D([0],[0], color=color_map["P1_PASS_P2_FAIL"], lw=2, label=f"P1 PASS / P2 FAIL ({count_map['P1_PASS_P2_FAIL']})"),
        Line2D([0],[0], color=color_map["P1_FAIL"],         lw=2, label=f"P1 FAIL ({count_map['P1_FAIL']})"),
        Line2D([0],[0], color="#27ae60", ls="--", lw=1.5, label="Phase 1 target ($11,000)"),
        Line2D([0],[0], color="#2980b9", ls="--", lw=1.5, label="Phase 2 target ($10,500)"),
        Line2D([0],[0], color="#c0392b", ls="--", lw=1.5, label="Fail level ($9,000)"),
    ]
    ax.legend(handles=legend_h, fontsize=8, loc="upper left", framealpha=0.9)
    ax.set_xlabel("Days elapsed")
    ax.set_ylabel("Equity (USDC)")
    ax.set_title(f"Breakout Equity Curves — all 44 sims (vol_target={vol_target_plot})", fontsize=10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.grid(True, alpha=0.20)

    # ── Middle: pass rate comparison ──────────────────────────────────────────
    ax2 = axes[1]
    propr_rates    = [_propr_metrics(vt)["pass_rate"] * 100 for vt in vts]
    breakout_p1    = [_breakout_sweep_metrics(breakout_sweep[vt])["p1_pass_rate"] * 100 for vt in vts]
    breakout_full  = [_breakout_sweep_metrics(breakout_sweep[vt])["full_pass_rate"] * 100 for vt in vts]

    x     = np.arange(len(vts))
    w     = 0.27
    bars1 = ax2.bar(x - w,   propr_rates,   w, label="Propr (1-step)",      color="#3498db", alpha=0.85)
    bars2 = ax2.bar(x,       breakout_p1,   w, label="Breakout P1 only",    color="#f39c12", alpha=0.85)
    bars3 = ax2.bar(x + w,   breakout_full, w, label="Breakout FULL PASS",  color="#2ecc71", alpha=0.85)

    for bars in (bars1, bars2, bars3):
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                         f"{h:.0f}%", ha="center", va="bottom", fontsize=7)

    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{vt:.2f}" for vt in vts])
    ax2.set_xlabel("Vol Target")
    ax2.set_ylabel("Pass Rate (%)")
    ax2.set_title("Pass Rate: Propr vs Breakout by Vol Target", fontsize=10)
    ax2.legend(fontsize=8)
    ax2.set_ylim(0, max(max(propr_rates), max(breakout_p1), 5) * 1.25)
    ax2.grid(True, axis="y", alpha=0.25)

    # ── Bottom: expected fee comparison ───────────────────────────────────────
    ax3 = axes[2]
    propr_fees     = [min(_propr_metrics(vt)["exp_fee"], 1000) for vt in vts]
    breakout_fees  = [min(_breakout_sweep_metrics(breakout_sweep[vt])["exp_fee"], 1000) for vt in vts]

    ax3.plot([f"{vt:.2f}" for vt in vts], propr_fees,    "o-", color="#3498db",
             lw=2, markersize=7, label=f"Propr (fee={int(PROPR_FEE)}$)")
    ax3.plot([f"{vt:.2f}" for vt in vts], breakout_fees, "s-", color="#2ecc71",
             lw=2, markersize=7, label=f"Breakout (fee={int(BREAKOUT_FEE)}$)")
    ax3.axhline(PROPR_FEE,    color="#3498db", ls=":", lw=1.0)
    ax3.axhline(BREAKOUT_FEE, color="#2ecc71", ls=":", lw=1.0)

    ax3.set_xlabel("Vol Target")
    ax3.set_ylabel("Expected Fee per PASS ($)")
    ax3.set_title("Expected Fee Cost to Get One Pass", fontsize=10)
    ax3.legend(fontsize=8)
    ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax3.grid(True, alpha=0.25)

    # Right axis: funded capital per $1 spent on fees
    ax3r = ax3.twinx()
    propr_cap    = [PROPR_CAPITAL / f if f > 0 else 0 for f in propr_fees]
    breakout_cap = [BREAKOUT_CAPITAL / f if f > 0 else 0 for f in breakout_fees]
    ax3r.plot([f"{vt:.2f}" for vt in vts], propr_cap,    "--", color="#3498db", alpha=0.5, lw=1)
    ax3r.plot([f"{vt:.2f}" for vt in vts], breakout_cap, "--", color="#2ecc71", alpha=0.5, lw=1)
    ax3r.set_ylabel("Funded capital / $ in fees", fontsize=8, color="gray")
    ax3r.tick_params(axis="y", labelcolor="gray", labelsize=8)
    ax3r.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}"))

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nPlot saved → {save_path}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — FINAL RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────

def print_final_recommendation(
    breakout_sweep: dict[float, list[dict[str, Any]]],
) -> None:
    """Step 7: Print final venue + vol_target recommendation."""
    # Find best Breakout vol_target
    best_bo_vt     = max(BREAKOUT_VOL_TARGETS,
                         key=lambda vt: _breakout_sweep_metrics(breakout_sweep[vt])["full_pass_rate"])
    best_bo_m      = _breakout_sweep_metrics(breakout_sweep[best_bo_vt])
    best_propr_m   = _propr_metrics(0.20)   # from vol_sweep: 0.20 is recommended

    bo_pass        = best_bo_m["full_pass_rate"]
    bo_fee         = best_bo_m["exp_fee"]
    bo_payout      = BREAKOUT_CAPITAL * (0.10 + 0.05) * PROFIT_SPLIT  # $1200
    bo_roi         = bo_payout / bo_fee if bo_fee < 1e9 else 0.0
    bo_days        = best_bo_m["avg_total_days"] or 0.0

    propr_pass     = best_propr_m["pass_rate"]
    propr_fee      = best_propr_m["exp_fee"]
    propr_payout   = PROPR_CAPITAL * 0.10 * PROFIT_SPLIT  # $400
    propr_roi      = propr_payout / propr_fee

    # Pick best venue by ROI
    if bo_roi > propr_roi and bo_pass > 0:
        best_venue = "Breakout"
        best_vt    = best_bo_vt
        pass_rate  = bo_pass
        exp_fee    = bo_fee
        payout     = bo_payout
        roi        = bo_roi
    else:
        best_venue = "Propr"
        best_vt    = 0.20
        pass_rate  = propr_pass
        exp_fee    = propr_fee
        payout     = propr_payout
        roi        = propr_roi

    print("\n" + "=" * 60)
    print("FINAL RECOMMENDATION")
    print("=" * 60)
    print(f"  Best venue        : {best_venue}")
    print(f"  Best vol_target   : {best_vt:.2f}")
    print(f"  Expected pass rate: {pass_rate:.0%}")
    print(f"  Expected fee cost : ${exp_fee:.0f} per funded account")
    print(f"  Expected payout   : ${payout:.0f} per payout cycle")
    print(f"  ROI on fees       : {roi:.2f}×")
    print()

    # Reasoning
    if best_venue == "Propr":
        print(
            f"  Reasoning: Despite Propr's lower capital ($5K vs $10K), its single-step "
            f"challenge (10% target, 3% daily limit) achieves {propr_pass:.0%} pass rate. "
            f"Breakout's 2-step structure means even Phase 1 passes must still clear "
            f"Phase 2, substantially reducing overall pass rate. Propr's lower fee "
            f"($60 vs $100) and faster path to funding make it capital-efficient. "
            f"Breakout's 5% daily limit provides more margin vs TSMOM v2's intraweek "
            f"volatility, but the additional 5% Phase 2 hurdle offsets this advantage."
        )
    else:
        print(
            f"  Reasoning: Breakout's looser daily limit (5% vs Propr's 3%) significantly "
            f"reduces daily-limit kills — the dominant fail cause in Propr simulations. "
            f"The {bo_pass:.0%} overall pass rate at vol={best_vt:.2f} combined with "
            f"${bo_payout:.0f} minimum payout (80% × $1,500 target profit) gives "
            f"{roi:.2f}× ROI on fees vs Propr's {propr_roi:.2f}×. "
            f"Average {bo_days:.0f} total days to fund is acceptable for the higher capital base."
        )

    print()
    print("  Action items:")
    if best_venue == "Breakout":
        print(f"    1. Start Breakout Explorer ($10K) challenge at vol_target={best_vt:.2f}")
        print(f"       Best calendar windows: Mar-Apr (based on TSMOM v2 regime analysis)")
        print(f"    2. Monitor Phase 2 — if TSMOM v2 win rate holds, "
              f"expect ~{best_bo_m['p2_pass_rate']:.0%} of Phase-1-passes to clear Phase 2")
    else:
        print(f"    1. Continue Propr Starter ($5K) at vol_target={best_vt:.2f}")
        print(f"       Best calendar windows: Mar-Apr (regime_score ≥ 0.20)")
        print(f"    2. Consider Breakout as second venue once Propr challenge is funded")

    # Side-by-side final summary
    print()
    print(f"  {'Metric':<25} | {'Propr (0.20)':<16} | {'Breakout (' + str(best_bo_vt) + ')'}")
    print(f"  {'-'*60}")
    print(f"  {'Pass rate':<25} | {propr_pass:<16.0%} | {bo_pass:.0%}")
    print(f"  {'Exp fee to pass':<25} | ${propr_fee:<15.0f} | ${bo_fee:.0f}" if bo_fee < 1e9 else
          f"  {'Exp fee to pass':<25} | ${propr_fee:<15.0f} | ∞")
    print(f"  {'Min payout/cycle':<25} | ${propr_payout:<15.0f} | ${bo_payout:.0f}")
    print(f"  {'ROI on fees':<25} | {propr_roi:<16.2f} | {bo_roi:.2f}×")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    import time
    t0 = time.time()

    prices = download_data(UNIVERSE, DATA_START, DATA_END)

    # Vol sweep
    print("\n" + "="*60)
    print("BREAKOUT VOL TARGET SWEEP")
    print("="*60)
    breakout_sweep = run_breakout_vol_sweep(prices)

    # Print sweep summary
    print("\n" + "-"*90)
    print(f"{'vol_t':>6} | {'P1 Pass%':>9} | {'Full Pass%':>11} | {'AvgDaysP1':>10} | "
          f"{'AvgDaysP2':>10} | {'AvgTotal':>9} | {'Breach P1':>10} | {'ExpFee':>8}")
    print("-"*90)
    for vt in BREAKOUT_VOL_TARGETS:
        m   = _breakout_sweep_metrics(breakout_sweep[vt])
        adp1 = f"{m['avg_days_p1']:.0f}d"  if m["avg_days_p1"]    else "—"
        adp2 = f"{m['avg_days_p2']:.0f}d"  if m["avg_days_p2"]    else "—"
        adt  = f"{m['avg_total_days']:.0f}d" if m["avg_total_days"] else "—"
        ef   = f"${m['exp_fee']:.0f}" if m["exp_fee"] < 1e9 else "∞"
        print(f"{vt:>6.2f} | {m['p1_pass_rate']*100:>8.0f}% | {m['full_pass_rate']*100:>10.0f}% | "
              f"{adp1:>10} | {adp2:>10} | {adt:>9} | {m['breaches_p1']:>10} | {ef:>8}")
    print("-"*90)

    # Comparison at vol=0.15
    print_comparison_table(breakout_sweep, vol_target=0.15)

    # Best vol_target for calendar + regime analysis
    best_vt = max(BREAKOUT_VOL_TARGETS,
                  key=lambda vt: _breakout_sweep_metrics(breakout_sweep[vt])["full_pass_rate"])
    print_calendar_analysis(breakout_sweep[best_vt], best_vt)

    # Plot
    plot_path = OUT_DIR / "breakout_simulation.png"
    plot_breakout_simulation(breakout_sweep, plot_path, vol_target_plot=best_vt)

    # Final recommendation
    print_final_recommendation(breakout_sweep)

    print(f"\nTotal runtime: {(time.time()-t0)/60:.1f} minutes")


if __name__ == "__main__":
    main()
