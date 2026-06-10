"""
Full rigorous test covering 3 paths:
- Path 1: 5 mods on best survivors (ang_025_flip mods 2-3, ang_047 mods 1-3)
- Path 2: 5 new event-driven (lit_012 pre-NFP, lit_013 pre-FOMC, ang_006, ang_018, lit_020)
- Path 3: re-run vol-target survivors with fixed sizing (compare methodology)

All 10 originals + 10 new + path-3 sizing variants. AMTP-Bonferroni over hypothesis tests.
"""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from framework import (
    StrategyResult, load_rf_daily, amtp_bonferroni,
)
from run_tests import STRATEGIES, evaluate
from strategies_v2 import NEW_STRATEGIES

RESULTS_DIR = Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/top10_test/results")


def run_full():
    rf_daily = load_rf_daily()
    all_results = []

    # Original 10 strategies + new 10 — all under vol-target sizing
    all_strats = STRATEGIES + NEW_STRATEGIES
    print(f"\nRunning {len(all_strats)} strategies under vol_target sizing...")
    print(f"AMTP-Bonferroni will use n_tests={len(all_strats)}\n")

    cached_results = {}  # sid -> (daily_pnl, meta) for path-3 reuse

    for sid, name, fn, asset_class in all_strats:
        print(f"\n[{sid}] {name}")
        try:
            daily_pnl, meta = fn()
            cached_results[sid] = (daily_pnl, meta)
            print(f"  n_trades raw: {meta['n_trades']}")
            r = evaluate(sid, name, daily_pnl, meta, rf_daily, sizing="vol_target")
            r.notes = (r.notes + " | sizing=vol_target").strip(" |")
            if "trades_df" in meta and isinstance(meta["trades_df"], pd.DataFrame) and not meta["trades_df"].empty:
                meta["trades_df"].to_csv(RESULTS_DIR / f"trades_{sid}.csv", index=False)
            daily_pnl.to_csv(RESULTS_DIR / f"daily_pnl_{sid}.csv", header=["pnl_frac"])
            print(f"  VT  SR={r.sharpe_excess:>5.2f}  MaxDD={r.max_dd_pct*100:>6.1f}%  "
                  f"WF={r.wf_pass_rate*100:>3.0f}%  HAC_t={r.hac_t_excess:>5.2f}  "
                  f"DSR={r.dsr:>6.2f}  p_FTMO={r.ftmo_p_pass_p1*100:>5.1f}%")
        except Exception as e:
            import traceback; traceback.print_exc()
            r = StrategyResult(id=sid, name=name, notes=f"ERROR: {e}")
        all_results.append(r)

    # AMTP across all hypothesis tests (sized vol_target)
    t_stats = [r.hac_t_excess for r in all_results]
    p_corrected = amtp_bonferroni(t_stats, alpha=0.05)
    for r, p in zip(all_results, p_corrected):
        r.amtp_p_value = p

    # Path 3 — Re-run TOP 5 by FTMO p_pass_p1 under FIXED sizing
    print("\n\n=== PATH 3 — Fixed sizing on top-5 by FTMO p_pass ===")
    sorted_by_mc = sorted(all_results, key=lambda r: -r.ftmo_p_pass_p1)
    top5_ids = [r.id for r in sorted_by_mc[:5]]
    print(f"Top-5 by p_pass_FTMO: {top5_ids}\n")

    fixed_results = []
    for sid in top5_ids:
        if sid not in cached_results:
            continue
        daily_pnl, meta = cached_results[sid]
        name = next((n for i, n, _, _ in all_strats if i == sid), sid)
        try:
            r_fixed = evaluate(f"{sid}_fixed", f"{name} [fixed sizing]", daily_pnl, meta, rf_daily,
                               sizing="fixed")
            print(f"  [{sid}_fixed] SR={r_fixed.sharpe_excess:>5.2f}  MaxDD={r_fixed.max_dd_pct*100:>6.1f}%  "
                  f"WF={r_fixed.wf_pass_rate*100:>3.0f}%  HAC_t={r_fixed.hac_t_excess:>5.2f}  "
                  f"p_FTMO={r_fixed.ftmo_p_pass_p1*100:>5.1f}%  median_days={r_fixed.ftmo_median_days_p1}")
            fixed_results.append(r_fixed)
        except Exception as e:
            print(f"  ERROR on {sid}_fixed: {e}")

    # Save consolidated CSV — original + fixed
    all_for_csv = all_results + fixed_results
    df = pd.DataFrame([asdict(r) for r in all_for_csv])
    # Sort by Sharpe excess descending within sizing group
    df["sizing"] = df["id"].apply(lambda x: "fixed" if x.endswith("_fixed") else "vol_target")
    df = df.sort_values(["sizing", "sharpe_excess"], ascending=[True, False])
    out_csv = RESULTS_DIR / "summary_full_3paths.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # Summary table
    cols = ["id", "n_trades", "n_days", "sharpe_excess", "max_dd_pct",
            "wf_pass_rate", "hac_t_excess", "dsr", "amtp_p_value",
            "ftmo_p_pass_p1", "ftmo_p_pass_p1_p2", "research_pass", "propfirm_pass",
            "cost_gate_ratio", "sizing"]
    df = df.sort_values("sharpe_excess", ascending=False)
    print("\n=== FULL SUMMARY (sorted by SR_excess) ===")
    print(df[cols].to_string(index=False))

    # Highlight survivors (research or propfirm pass)
    survivors = df[df["research_pass"] | df["propfirm_pass"]]
    print(f"\n=== SURVIVORS (research_pass OR propfirm_pass): {len(survivors)} ===")
    if len(survivors) > 0:
        print(survivors[cols].to_string(index=False))


if __name__ == "__main__":
    run_full()
