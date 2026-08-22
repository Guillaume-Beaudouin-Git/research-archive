"""
ftmo_us100_cost_sweep.py — Recompute K1/K5 p_funded under US100 CFD realistic costs.

The original combined_pushpass used COST_BPS=2.0 RT on NQ futures.
For FTMO US100 CFD live, realistic costs are higher:
  - Liquid hours spread: 0.7-1.0 pt → at US100~25000 = 3-4 bps single side
  - During 09:30 ET open (when ORB triggers): 2-4 pts spread = 8-16 bps single side
  - RT realistic: ~6-12 bps depending on auction slippage

Sweep cost_bps_rt ∈ {2 (NQ futures, baseline), 4, 6, 8, 10, 12} and report:
  - p(funded) in-sample
  - p(funded) OOF held (test folds only)
  - effective leverage (with floor_taper)
  - DSR survival

Re-run V2+E7 alone (K1) AND V2+E7+floor_taper+vol_high (K5) — the two key configs.
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
                                       vol_regime_sizing, event_sizing, VOL_CONFIGS)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Configs to test
SPECS = {
    "V2+E7 (K1)": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": None, "event_factor": (1.0, 1.0),
        "mgmt": {},
    },
    "V2+E7+floor (K2)": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": None, "event_factor": (1.0, 1.0),
        "mgmt": {"floor_proximity_taper": True, "taper_min_factor": 0.25},
    },
    "V2+E7+floor+vol_high (K5)": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": VOL_CONFIGS["B04_vol_high_only"],
        "event_factor": (1.0, 1.0),
        "mgmt": {"floor_proximity_taper": True, "taper_min_factor": 0.25},
    },
}


def build_daily_R_for_cost(spec: dict, cost_bps: float,
                             vol_tag: pd.Series, event_flag: pd.Series):
    """Build daily R with explicit cost."""
    sleeve = SLEEVES["NQ"]  # Use NQ data as proxy for ORB-on-index
    tl = build_orb_trades(sleeve, filter_spec=spec["filter"], exit_spec=spec["exit"],
                            cost_bps_rt=cost_bps)
    dR = build_daily_R_series(tl)
    if spec["vol_sizing"] is not None:
        dR = vol_regime_sizing(dR, vol_tag.reindex(dR.index), spec["vol_sizing"])
    ev_f, nev_f = spec["event_factor"]
    if ev_f != 1.0 or nev_f != 1.0:
        dR = event_sizing(dR, event_flag.reindex(dR.index), ev_f, nev_f)
    return dR, tl


def eval_p_funded(daily_R, mgmt, start_indices=None, block_cap=0.005):
    bcp1 = mgmt.get("block_cap_p1", block_cap)
    bcp2 = mgmt.get("block_cap_p2", block_cap)
    kw = {k: v for k, v in mgmt.items() if k not in ("block_cap_p1", "block_cap_p2")}
    si = start_indices.tolist() if start_indices is not None else None
    return simulate_2step_v3(daily_R, block_cap_p1=bcp1, block_cap_p2=bcp2,
                              start_indices=si, **kw)


if __name__ == "__main__":
    log.info("Building conditioning variables...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    vol_tag = compute_vol_tag(daily_close)
    bd_idx = pd.bdate_range(daily_close.index.min(), daily_close.index.max())
    event_flag = compute_event_flag(bd_idx)
    vol_tag_aligned = vol_tag.reindex(bd_idx).ffill().fillna("mid")

    cost_levels = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    print("=" * 115)
    print("FTMO US100 CFD COST SWEEP — re-validate K1/K2/K5 under realistic cost")
    print("=" * 115)
    print(f"\nCost levels (bps RT): {cost_levels}")
    print("Baseline NQ futures = 2 bps RT")
    print("US100 CFD realistic: liquid hours 6-8 bps, open auction 10-12 bps")
    print()

    rows = []
    for cost in cost_levels:
        for cfg_name, spec in SPECS.items():
            dR, tl = build_daily_R_for_cost(spec, cost, vol_tag_aligned, event_flag)
            is_res = eval_p_funded(dR, spec["mgmt"])
            boundaries = build_fold_boundaries(dR, WF_FOLD_END_DATES)
            test_start_first = boundaries[0][1]
            test_end_last = boundaries[-1][2]
            test_starts_all = np.arange(test_start_first, test_end_last)
            oof_res = eval_p_funded(dR, spec["mgmt"], start_indices=test_starts_all)
            mean_R = float(tl["r_realised"].mean()) if not tl.empty else float("nan")
            std_R = float(tl["r_realised"].std()) if not tl.empty else float("nan")
            rows.append({
                "cost_bps": cost,
                "config": cfg_name,
                "n_trades": len(tl),
                "mean_R": round(mean_R, 4),
                "std_R": round(std_R, 4),
                "in_sample_pfunded": round(is_res["p_funded_pct"], 1)
                    if not pd.isna(is_res["p_funded_pct"]) else float("nan"),
                "oof_held_pfunded": round(oof_res["p_funded_pct"], 1)
                    if not pd.isna(oof_res["p_funded_pct"]) else float("nan"),
                "oof_n_resolved": oof_res["n_resolved"],
                "oof_n_funded": oof_res["n_funded"],
                "oof_censored_pct": round(oof_res["censored_pct"], 1),
            })

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "ftmo_us100_cost_sweep.csv", index=False)
    print(df.to_string(index=False))

    # Pivots
    print()
    print("=" * 115)
    print("OOF p_funded by (cost × config)")
    print("=" * 115)
    piv = df.pivot_table(index="cost_bps", columns="config", values="oof_held_pfunded")
    print(piv.round(1).to_string())

    print()
    print("Mean R per trade by (cost × config)")
    piv2 = df.pivot_table(index="cost_bps", columns="config", values="mean_R")
    print(piv2.round(4).to_string())

    # Decision thresholds
    print()
    print("=" * 115)
    print("DECISION — GO threshold p_funded ~50%, KILL threshold ~30%")
    print("=" * 115)
    for cost in cost_levels:
        sub = df[df["cost_bps"] == cost]
        best = sub.sort_values("oof_held_pfunded", ascending=False).iloc[0]
        verdict = ("GO" if best["oof_held_pfunded"] >= 50 else
                    ("MARGINAL" if best["oof_held_pfunded"] >= 30 else "KILL"))
        print(f"  cost_bps={cost:4.0f}: best={best['config']:>30s} pfunded={best['oof_held_pfunded']:5.1f}% "
              f"meanR={best['mean_R']:+.4f} → {verdict}")
