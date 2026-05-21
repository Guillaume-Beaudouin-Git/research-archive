"""
signal_refinements.py — Part C: Targeted Modifications
=========================================================
Implements modifications ONLY for passing hypotheses from hypothesis_tests.py.

Passing: H3 (opening range size effect, p≈0.000)

Modification M1 — Range minimum filter:
  Only trade if opening range (09:30-09:45) >= rng_min points.
  Threshold search: rng_min ∈ {20, 25, 30, 35, 40, 45, 50} pts.

Adoption rules (ALL must pass):
  Rule 1: ΔSharpe > +0.15  vs baseline iter_05_A400+B012
  Rule 2: ≥50% trades retained (N_modified / N_baseline ≥ 0.50)
  Rule 3: Walk-forward positive% ≥ baseline WF% on extended 6M/3M test

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.signal_refinements
n_tests: 134 → 134 + 7 M1 variants = 141
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import NQBacktestEngine
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, signals_from_features,
)
from Futures.research.active.nq_intraday.iter_07_validation import (
    sharpe_hac,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

STRATEGY_GAP   = 0.012
STRATEGY_STOP  = 400.0
N_TESTS_START  = 134

# Baseline from iter_05_A400+B012
BASELINE = {
    "sharpe":       1.2132,
    "max_dd":      -0.2506,
    "n_trades":     567,
    "wf_pct":       100.0,
}

DSHARPE_MIN   = 0.15     # Rule 1
RETENTION_MIN = 0.50     # Rule 2

TRAIN_MONTHS  = 6
TEST_MONTHS   = 3


# ─────────────────────────────────────────────────────────────────────────────
# Modified signal builder with range filter
# ─────────────────────────────────────────────────────────────────────────────

def signals_m1(feats: pd.DataFrame, rng_min: float) -> pd.DataFrame:
    """iter_05_A400+B012 + minimum opening range filter."""
    feats_filtered = feats[feats["rng"] >= rng_min].copy()
    return signals_from_features(
        feats_filtered,
        gap_thresh=STRATEGY_GAP,
        dollar_stop=STRATEGY_STOP,
    )


def make_signal_fn_m1(rng_min: float):
    """Closure: returns signal_fn(df_1min, params) compatible with WF."""
    def fn(df_1min: pd.DataFrame, params: dict) -> pd.DataFrame:
        feats_w = build_opening_features(df_1min)
        return signals_m1(feats_w, rng_min=rng_min)
    return fn


# ─────────────────────────────────────────────────────────────────────────────
# Extended walk-forward (6M train / 3M test)
# ─────────────────────────────────────────────────────────────────────────────

def extended_wf(engine: NQBacktestEngine,
                signal_fn,
                max_windows: int = 12) -> dict:
    """
    Extended walk-forward: 6M train / 3M test, rolling +3M.
    Returns {n_windows, wf_pct_positive, windows, total_pnl}.
    """
    all_dates = pd.Series(
        engine.rth.index.normalize().unique()
    ).sort_values()
    start_date = all_dates.iloc[0]

    windows   = []
    start_m   = 0

    while len(windows) < max_windows:
        t_start = start_date + pd.DateOffset(months=start_m)
        t_end   = t_start    + pd.DateOffset(months=TRAIN_MONTHS)
        oos_end = t_end       + pd.DateOffset(months=TEST_MONTHS)

        if oos_end > all_dates.iloc[-1] + pd.DateOffset(days=10):
            break

        oos = engine.rth[
            (engine.rth.index >= t_end) &
            (engine.rth.index <  oos_end)
        ]
        if len(oos) < 30:
            start_m += TEST_MONTHS
            continue

        eng_oos     = NQBacktestEngine.__new__(NQBacktestEngine)
        eng_oos.df  = oos
        eng_oos.rth = oos

        try:
            sigs_oos = signal_fn(oos, {})
            if sigs_oos.empty or len(sigs_oos) < 3:
                start_m += TEST_MONTHS
                continue

            tl_oos, met_oos = eng_oos.run(sigs_oos)
            pnl_tot = met_oos.get("total_pnl_usd", 0)
            n       = met_oos.get("n_trades", 0)

            if not tl_oos.empty:
                tl_oos["date"] = pd.to_datetime(tl_oos["entry_ts"]).dt.normalize()
                daily_w = tl_oos.groupby("date")["pnl_usd"].sum()
                sh_w = sharpe_hac(daily_w)
            else:
                sh_w = np.nan

            windows.append({
                "oos_start": str(t_end.date()),
                "oos_end":   str(oos_end.date()),
                "n_trades":  n,
                "sharpe":    round(sh_w, 3) if np.isfinite(sh_w) else None,
                "total_pnl": round(pnl_tot, 2),
                "positive":  pnl_tot > 0,
            })
        except Exception as e:
            log.warning("WF window failed: %s", e)

        start_m += TEST_MONTHS

    if not windows:
        return {"n_windows": 0, "wf_pct_positive": 0, "windows": [], "total_pnl": 0}

    n_pos     = sum(w["positive"] for w in windows)
    pct_pos   = n_pos / len(windows) * 100
    total_pnl = sum(w["total_pnl"] for w in windows)
    return {
        "n_windows":       len(windows),
        "wf_pct_positive": round(pct_pos, 1),
        "windows":         windows,
        "total_pnl":       total_pnl,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> Optional[dict]:
    print("=" * 80)
    print("PART C — SIGNAL REFINEMENTS  |  H3 only: range minimum filter")
    print(f"  Baseline: Sharpe={BASELINE['sharpe']:.4f}  MaxDD={BASELINE['max_dd']*100:.1f}%  "
          f"N={BASELINE['n_trades']}  WF%={BASELINE['wf_pct']:.0f}%")
    print(f"  Adoption rules: ΔSharpe>{DSHARPE_MIN:.2f}  "
          f"AND retention>={RETENTION_MIN*100:.0f}%  AND WF%≥baseline")
    print("=" * 80)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)

    # Threshold candidates (pts)
    rng_thresholds = [20, 25, 30, 35, 40, 45, 50]

    print(f"\n  {'RngMin':>8} {'N':>5} {'Ret%':>7} {'Sharpe':>8} {'ΔSharpe':>9} "
          f"{'MaxDD':>8} {'WF%':>6} | {'R1':>4} {'R2':>4} {'R3':>4} {'Adopt':>6}")
    print(f"  {'-'*80}")

    # Compute baseline extended WF (6M/3M) for fair comparison
    def _baseline_signal_fn(df_1min, params):
        feats_w = build_opening_features(df_1min)
        return signals_from_features(feats_w, gap_thresh=STRATEGY_GAP,
                                      dollar_stop=STRATEGY_STOP)

    print("\n  Computing baseline extended WF (6M train / 3M test)...")
    baseline_wf = extended_wf(engine, _baseline_signal_fn)
    baseline_wf_pct = baseline_wf["wf_pct_positive"]
    print(f"  Baseline WF: {baseline_wf['n_windows']} windows  "
          f"{baseline_wf_pct:.0f}% positive")

    # Rule 3: modified WF% >= baseline extended WF% (apples-to-apples)
    WF_THRESHOLD = baseline_wf_pct

    best_result  = None
    best_sharpe  = BASELINE["sharpe"]
    n_test       = N_TESTS_START

    all_results = []

    for rng_min in rng_thresholds:
        n_test += 1
        sigs = signals_m1(feats, rng_min=rng_min)

        if len(sigs) < 20:
            print(f"  {rng_min:>8} {'<20 trades — skip':>60}")
            continue

        tl, met = engine.run(sigs)

        sh    = met.get("sharpe_daily_hac") or 0
        mdd   = met.get("max_dd_pct") or 0
        n     = met.get("n_trades", 0)
        ret   = n / BASELINE["n_trades"]
        dsh   = sh - BASELINE["sharpe"]

        r1 = dsh    > DSHARPE_MIN
        r2 = ret    >= RETENTION_MIN

        # Only run WF if R1 and R2 pass (expensive)
        if r1 and r2:
            wf_res = extended_wf(engine, make_signal_fn_m1(rng_min))
            wf_pct = wf_res["wf_pct_positive"]
            r3     = wf_pct >= WF_THRESHOLD
        else:
            wf_pct = np.nan
            r3     = False

        adopt = r1 and r2 and r3

        wf_str = f"{wf_pct:.0f}%" if np.isfinite(wf_pct) else "  N/A"
        r1s = "OK" if r1 else "NO"
        r2s = "OK" if r2 else "NO"
        r3s = "OK" if r3 else ("NO" if (r1 and r2) else "---")
        adp = "ADOPT" if adopt else "skip"

        print(f"  {rng_min:>8} {n:>5} {ret*100:>6.0f}% {sh:>8.4f} {dsh:>+9.4f} "
              f"{mdd*100:>7.1f}% {wf_str:>5} | {r1s:>4} {r2s:>4} {r3s:>4} {adp:>6}")

        result = {
            "rng_min":   rng_min,
            "n_trades":  n,
            "retention": ret,
            "sharpe":    sh,
            "dsharpe":   dsh,
            "max_dd":    mdd,
            "wf_pct":    wf_pct,
            "r1": r1, "r2": r2, "r3": r3,
            "adopt":     adopt,
        }
        all_results.append(result)

        if adopt and sh > best_sharpe:
            best_sharpe = sh
            best_result = result

    print(f"\n  n_tests: {N_TESTS_START} → {n_test}  (+{len(rng_thresholds)} M1 variants)")

    # ── DECISION ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("  MODIFICATION DECISION")
    print("=" * 80)

    if best_result is None:
        print("\n  DECISION: NO MODIFICATIONS ADOPTED")
        print("  H3 identified a range size effect, but no rng_min threshold satisfies")
        print("  ALL THREE rules (ΔSharpe, retention, WF%). Proceed with baseline A400+B012.")

        # Still report: what threshold is closest to passing?
        r1_pass = [r for r in all_results if r["r1"]]
        r1r2_pass = [r for r in all_results if r["r1"] and r["r2"]]
        print(f"\n  R1 (ΔSharpe>{DSHARPE_MIN:.2f}) passed for: "
              f"{[r['rng_min'] for r in r1_pass]}")
        print(f"  R1+R2 passed for: {[r['rng_min'] for r in r1r2_pass]}")

        print("\n  Root cause analysis:")
        for r in all_results:
            if r["r1"]:
                wf_str = f"{r['wf_pct']:.0f}%" if np.isfinite(r['wf_pct']) else "N/A"
                print(f"    rng_min={r['rng_min']}pt: "
                      f"Sh={r['sharpe']:.4f} (+{r['dsharpe']:+.4f})  "
                      f"Ret={r['retention']*100:.0f}%  WF={wf_str}")
    else:
        print(f"\n  DECISION: ADOPT M1 — range minimum filter rng_min={best_result['rng_min']} pts")
        print(f"    Sharpe={best_result['sharpe']:.4f}  ΔSharpe={best_result['dsharpe']:+.4f}")
        print(f"    MaxDD={best_result['max_dd']*100:.1f}%  "
              f"Retention={best_result['retention']*100:.0f}%  WF%={best_result['wf_pct']:.0f}%")
        print(f"\n  Use rng_min={best_result['rng_min']} in iter_10.")

    print("=" * 80)
    return best_result


if __name__ == "__main__":
    best = main()
