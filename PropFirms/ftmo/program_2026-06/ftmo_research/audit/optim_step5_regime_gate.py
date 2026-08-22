"""
optim_step5_regime_gate.py — Regime gate × container × WF (L19 ablation).

CONDITIONAL on Step 4 showing a container CLOSE to 70%.

Gates tested:
  - vr5 low tercile (best in audit Step 5-A)
  - trend20 mid tercile (best alternative)
  - rv20 mid tercile (alternative)
  - vr5_low OR trend20_mid (combined)

Containers (the realistic ones):
  - ftmo_2phase   @ argmax baseline risk = 1.25%
  - 1phase_static @ argmax baseline risk = 1.25%

L19 ablation: each gate compared to baseline-no-gate at SAME container and SAME risk.

⚠ N≈1 caveat: the regime gate is fit on 2022-2025 which has ~3-5 distinct chop
episodes, dominated by 2023. WF dispersion will reveal in-sample overfit.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from step5_regime import (
    underlying_daily_log_returns, rolling_features, tag_terciles_expanding
)
from optim_step2_finegrid import make_wf_folds


def get_feature_terciles(M: pd.DataFrame) -> pd.DataFrame:
    """Compute features and terciles for each calendar day in M."""
    r_us = underlying_daily_log_returns("US100", "2020", "2026")
    r_ger = underlying_daily_log_returns("GER40", "2020", "2026")
    feat_us = rolling_features(r_us)
    feat_ger = rolling_features(r_ger)
    feat_avg = (feat_us.reindex(M.index) + feat_ger.reindex(M.index)) / 2
    out = pd.DataFrame(index=M.index)
    for fname in ["rv20", "vr5", "vr10", "trend20"]:
        out[fname] = feat_avg[fname]
        out[fname + "_tercile"] = tag_terciles_expanding(feat_avg[fname])
    return out


def gate_real_path(M: pd.DataFrame, container: str, risk: float,
                   gate_mask_at_starts: np.ndarray) -> dict:
    """Run simulate_real_path_container only at start indices where gate is True."""
    rp_full = simulate_real_path_container(M, container, block_cap_pct=risk)
    n_starts = len(rp_full["starts"])
    starts_full = rp_full["starts"]
    if len(gate_mask_at_starts) != n_starts:
        # Truncate mask to match starts
        gate_mask_at_starts = gate_mask_at_starts[:n_starts]
    selected_starts = starts_full[gate_mask_at_starts]
    if len(selected_starts) == 0:
        return {"p_funded": float("nan"), "p_phase1": float("nan"),
                "n_selected": 0}
    rp_gated = simulate_real_path_container(
        M, container, block_cap_pct=risk, start_indices=selected_starts)
    return rp_gated


def wf_with_gate(M: pd.DataFrame, container: str, risk: float,
                  gate_feature: str, gate_tercile: int,
                  n_folds: int = 5) -> pd.DataFrame:
    """
    Walk-forward: compute gate features expanding (terciles use only history),
    then apply gate per fold and compute p_funded.
    """
    feats = get_feature_terciles(M)
    folds = make_wf_folds(M, n_folds)
    rows = []
    for fname, fold in folds:
        # No gate (L19 baseline at same risk)
        rp_nogate = simulate_real_path_container(fold, container, block_cap_pct=risk)
        # With gate: get tercile values at start dates in this fold
        starts = rp_nogate["starts"]
        start_dates = fold.index[starts]
        feat_at_start = feats[gate_feature + "_tercile"].reindex(start_dates).values
        gate_mask = (feat_at_start == gate_tercile)
        gate_n = int(np.nansum(gate_mask))
        if gate_n > 0:
            selected_starts = starts[gate_mask.astype(bool)]
            rp_gate = simulate_real_path_container(
                fold, container, block_cap_pct=risk, start_indices=selected_starts)
            p_funded_gated = rp_gate["p_funded"] * 100
            p1_gated = rp_gate["p_phase1"] * 100
        else:
            p_funded_gated = float("nan")
            p1_gated = float("nan")
        rows.append({
            "fold": fname,
            "container": container,
            "risk_pct": risk * 100,
            "feature": gate_feature,
            "tercile": gate_tercile,
            "n_nogate": rp_nogate["n_paths"],
            "n_gated": gate_n,
            "p_funded_nogate_pct": rp_nogate["p_funded"] * 100,
            "p_funded_gated_pct": p_funded_gated,
            "p1_nogate_pct": rp_nogate["p_phase1"] * 100,
            "p1_gated_pct": p1_gated,
        })
    return pd.DataFrame(rows)


def full_with_gate(M: pd.DataFrame, container: str, risk: float,
                    gate_feature: str, gate_tercile: int) -> dict:
    """Full-sample (in-sample) gate measurement."""
    feats = get_feature_terciles(M)
    rp_nogate = simulate_real_path_container(M, container, block_cap_pct=risk)
    starts = rp_nogate["starts"]
    start_dates = M.index[starts]
    feat_at_start = feats[gate_feature + "_tercile"].reindex(start_dates).values
    gate_mask = (feat_at_start == gate_tercile)
    selected_starts = starts[gate_mask.astype(bool)]
    rp_gate = simulate_real_path_container(
        M, container, block_cap_pct=risk, start_indices=selected_starts)
    return {
        "nogate_p_funded": rp_nogate["p_funded"] * 100,
        "nogate_p1": rp_nogate["p_phase1"] * 100,
        "nogate_n": rp_nogate["n_paths"],
        "gated_p_funded": rp_gate["p_funded"] * 100,
        "gated_p1": rp_gate["p_phase1"] * 100,
        "gated_n": rp_gate["n_paths"],
    }


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    risk = 0.0125  # best baseline from Steps 1-2

    gates = [
        ("vr5", 0, "vr5 low tercile"),
        ("trend20", 1, "trend20 mid tercile"),
        ("rv20", 1, "rv20 mid tercile"),
    ]

    for container in ["ftmo_2phase", "1phase_static"]:
        print("=" * 100)
        print(f"STEP 5 — REGIME GATE × {container} @ risk={risk*100}%")
        print("=" * 100)
        # Baseline FULL
        nogate_full = simulate_real_path_container(M_full, container, block_cap_pct=risk)
        print(f"  Baseline (no gate, FULL 2022-25): p_funded={nogate_full['p_funded']*100:.1f}%, "
              f"p1={nogate_full['p_phase1']*100:.1f}%, n={nogate_full['n_paths']}")
        for feat, terc, label in gates:
            res = full_with_gate(M_full, container, risk, feat, terc)
            delta = res["gated_p_funded"] - res["nogate_p_funded"]
            print(f"\n  Gate: {label}")
            print(f"    FULL: p_funded={res['gated_p_funded']:.1f}% (Δ={delta:+.1f}pt), "
                  f"p1={res['gated_p1']:.1f}%, n_selected={res['gated_n']}/{res['nogate_n']}")
            # WF
            wf = wf_with_gate(M_full, container, risk, feat, terc, n_folds=5)
            print(f"    WF per-fold:")
            for _, row in wf.iterrows():
                d = row["p_funded_gated_pct"] - row["p_funded_nogate_pct"] if pd.notna(row["p_funded_gated_pct"]) else float("nan")
                print(f"      {row['fold'][:30]:30s} nogate={row['p_funded_nogate_pct']:.1f}% "
                      f"gated={row['p_funded_gated_pct']:.1f}% Δ={d:+.1f}pt n_gated={int(row['n_gated'])}")
            print(f"    WF mean gated = {wf['p_funded_gated_pct'].mean():.1f}% "
                  f"vs WF mean nogate = {wf['p_funded_nogate_pct'].mean():.1f}%")
            wf.to_csv(f"optim_step5_{container}_{feat}_t{terc}.csv", index=False)
