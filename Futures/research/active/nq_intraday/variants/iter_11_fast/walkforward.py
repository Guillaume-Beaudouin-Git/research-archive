"""
walkforward.py — Expanding walk-forward for iter_11_fast.
==========================================================
5-fold+ expanding window, 6M min train, 3M test rolling.

Reports per-fold Sharpe, WF% positive, comparison vs iter_10 baseline:
  iter_10: WF%=77.8% (9 windows), Sharpe=1.52 full period.
  H1 gate: median WF Sharpe ≥ 1.22 (= 0.8 × 1.52).

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.variants.iter_11_fast.walkforward
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[6]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import NQBacktestEngine
from Futures.research.active.nq_intraday.iter_05 import build_opening_features
from Futures.research.active.nq_intraday.iter_07_validation import sharpe_hac
from Futures.research.active.nq_intraday.variants.iter_11_fast.iter_11_refined import (
    build_signals_fast,
)

# Walk-forward configuration (expanding window)
TRAIN_MONTHS_MIN = 6    # expanding: grows from 6M to full history
TEST_MONTHS      = 3    # fixed 3M OOS window, rolling forward
MIN_OOS_BARS     = 30   # skip windows with < 30 OOS bars

ITER10_SHARPE    = 1.5212
H1_GATE          = 1.22     # 0.80 × iter_10 Sharpe


def run_expanding_wf(engine: NQBacktestEngine) -> list[dict]:
    """
    Expanding walk-forward: train always starts from dataset beginning,
    OOS window rolls forward by TEST_MONTHS each fold.

    Returns list of per-window result dicts.
    """
    all_dates = pd.Series(engine.rth.index.normalize().unique()).sort_values()
    dataset_start = all_dates.iloc[0]
    dataset_end   = all_dates.iloc[-1]

    total_months = (
        (dataset_end.year - dataset_start.year) * 12
        + (dataset_end.month - dataset_start.month)
    )

    windows: list[dict] = []
    oos_start_m = TRAIN_MONTHS_MIN  # first OOS starts after min train period

    while True:
        oos_start = dataset_start + pd.DateOffset(months=oos_start_m)
        oos_end   = oos_start     + pd.DateOffset(months=TEST_MONTHS)

        if oos_end > dataset_end + pd.DateOffset(days=10):
            break

        # OOS data slice
        oos = engine.rth[
            (engine.rth.index >= oos_start) &
            (engine.rth.index <  oos_end)
        ]
        if len(oos) < MIN_OOS_BARS:
            oos_start_m += TEST_MONTHS
            continue

        # Build OOS sub-engine
        eng_oos     = NQBacktestEngine.__new__(NQBacktestEngine)
        eng_oos.df  = oos
        eng_oos.rth = oos

        try:
            feats_oos = build_opening_features(oos)
            sigs_oos  = build_signals_fast(feats_oos)

            if sigs_oos.empty or len(sigs_oos) < 3:
                oos_start_m += TEST_MONTHS
                continue

            tl_oos, met_oos = eng_oos.run(sigs_oos)
            pnl_tot = met_oos.get("total_pnl_usd", 0)
            n       = met_oos.get("n_trades", 0)
            avg_w   = met_oos.get("avg_winner_usd", 0)
            avg_l   = met_oos.get("avg_loser_usd", 0)
            wr      = met_oos.get("win_rate", 0)

            if not tl_oos.empty:
                tl_oos["date"] = pd.to_datetime(tl_oos["entry_ts"]).dt.normalize()
                daily_w = tl_oos.groupby("date")["pnl_usd"].sum()
                sh_w = sharpe_hac(daily_w)
            else:
                sh_w = np.nan

            windows.append({
                "train_start":  str(dataset_start.date()),
                "train_end":    str(oos_start.date()),
                "oos_start":    str(oos_start.date()),
                "oos_end":      str(oos_end.date()),
                "train_months": oos_start_m,
                "n_trades":     n,
                "win_rate":     round(wr, 4) if wr else 0.0,
                "avg_winner":   round(float(avg_w), 2),
                "avg_loser":    round(float(avg_l), 2),
                "sharpe":       round(float(sh_w), 4) if np.isfinite(sh_w) else None,
                "total_pnl":    round(float(pnl_tot), 2),
                "positive":     pnl_tot > 0,
            })

        except Exception as e:
            print(f"  WARNING: WF window {oos_start.date()}→{oos_end.date()} failed: {e}")

        oos_start_m += TEST_MONTHS

    return windows


def print_wf_table(windows: list[dict]) -> tuple[float, float]:
    """Print walk-forward table, return (median_sharpe, wf_pct_positive)."""
    print(f"\n  {'#':<4} {'Train start':<12} {'OOS start':<12} {'OOS end':<12} "
          f"{'N':>5} {'WR':>6} {'Sharpe':>8} {'PnL$':>9} {'+'}")
    print(f"  {'-'*78}")

    sh_vals = []
    for i, w in enumerate(windows, 1):
        sh_s = f"{w['sharpe']:.4f}" if w.get("sharpe") is not None else "    N/A"
        pos  = "✓" if w["positive"] else "✗"
        wr_s = f"{w['win_rate']*100:.1f}%"
        if w.get("sharpe") is not None:
            sh_vals.append(w["sharpe"])
        print(f"  {i:<4} {w['train_start']:<12} {w['oos_start']:<12} {w['oos_end']:<12} "
              f"{w['n_trades']:>5} {wr_s:>6} {sh_s:>8} {w['total_pnl']:>9.0f} {pos}")

    n_pos   = sum(w["positive"] for w in windows)
    n_tot   = len(windows)
    wf_pct  = n_pos / n_tot * 100 if n_tot > 0 else 0.0
    med_sh  = float(np.median(sh_vals)) if sh_vals else np.nan
    mean_sh = float(np.mean(sh_vals))   if sh_vals else np.nan
    total_pnl = sum(w["total_pnl"] for w in windows)

    print(f"\n  {'-'*78}")
    print(f"  Summary: {n_tot} windows | {n_pos} positive ({wf_pct:.0f}%)")
    print(f"  Median OOS Sharpe: {med_sh:.4f}" if np.isfinite(med_sh) else "  Median OOS Sharpe: N/A")
    print(f"  Mean   OOS Sharpe: {mean_sh:.4f}" if np.isfinite(mean_sh) else "  Mean OOS Sharpe: N/A")
    print(f"  Total OOS PnL:     ${total_pnl:,.0f}")

    return med_sh, wf_pct


def main() -> None:
    print("=" * 80)
    print("iter_11_fast — Expanding Walk-Forward (6M min train / 3M OOS rolling)")
    print(f"H1 gate: median OOS Sharpe ≥ {H1_GATE:.2f}  (= 0.80 × {ITER10_SHARPE:.4f})")
    print(f"iter_10 reference: WF%={100*ITER10_SHARPE/ITER10_SHARPE:.0f}%, Sharpe={ITER10_SHARPE:.4f}")
    print("=" * 80)

    t0  = time.perf_counter()
    df  = load_nq_1min()
    engine = NQBacktestEngine(df)
    n_days = engine.rth.index.normalize().nunique()
    print(f"\n  Dataset: {len(df):,} bars | {n_days} trading days")

    print("\n  Running expanding walk-forward...")
    windows = run_expanding_wf(engine)

    if not windows:
        print("  ERROR: No WF windows produced. Check data.")
        return

    # ── Results table ─────────────────────────────────────────────────────────
    print("\n" + "─" * 80)
    print("  Walk-forward results (expanding train, 3M OOS):")
    print("─" * 80)
    med_sh, wf_pct = print_wf_table(windows)

    # ── iter_10 comparison ────────────────────────────────────────────────────
    print(f"\n  Comparison vs iter_10:")
    print(f"  {'Metric':<30} {'iter_11_fast':>14} {'iter_10 ref':>14} {'Delta':>12}")
    print(f"  {'-'*72}")
    med_sh_str = f"{med_sh:.4f}" if np.isfinite(med_sh) else "N/A"
    print(f"  {'WF% positive':<30} {wf_pct:>13.0f}% {ITER10_SHARPE/ITER10_SHARPE*77.78:>13.0f}%")
    print(f"  {'Median OOS Sharpe':<30} {med_sh_str:>14} {'n/a (iter_10 ref)':>14}")

    # ── H1 gate ───────────────────────────────────────────────────────────────
    h1_pass = med_sh >= H1_GATE if np.isfinite(med_sh) else False

    print(f"\n" + "=" * 80)
    print("STOP-POINT 1 — Walk-forward verdict")
    print("=" * 80)
    print(f"  Expanding WF windows:     {len(windows)}")
    print(f"  WF% positive:             {wf_pct:.0f}%")
    print(f"  Median OOS Sharpe:        {med_sh_str}")
    print(f"  H1 gate (Sharpe ≥ {H1_GATE:.2f}):  {'PASS ✓' if h1_pass else 'FAIL ✗'}  ({med_sh_str})")

    if h1_pass:
        print(f"\n  → H1 PASS: edge preserved under TP=1.0R + time_stop=11:30 modifications.")
        print(f"    Proceed to STOP-POINT 2: run mc_pivot_test.py")
    else:
        diff = (med_sh - H1_GATE) if np.isfinite(med_sh) else float("nan")
        print(f"\n  → H1 FAIL: Sharpe degradation exceeds 20% threshold.")
        print(f"    Gap from gate: {diff:+.4f} ({diff/H1_GATE*100:+.1f}%)")
        print(f"    If TP=1.0R destroys Sharpe, consider: TP=1.2R as middle ground (mod #2).")

    elapsed = time.perf_counter() - t0
    print(f"\n  Runtime: {elapsed:.1f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
