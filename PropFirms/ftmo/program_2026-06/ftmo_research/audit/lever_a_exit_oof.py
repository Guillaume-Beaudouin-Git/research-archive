"""
lever_a_exit_oof.py — Lever A: select exit variant via walk-forward expanding OOF.

12 candidate configs (filter × exit), all run on NQ 30-min ORB, cost 2 bp RT,
same-bar exec.

For each WF fold:
  - Compute training p_funded for each candidate.
  - Pick best by training p_funded.
  - Apply to test fold.
Aggregate OOF p_funded across all test folds.

Compare:
  - In-sample p_funded (full-data) per config
  - OOF p_funded (walk-forward) per config (held constant)
  - OOF p_funded (walk-forward) with config SELECTION per fold

Outputs:
  - lever_a_in_sample.csv : config × in-sample p_funded
  - lever_a_oof_held.csv  : config × OOF p_funded (config held constant)
  - lever_a_wf_selected.csv : per-fold selection log + aggregate OOF
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES
from oof_framework import (build_fold_boundaries, evaluate_config_pfunded,
                            walk_forward_select_apply, full_sample_pfunded,
                            WF_FOLD_END_DATES)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


CONFIGS = {
    "C00_E0_at_close":   {"filter": {}, "exit": {"kind": "at_close"}},
    "C01_E1_tp_1R":      {"filter": {}, "exit": {"kind": "tp_R", "tp_R": 1.0}},
    "C02_E2_tp_1.5R":    {"filter": {}, "exit": {"kind": "tp_R", "tp_R": 1.5}},
    "C03_E3_tp_2R":      {"filter": {}, "exit": {"kind": "tp_R", "tp_R": 2.0}},
    "C04_E4_tp_3R":      {"filter": {}, "exit": {"kind": "tp_R", "tp_R": 3.0}},
    "C05_E5_scale_1R":   {"filter": {}, "exit": {"kind": "scale_out", "partial_tp_R": 1.0, "partial_frac": 0.5}},
    "C06_E6_scale_2R":   {"filter": {}, "exit": {"kind": "scale_out", "partial_tp_R": 2.0, "partial_frac": 0.5}},
    "C07_E7_trail_1R":   {"filter": {}, "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0}},
    "C08_E8_trail_2R":   {"filter": {}, "exit": {"kind": "trailing", "trigger_R": 2.0, "lock_R": 1.0}},
    "C09_E9_time_3h":    {"filter": {}, "exit": {"kind": "time_stop", "n_bars": 180}},
    "C10_V2+E3":         {"filter": {"kind": "pct", "min_pct": 0.001},
                          "exit": {"kind": "tp_R", "tp_R": 2.0}},
    "C11_V2+E7":         {"filter": {"kind": "pct", "min_pct": 0.001},
                          "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0}},
}

COST_BPS = 2.0


def build_daily_R_per_config() -> dict[str, pd.Series]:
    """Pre-compute the daily R series for each config (one build per config)."""
    sleeve = SLEEVES["NQ"]
    daily_R = {}
    for name, cfg in CONFIGS.items():
        log.info(f"  Building {name}...")
        tl = build_orb_trades(sleeve, filter_spec=cfg["filter"], exit_spec=cfg["exit"],
                               cost_bps_rt=COST_BPS)
        dR = build_daily_R_series(tl)
        daily_R[name] = dR
    return daily_R


if __name__ == "__main__":
    print("=" * 110)
    print("LEVER A — Exit/filter OOF via walk-forward expanding")
    print("=" * 110)
    print(f"  Candidates: {len(CONFIGS)} configs (10 exits × 1 filter + 2 combined)")
    print(f"  Cost: {COST_BPS} bp RT")
    print(f"  WF folds: {len(WF_FOLD_END_DATES) - 1} fold boundaries → 1-year test folds 2014-2026")
    print()

    log.info("Building daily R series for each config...")
    daily_R_per_config = build_daily_R_per_config()

    # Use one config's index to derive fold boundaries (all should align by date)
    ref_dR = daily_R_per_config["C00_E0_at_close"]
    boundaries = build_fold_boundaries(ref_dR, WF_FOLD_END_DATES)
    log.info(f"  WF boundaries: {len(boundaries)} folds")
    for tr_end, ts_start, ts_end, tr_date, te_date in boundaries:
        log.info(f"    train→{tr_date} ({tr_end} days), test→{te_date} ({ts_end - ts_start} test days)")

    # In-sample full-data p_funded per config
    print()
    print("=" * 110)
    print("IN-SAMPLE p_funded (config held constant on full data)")
    print("=" * 110)
    rows_is = []
    for name, dR in daily_R_per_config.items():
        ip = full_sample_pfunded(dR)
        rows_is.append({"config": name, "in_sample_p_funded_pct": round(ip, 2)})
    df_is = pd.DataFrame(rows_is)
    print(df_is.to_string(index=False))
    df_is.to_csv(ROOT / "lever_a_in_sample.csv", index=False)

    # OOF held: for each config, compute p_funded over all test fold starts (pooled)
    print()
    print("=" * 110)
    print("OOF p_funded — config held constant (no selection)")
    print("=" * 110)
    rows_oof = []
    for name, dR in daily_R_per_config.items():
        n_resolved_tot = 0
        n_funded_tot = 0
        for tr_end, ts_start, ts_end, _, _ in boundaries:
            test_starts = np.arange(ts_start, ts_end)
            res = evaluate_config_pfunded(dR, test_starts)
            n_resolved_tot += res["n_resolved"]
            n_funded_tot += res["n_funded"]
        oof = (n_funded_tot / n_resolved_tot * 100) if n_resolved_tot > 0 else float("nan")
        rows_oof.append({"config": name, "oof_p_funded_pct": round(oof, 2),
                          "oof_n_resolved": n_resolved_tot,
                          "oof_n_funded": n_funded_tot})
    df_oof = pd.DataFrame(rows_oof)
    print(df_oof.to_string(index=False))
    df_oof.to_csv(ROOT / "lever_a_oof_held.csv", index=False)

    # In-sample vs OOF comparison
    print()
    print("=" * 110)
    print("IN-SAMPLE vs OOF (held) — overfit gap per config")
    print("=" * 110)
    merged = pd.merge(df_is, df_oof, on="config")
    merged["delta_oof_vs_is"] = merged["oof_p_funded_pct"] - merged["in_sample_p_funded_pct"]
    print(merged.sort_values("oof_p_funded_pct", ascending=False).to_string(index=False))
    merged.to_csv(ROOT / "lever_a_overfit_gap.csv", index=False)

    # Walk-forward with SELECTION
    print()
    print("=" * 110)
    print("WALK-FORWARD SELECTION — pick best per training fold, apply to test")
    print("=" * 110)
    wf_result = walk_forward_select_apply(daily_R_per_config, boundaries,
                                            block_cap_pct=0.005,
                                            min_train_n_resolved=100)
    fold_df = pd.DataFrame(wf_result["fold_records"])
    print(fold_df.to_string(index=False))
    fold_df.to_csv(ROOT / "lever_a_wf_selected.csv", index=False)
    print()
    print(f"  OOF pooled p_funded (WF selection): {wf_result['oof_p_funded_pct']:.2f}% "
           f"({wf_result['oof_total_funded']} funded / {wf_result['oof_total_resolved']} resolved)")
    print(f"  OOF total starts: {wf_result['oof_total_starts']}")

    # Best OOF held config vs WF-selected
    best_oof_held = merged.sort_values("oof_p_funded_pct", ascending=False).iloc[0]
    print()
    print("=" * 110)
    print("SUMMARY — best held vs WF-selected vs baseline")
    print("=" * 110)
    baseline_is = merged[merged["config"] == "C00_E0_at_close"].iloc[0]
    v2e7_is = merged[merged["config"] == "C11_V2+E7"].iloc[0]
    print(f"  Baseline (E0 at_close)         : in-sample={baseline_is['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={baseline_is['oof_p_funded_pct']:5.2f}%")
    print(f"  V2+E7 (best in-sample Fil 1)   : in-sample={v2e7_is['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={v2e7_is['oof_p_funded_pct']:5.2f}%")
    print(f"  Best held config ({best_oof_held['config']}): in-sample={best_oof_held['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={best_oof_held['oof_p_funded_pct']:5.2f}%")
    print(f"  WF-selection                     : OOF={wf_result['oof_p_funded_pct']:5.2f}%")
