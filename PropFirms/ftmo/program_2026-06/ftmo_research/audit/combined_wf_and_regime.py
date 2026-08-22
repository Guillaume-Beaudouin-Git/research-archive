"""
combined_wf_and_regime.py — WF selection across K configs + regime-conditional K5.

1. Walk-forward expanding selection across {K0, K1, K2, K3, K4, K5, K6}.
   For each fold: select best K by training p_funded, apply to test fold.
   Aggregate OOF p_funded with selection.

2. Regime-conditional p(pass) for K5 (best).
3. Per-regime breakdown for K5 across regime buckets.

4. Honest summary: in-sample / OOF held / WF-selected / regime-cond.
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES, load_instrument
from nq_sim_v3 import simulate_2step_v3
from oof_framework import build_fold_boundaries, WF_FOLD_END_DATES
from lever_b_conditional_oof import (compute_vol_tag, compute_event_flag,
                                       vol_regime_sizing, event_sizing,
                                       VOL_CONFIGS)
from combined_pushpass import SPECS, build_daily_R_for_spec, eval_p_funded

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


REGIMES = [
    ("2010-2012", "2010-06-01", "2013-01-01"),
    ("2013-2015", "2013-01-01", "2016-01-01"),
    ("2016-2018", "2016-01-01", "2019-01-01"),
    ("2019-2021", "2019-01-01", "2022-01-01"),
    ("2022-2023", "2022-01-01", "2024-01-01"),
    ("2024-2026", "2024-01-01", "2027-01-01"),
]


if __name__ == "__main__":
    print("=" * 110)
    print("WF SELECTION + REGIME-COND for K configs")
    print("=" * 110)

    log.info("Building conditioning variables...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    vol_tag = compute_vol_tag(daily_close)
    bd_idx = pd.bdate_range(daily_close.index.min(), daily_close.index.max())
    event_flag = compute_event_flag(bd_idx)
    vol_tag_aligned = vol_tag.reindex(bd_idx).ffill().fillna("mid")

    log.info("Building daily R series per K config...")
    daily_R_per_K = {}
    mgmt_per_K = {}
    for name, spec in SPECS.items():
        log.info(f"  {name}")
        dR, _ = build_daily_R_for_spec(spec, vol_tag_aligned, event_flag)
        daily_R_per_K[name] = dR
        mgmt_per_K[name] = spec["mgmt"]

    # === Walk-forward expanding selection ===
    print()
    print("=" * 110)
    print("WALK-FORWARD EXPANDING — pick best K per training fold")
    print("=" * 110)
    ref = daily_R_per_K["K0_baseline"]
    boundaries = build_fold_boundaries(ref, WF_FOLD_END_DATES)
    fold_records = []
    total_resolved = 0
    total_funded = 0
    for fold_idx, (tr_end, ts_start, ts_end, tr_date, te_date) in enumerate(boundaries):
        train_starts = np.arange(0, tr_end)
        train_p = {}
        for name in SPECS:
            res = eval_p_funded(daily_R_per_K[name], mgmt_per_K[name],
                                 start_indices=train_starts)
            train_p[name] = {
                "p_funded": res["p_funded"] if not pd.isna(res["p_funded"]) else -1,
                "p_phase1": res["p_phase1"] if not pd.isna(res["p_phase1"]) else -1,
                "n_resolved": res["n_resolved"],
            }
        ranked = sorted(
            train_p.items(),
            key=lambda kv: (
                kv[1]["p_funded"] if kv[1]["n_resolved"] >= 100 else -100,
                kv[1]["p_phase1"],
            ),
            reverse=True,
        )
        best_name = ranked[0][0]
        test_starts = np.arange(ts_start, ts_end)
        test_res = eval_p_funded(daily_R_per_K[best_name], mgmt_per_K[best_name],
                                   start_indices=test_starts)
        fold_records.append({
            "fold_idx": fold_idx,
            "train_end": tr_date,
            "test_end": te_date,
            "best_K": best_name,
            "train_p_funded_pct": round(train_p[best_name]["p_funded"] * 100, 2),
            "train_n_resolved": train_p[best_name]["n_resolved"],
            "test_p_funded_pct": round(test_res["p_funded_pct"], 2)
                if not pd.isna(test_res["p_funded_pct"]) else float("nan"),
            "test_n_resolved": test_res["n_resolved"],
            "test_n_funded": test_res["n_funded"],
            "test_censored_pct": round(test_res["censored_pct"], 1),
        })
        total_resolved += test_res["n_resolved"]
        total_funded += test_res["n_funded"]

    fold_df = pd.DataFrame(fold_records)
    print(fold_df.to_string(index=False))
    fold_df.to_csv(ROOT / "combined_wf_selected.csv", index=False)
    wf_oof = (total_funded / total_resolved * 100) if total_resolved > 0 else float("nan")
    print()
    print(f"  WF-selected OOF p_funded across {len(boundaries)} folds: "
           f"{wf_oof:.2f}% ({total_funded}/{total_resolved})")

    # === Regime decomp for K5 ===
    print()
    print("=" * 110)
    print("REGIME DECOMPOSITION — K5 (V2+E7+floor+vol_high)")
    print("=" * 110)
    K5_R = daily_R_per_K["K5_V2E7_floor_vol"]
    K5_mgmt = mgmt_per_K["K5_V2E7_floor_vol"]
    rows = []
    for name, lo, hi in REGIMES:
        mask = (K5_R.index >= pd.Timestamp(lo)) & (K5_R.index < pd.Timestamp(hi))
        idx_range = np.where(mask)[0]
        if len(idx_range) == 0:
            rows.append({"block": name, "n_days": 0})
            continue
        # Run sim only with starts in this regime
        res = eval_p_funded(K5_R, K5_mgmt, start_indices=idx_range)
        rows.append({
            "block": name,
            "n_days": len(idx_range),
            "n_resolved": res["n_resolved"],
            "n_funded": res["n_funded"],
            "p_phase1_pct": round(res["p_phase1"] * 100, 2)
                if not pd.isna(res["p_phase1"]) else float("nan"),
            "p_funded_pct": round(res["p_funded_pct"], 2)
                if not pd.isna(res["p_funded_pct"]) else float("nan"),
            "censored_pct": round(res["censored_pct"], 1),
        })
    reg_df = pd.DataFrame(rows)
    print(reg_df.to_string(index=False))
    reg_df.to_csv(ROOT / "combined_K5_regime.csv", index=False)

    # === Regime-conditional via vol tercile (NOWCAST) ===
    print()
    print("=" * 110)
    print("VOL-REGIME CONDITIONAL p(pass) — K5")
    print("=" * 110)
    vol_aligned = vol_tag_aligned.reindex(K5_R.index)
    rows = []
    for r_name in ["low", "mid", "high"]:
        idx = np.where(vol_aligned == r_name)[0]
        if len(idx) < 30:
            rows.append({"vol_regime": r_name, "n_starts": len(idx)})
            continue
        res = eval_p_funded(K5_R, K5_mgmt, start_indices=idx)
        rows.append({
            "vol_regime": r_name,
            "n_starts": len(idx),
            "n_resolved": res["n_resolved"],
            "n_funded": res["n_funded"],
            "p_phase1_pct": round(res["p_phase1"] * 100, 2)
                if not pd.isna(res["p_phase1"]) else float("nan"),
            "p_funded_pct": round(res["p_funded_pct"], 2)
                if not pd.isna(res["p_funded_pct"]) else float("nan"),
            "censored_pct": round(res["censored_pct"], 1),
        })
    vol_df = pd.DataFrame(rows)
    print(vol_df.to_string(index=False))
    vol_df.to_csv(ROOT / "combined_K5_vol_regime.csv", index=False)

    # === Today's regime ===
    print()
    print("=" * 110)
    print("REGIME ACTUEL")
    print("=" * 110)
    last_idx = K5_R.dropna().index[-1] if not K5_R.dropna().empty else K5_R.index[-1]
    rv_last = vol_aligned.loc[last_idx] if last_idx in vol_aligned.index else "unknown"
    print(f"  Last date: {last_idx}")
    print(f"  Current vol tercile: **{rv_last}**")
    cur_row = vol_df[vol_df["vol_regime"] == rv_last] if rv_last in ["low", "mid", "high"] else None
    if cur_row is not None and len(cur_row) > 0:
        print(f"  Honest p(pass) today (K5, regime={rv_last}): "
               f"**{cur_row.iloc[0]['p_funded_pct']:.1f}%**")
