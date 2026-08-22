"""
combined_pushpass.py — Stack best from A + B + C, compute honest OOF + DSR.

Final candidate configs:
  K0 baseline                : V0 + E0 + nothing
  K1 V2+E7 (Lever A best)    : V2 filter + E7 trail_BE exit
  K2 K1 + M06 floor_taper    : + reduce risk near floor
  K3 K1 + B04 vol_high_only  : + sizing 0.3/0.3/0.7 by vol regime
  K4 K1 + B21 drop_events    : + skip FOMC/NFP/CPI days
  K5 K1 + M06 + B04          : Levers A + C + B (top of B)
  K6 K1 + M06 + B04 + B21    : all three stacked

For each candidate:
  - In-sample p_funded (full 2010-2026 starts)
  - OOF held p_funded (test-fold starts only)
  - WF-selected aggregate (we don't re-select per fold for the final combo —
    each Kx is one fixed config — but we report the WF-selected from each Lever
    pre-determined choice and apply to the test folds)

DSR Bailey-LdP:
  - n_trials accountable: 12 (Lever A) + 16 (Lever C) + 17 (Lever B) +
    7 (combined K) ≈ 52 trials honest.
  - Compute SR per-trade on the trade log, apply DSR formula.

Output: combined_pushpass.csv + combined_pushpass_output.txt.
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd
from scipy import stats as scstats

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES, load_instrument
from nq_sim_v3 import simulate_2step_v3
from oof_framework import build_fold_boundaries, WF_FOLD_END_DATES
from lever_b_conditional_oof import (compute_vol_tag, compute_dow,
                                      compute_event_flag, vol_regime_sizing,
                                      event_sizing, VOL_CONFIGS)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

COST_BPS = 2.0


# Filter / exit candidate specs
SPECS = {
    "K0_baseline": {
        "filter": {}, "exit": {"kind": "at_close"},
        "vol_sizing": None, "event_factor": (1.0, 1.0),
        "mgmt": {},
    },
    "K1_V2_E7": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": None, "event_factor": (1.0, 1.0),
        "mgmt": {},
    },
    "K2_V2E7_floor": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": None, "event_factor": (1.0, 1.0),
        "mgmt": {"floor_proximity_taper": True, "taper_min_factor": 0.25},
    },
    "K3_V2E7_vol_high": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": VOL_CONFIGS["B04_vol_high_only"],
        "event_factor": (1.0, 1.0),
        "mgmt": {},
    },
    "K4_V2E7_drop_events": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": None, "event_factor": (0.0, 1.0),  # drop event days
        "mgmt": {},
    },
    "K5_V2E7_floor_vol": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": VOL_CONFIGS["B04_vol_high_only"],
        "event_factor": (1.0, 1.0),
        "mgmt": {"floor_proximity_taper": True, "taper_min_factor": 0.25},
    },
    "K6_all": {
        "filter": {"kind": "pct", "min_pct": 0.001},
        "exit": {"kind": "trailing", "trigger_R": 1.0, "lock_R": 0.0},
        "vol_sizing": VOL_CONFIGS["B04_vol_high_only"],
        "event_factor": (0.0, 1.0),
        "mgmt": {"floor_proximity_taper": True, "taper_min_factor": 0.25},
    },
}


def build_daily_R_for_spec(spec: dict, vol_tag: pd.Series, event_flag: pd.Series) -> pd.Series:
    """Build daily R series with filter+exit, scaled by vol_sizing and event_factor."""
    sleeve = SLEEVES["NQ"]
    tl = build_orb_trades(sleeve, filter_spec=spec["filter"], exit_spec=spec["exit"],
                           cost_bps_rt=COST_BPS)
    dR = build_daily_R_series(tl)
    # Apply conditional sizing scales
    if spec["vol_sizing"] is not None:
        dR = vol_regime_sizing(dR, vol_tag.reindex(dR.index), spec["vol_sizing"])
    ev_f, nev_f = spec["event_factor"]
    if ev_f != 1.0 or nev_f != 1.0:
        dR = event_sizing(dR, event_flag.reindex(dR.index), ev_f, nev_f)
    return dR, tl


def eval_p_funded(daily_R: pd.Series, mgmt: dict,
                    start_indices: np.ndarray | None = None,
                    block_cap: float = 0.005) -> dict:
    bcp1 = mgmt.get("block_cap_p1", block_cap)
    bcp2 = mgmt.get("block_cap_p2", block_cap)
    kw = {k: v for k, v in mgmt.items() if k not in ("block_cap_p1", "block_cap_p2")}
    si = start_indices.tolist() if start_indices is not None else None
    return simulate_2step_v3(daily_R, block_cap_p1=bcp1, block_cap_p2=bcp2,
                              start_indices=si, **kw)


def dsr_bailey_lopezdeprado(sr: float, n_obs: int, n_trials: int,
                              skew_r: float = 0.0, kurt_r: float = 3.0) -> dict:
    if n_trials < 2:
        emax = 0.0
    else:
        gamma = 0.5772156649
        emax = (1 - gamma) * scstats.norm.ppf(1 - 1.0 / n_trials) + \
                gamma * scstats.norm.ppf(1 - 1.0 / (n_trials * np.e))
    denom = np.sqrt(max(1e-12, 1 - skew_r * sr + ((kurt_r - 1) / 4) * sr**2))
    sr_n = sr * np.sqrt(n_obs - 1) / denom
    z = sr_n - emax
    return {"sr": float(sr), "sr_normalized": round(float(sr_n), 3),
             "n_obs": n_obs, "n_trials": n_trials,
             "emax": round(float(emax), 3), "z": round(float(z), 3),
             "dsr_p": round(float(scstats.norm.cdf(z)), 4)}


if __name__ == "__main__":
    print("=" * 110)
    print("COMBINED PUSH-PASS — stack A + B + C, in-sample vs OOF vs deflated")
    print("=" * 110)

    log.info("Building conditioning variables...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    vol_tag = compute_vol_tag(daily_close)
    # Build event flag using NQ index (then will be aligned per config)
    # We need a 'master' date index that covers all SPECS; using business days
    # over data range:
    bd_idx = pd.bdate_range(daily_close.index.min(), daily_close.index.max())
    event_flag = compute_event_flag(bd_idx)
    vol_tag_aligned = vol_tag.reindex(bd_idx).ffill().fillna("mid")

    rows = []
    spec_trade_logs = {}
    for name, spec in SPECS.items():
        log.info(f"  Building {name}...")
        dR, tl = build_daily_R_for_spec(spec, vol_tag_aligned, event_flag)
        spec_trade_logs[name] = (dR, tl)

        # In-sample p_funded
        is_res = eval_p_funded(dR, spec["mgmt"])
        # OOF held
        boundaries = build_fold_boundaries(dR, WF_FOLD_END_DATES)
        test_start_first = boundaries[0][1]
        test_end_last = boundaries[-1][2]
        test_starts_all = np.arange(test_start_first, test_end_last)
        oof_res = eval_p_funded(dR, spec["mgmt"], start_indices=test_starts_all)

        rows.append({
            "config": name,
            "in_sample_p_funded_pct": round(is_res["p_funded_pct"], 2)
                if not pd.isna(is_res["p_funded_pct"]) else float("nan"),
            "in_sample_p_phase1_pct": round(is_res["p_phase1"] * 100, 2)
                if not pd.isna(is_res["p_phase1"]) else float("nan"),
            "in_sample_n_resolved": is_res["n_resolved"],
            "in_sample_censored_pct": round(is_res["censored_pct"], 1),
            "oof_held_p_funded_pct": round(oof_res["p_funded_pct"], 2)
                if not pd.isna(oof_res["p_funded_pct"]) else float("nan"),
            "oof_held_p_phase1_pct": round(oof_res["p_phase1"] * 100, 2)
                if not pd.isna(oof_res["p_phase1"]) else float("nan"),
            "oof_held_n_resolved": oof_res["n_resolved"],
            "oof_held_n_funded": oof_res["n_funded"],
            "oof_held_censored_pct": round(oof_res["censored_pct"], 1),
            "n_trades": len(tl),
            "delta_oof_vs_is": round(oof_res["p_funded_pct"] - is_res["p_funded_pct"], 2)
                if not pd.isna(oof_res["p_funded_pct"]) else float("nan"),
        })

    df = pd.DataFrame(rows)
    print()
    print(df.to_string(index=False))
    df.to_csv(ROOT / "combined_pushpass.csv", index=False)

    # DSR computation on the best OOF held config
    print()
    print("=" * 110)
    print("DSR — Bailey-Lopez de Prado on best OOF held")
    print("=" * 110)
    n_trials = 12 + 16 + 17 + 7  # A + C + B + combined
    print(f"  Honest n_trials = {n_trials} (Lever A 12 + C 16 + B 17 + combined 7)")
    best_row = df.sort_values("oof_held_p_funded_pct", ascending=False).iloc[0]
    best_name = best_row["config"]
    print(f"  Best by OOF held: {best_name}")
    print(f"    in-sample p_funded: {best_row['in_sample_p_funded_pct']}%")
    print(f"    OOF held p_funded : {best_row['oof_held_p_funded_pct']}%")

    # For DSR, compute per-trade SR on the trade log of the best config
    dR_best, tl_best = spec_trade_logs[best_name]
    if not tl_best.empty:
        pnls = tl_best["r_realised"].values
        n = len(pnls)
        m = float(np.mean(pnls))
        s = float(np.std(pnls, ddof=1))
        sr_pt = m / s if s > 0 else 0.0
        skew = float(scstats.skew(pnls))
        kurt = float(scstats.kurtosis(pnls, fisher=False))
        print(f"    per-trade SR: {sr_pt:.4f} (mean={m:.4f}, std={s:.4f})")
        print(f"    skew: {skew:.3f}, kurt: {kurt:.3f}, n_trades: {n}")
        dsr = dsr_bailey_lopezdeprado(sr_pt, n, n_trials, skew_r=skew, kurt_r=kurt)
        for k, v in dsr.items():
            print(f"      {k}: {v}")

    print()
    print("=" * 110)
    print("Summary table (in-sample / OOF held / Δ)")
    print("=" * 110)
    print(df[["config", "in_sample_p_funded_pct", "oof_held_p_funded_pct",
              "delta_oof_vs_is", "n_trades"]].to_string(index=False))
