"""
lever_c_challenge_mgmt.py — Lever C: challenge-management rules, OOF selection.

Building on V2+E7 (Lever A best) daily R series, test challenge-management rules
via the v3 simulator. For each rule combination, compute:
  - In-sample p_funded (all starts)
  - OOF p_funded held (config held constant, test fold starts only)
  - WF-selected OOF (best per training, applied to test)

Mechanisms tested:
  (1) De-risk after target frac: 0.7 / 0.8 / 0.9 × {stop=0, half=0.5}
  (2) Floor proximity taper: ON / OFF
  (3) Phase-2 sizing: 0.5% / 0.4% / 0.3%
  (4) Combos: best (1) × best (2) × best (3)

Honest reporting:
  - Selection space ≥ 12 single-rule configs + 6 combos = ~18 trials.
  - DSR penalty applied to final selected.
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
from nq_sim_v3 import simulate_2step_v3
from oof_framework import build_fold_boundaries, WF_FOLD_END_DATES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# Base config: V2+E7 from Lever A
V2_E7_FILTER = {"kind": "pct", "min_pct": 0.001}
V2_E7_EXIT = {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0}
COST_BPS = 2.0


# Candidate mgmt rule configs (each is a dict of sim kwargs)
MGMT_CONFIGS = {
    "M00_baseline":         {},
    "M01_derisk_0.7_stop":  {"derisk_at_target_frac": 0.7, "derisk_size_factor": 0.0},
    "M02_derisk_0.8_stop":  {"derisk_at_target_frac": 0.8, "derisk_size_factor": 0.0},
    "M03_derisk_0.9_stop":  {"derisk_at_target_frac": 0.9, "derisk_size_factor": 0.0},
    "M04_derisk_0.7_half":  {"derisk_at_target_frac": 0.7, "derisk_size_factor": 0.5},
    "M05_derisk_0.8_half":  {"derisk_at_target_frac": 0.8, "derisk_size_factor": 0.5},
    "M06_floor_taper":      {"floor_proximity_taper": True, "taper_min_factor": 0.25},
    "M07_floor_taper_strict": {"floor_proximity_taper": True, "taper_min_factor": 0.10},
    "M08_p2_0.4":           {"block_cap_p2": 0.004},
    "M09_p2_0.3":           {"block_cap_p2": 0.003},
    "M10_p2_0.2":           {"block_cap_p2": 0.002},
    # Combos:
    "M11_derisk0.8_p2_0.3": {"derisk_at_target_frac": 0.8, "derisk_size_factor": 0.0,
                              "block_cap_p2": 0.003},
    "M12_derisk0.8_floor":  {"derisk_at_target_frac": 0.8, "derisk_size_factor": 0.0,
                              "floor_proximity_taper": True, "taper_min_factor": 0.25},
    "M13_all_three":        {"derisk_at_target_frac": 0.8, "derisk_size_factor": 0.0,
                              "floor_proximity_taper": True, "taper_min_factor": 0.25,
                              "block_cap_p2": 0.003},
    "M14_p1agressif":       {"block_cap_p1": 0.007},
    "M15_p1_p2_0.7_0.3":    {"block_cap_p1": 0.007, "block_cap_p2": 0.003},
}


def eval_pfunded_v3(daily_R: pd.Series, mgmt_kwargs: dict,
                     start_indices: np.ndarray | None = None,
                     block_cap_default: float = 0.005) -> dict:
    """Run v3 simulator with given mgmt rules + restricted starts."""
    bcp1 = mgmt_kwargs.get("block_cap_p1", block_cap_default)
    bcp2 = mgmt_kwargs.get("block_cap_p2", block_cap_default)
    kwargs = {k: v for k, v in mgmt_kwargs.items()
              if k not in ("block_cap_p1", "block_cap_p2")}
    if start_indices is None:
        si = None
    else:
        si = start_indices.tolist()
    out = simulate_2step_v3(daily_R, block_cap_p1=bcp1, block_cap_p2=bcp2,
                              start_indices=si, **kwargs)
    return out


if __name__ == "__main__":
    print("=" * 110)
    print("LEVER C — Challenge-management rules, OOF selection on V2+E7 daily R series")
    print("=" * 110)
    print(f"  Cost: {COST_BPS} bp RT")
    print(f"  Mgmt configs: {len(MGMT_CONFIGS)}")
    print()

    # Build the V2+E7 daily R series
    log.info("Building V2+E7 daily R series on NQ...")
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec=V2_E7_FILTER, exit_spec=V2_E7_EXIT,
                           cost_bps_rt=COST_BPS)
    daily_R = build_daily_R_series(tl)
    log.info(f"  {len(daily_R)} days, n_trades={len(tl)}")

    # 1) In-sample (all starts)
    print()
    print("=" * 110)
    print("IN-SAMPLE p_funded — all start dates 2010-2026")
    print("=" * 110)
    rows_is = []
    for name, kw in MGMT_CONFIGS.items():
        log.info(f"  In-sample: {name}")
        res = eval_pfunded_v3(daily_R, kw)
        rows_is.append({
            "config": name,
            "in_sample_p_funded_pct": round(res["p_funded_pct"], 2)
                if not pd.isna(res["p_funded_pct"]) else float("nan"),
            "in_sample_p_phase1_pct": round(res["p_phase1"] * 100, 2)
                if not pd.isna(res["p_phase1"]) else float("nan"),
            "in_sample_n_resolved": res["n_resolved"],
            "censored_pct": round(res["censored_pct"], 1),
        })
    df_is = pd.DataFrame(rows_is)
    print(df_is.to_string(index=False))
    df_is.to_csv(ROOT / "lever_c_in_sample.csv", index=False)

    # 2) OOF held (only 2014-2026 starts)
    print()
    print("=" * 110)
    print("OOF p_funded — config held constant, starts in 2014-2026 only")
    print("=" * 110)
    boundaries = build_fold_boundaries(daily_R, WF_FOLD_END_DATES)
    test_start_idx_first = boundaries[0][1]
    test_end_idx_last = boundaries[-1][2]
    test_starts_all = np.arange(test_start_idx_first, test_end_idx_last)
    rows_oof = []
    for name, kw in MGMT_CONFIGS.items():
        log.info(f"  OOF: {name}")
        res = eval_pfunded_v3(daily_R, kw, start_indices=test_starts_all)
        rows_oof.append({
            "config": name,
            "oof_p_funded_pct": round(res["p_funded_pct"], 2)
                if not pd.isna(res["p_funded_pct"]) else float("nan"),
            "oof_p_phase1_pct": round(res["p_phase1"] * 100, 2)
                if not pd.isna(res["p_phase1"]) else float("nan"),
            "oof_n_resolved": res["n_resolved"],
            "oof_n_funded": res["n_funded"],
            "censored_pct": round(res["censored_pct"], 1),
        })
    df_oof = pd.DataFrame(rows_oof)
    print(df_oof.to_string(index=False))
    df_oof.to_csv(ROOT / "lever_c_oof_held.csv", index=False)

    merged = pd.merge(df_is, df_oof, on="config")
    merged["delta_oof_vs_is"] = merged["oof_p_funded_pct"] - merged["in_sample_p_funded_pct"]
    merged_sorted = merged.sort_values("oof_p_funded_pct", ascending=False)
    print()
    print("=" * 110)
    print("RANKED BY OOF HELD — challenge mgmt configs")
    print("=" * 110)
    print(merged_sorted.to_string(index=False))
    merged.to_csv(ROOT / "lever_c_comparison.csv", index=False)

    # 3) WF selection (pick best per training, apply to test)
    print()
    print("=" * 110)
    print("WALK-FORWARD SELECTION across mgmt configs (pick best per training)")
    print("=" * 110)
    fold_records = []
    total_resolved = 0
    total_funded = 0
    for fold_idx, (tr_end, ts_start, ts_end, tr_date, te_date) in enumerate(boundaries):
        train_starts = np.arange(0, tr_end)
        # Eval each config on training
        train_p = {}
        for name, kw in MGMT_CONFIGS.items():
            res = eval_pfunded_v3(daily_R, kw, start_indices=train_starts)
            train_p[name] = {
                "p_funded": res["p_funded"] if not pd.isna(res["p_funded"]) else -1,
                "p_phase1": res["p_phase1"] if not pd.isna(res["p_phase1"]) else -1,
                "n_resolved": res["n_resolved"],
            }
        # Pick best (min 100 resolved gate)
        ranked = sorted(
            train_p.items(),
            key=lambda kv: (
                kv[1]["p_funded"] if kv[1]["n_resolved"] >= 100 else -100,
                kv[1]["p_phase1"],
            ),
            reverse=True,
        )
        best_name = ranked[0][0]

        # Apply to test
        test_starts = np.arange(ts_start, ts_end)
        res_test = eval_pfunded_v3(daily_R, MGMT_CONFIGS[best_name], start_indices=test_starts)
        fold_records.append({
            "fold_idx": fold_idx,
            "train_end": tr_date,
            "test_end": te_date,
            "best_config": best_name,
            "train_p_funded_pct": round(train_p[best_name]["p_funded"] * 100, 2)
                if train_p[best_name]["p_funded"] > -1 else float("nan"),
            "train_n_resolved": train_p[best_name]["n_resolved"],
            "test_p_funded_pct": round(res_test["p_funded_pct"], 2)
                if not pd.isna(res_test["p_funded_pct"]) else float("nan"),
            "test_n_resolved": res_test["n_resolved"],
            "test_n_funded": res_test["n_funded"],
            "test_censored_pct": round(res_test["censored_pct"], 1),
        })
        total_resolved += res_test["n_resolved"]
        total_funded += res_test["n_funded"]
    fold_df = pd.DataFrame(fold_records)
    print(fold_df.to_string(index=False))
    fold_df.to_csv(ROOT / "lever_c_wf_selected.csv", index=False)
    wf_oof = (total_funded / total_resolved * 100) if total_resolved > 0 else float("nan")
    print()
    print(f"  WF-selection OOF p_funded: {wf_oof:.2f}% ({total_funded}/{total_resolved})")

    # Summary
    print()
    print("=" * 110)
    print("SUMMARY")
    print("=" * 110)
    baseline_row = merged[merged["config"] == "M00_baseline"].iloc[0]
    best_held = merged_sorted.iloc[0]
    print(f"  Baseline (no mgmt rule, V2+E7 only): in-sample={baseline_row['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={baseline_row['oof_p_funded_pct']:5.2f}%")
    print(f"  Best held config ({best_held['config']}): in-sample={best_held['in_sample_p_funded_pct']:5.2f}% "
           f"OOF-held={best_held['oof_p_funded_pct']:5.2f}% "
           f"(Δ OOF vs baseline: +{best_held['oof_p_funded_pct'] - baseline_row['oof_p_funded_pct']:.2f}pp)")
    print(f"  WF-selected OOF: {wf_oof:.2f}% "
           f"(Δ vs baseline: +{wf_oof - baseline_row['oof_p_funded_pct']:.2f}pp)")
