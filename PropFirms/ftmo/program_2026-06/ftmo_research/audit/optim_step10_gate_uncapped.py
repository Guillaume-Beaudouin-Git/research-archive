"""
optim_step10_gate_uncapped.py — Regime gate on FTMO 2-step uncapped.

Applies the vr5 low / trend20 mid gate as a date filter on the start position
of the uncapped 2-step container. L19 ablation: same risk, same container,
no-gate vs gated.

⚠ in-sample N≈1: gate fitted on 2022-2025 with single chop episode (2023).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from step5_regime import (
    underlying_daily_log_returns, rolling_features, tag_terciles_expanding
)


def get_feature_terciles(M: pd.DataFrame) -> pd.DataFrame:
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


def gated_uncapped(M: pd.DataFrame, risk: float,
                   gate_feature: str | None, gate_tercile: int | None,
                   precomputed_full: dict | None = None) -> dict:
    """Run uncapped 2-step on starts where gate is True; or no gate if gate=None.

    precomputed_full: optionally pass the no-gate run output to avoid recomputing
    the full simulation for each gate. We then sub-select outcomes by gate mask.
    """
    if precomputed_full is None:
        precomputed_full = simulate_real_path_container(
            M, "ftmo_2step_uncapped", block_cap_pct=risk
        )
    if gate_feature is None:
        return precomputed_full
    starts = precomputed_full["starts"]
    feats = get_feature_terciles(M)
    start_dates = M.index[starts]
    feat_at_start = feats[gate_feature + "_tercile"].reindex(start_dates).values
    gate_mask = (feat_at_start == gate_tercile)
    if gate_mask.sum() == 0:
        return None
    # Sub-select outcomes from the full run rather than re-simulating
    p1_out = np.array(precomputed_full["outcomes_p1"])[gate_mask]
    p2_out = np.array(precomputed_full["outcomes_p2"])[gate_mask]
    p1_ttp = np.array(precomputed_full["ttps_p1"])[gate_mask]
    p2_ttp = np.array(precomputed_full["ttps_p2"])[gate_mask]
    resolved_mask_full = precomputed_full["resolved_mask"][gate_mask]
    n_total = len(p1_out)
    n_resolved = int(resolved_mask_full.sum())
    n_censored = n_total - n_resolved
    funded_mask = (p1_out == "PASS") & (p2_out == "PASS") & resolved_mask_full
    p1_pass_mask = (p1_out == "PASS") & resolved_mask_full
    n_p1_pass = int(p1_pass_mask.sum())
    p_p1 = n_p1_pass / n_resolved if n_resolved else float("nan")
    p_funded = int(funded_mask.sum()) / n_resolved if n_resolved else float("nan")
    p_p2 = (int(funded_mask.sum()) / n_p1_pass) if n_p1_pass else 0.0
    # Median grind for funded
    grinds = [(p1_ttp[i] + (p2_ttp[i] if p2_ttp[i] > 0 else 0))
              for i in range(n_total) if funded_mask[i]]
    return {
        "container": "ftmo_2step_uncapped",
        "n_paths": n_total,
        "n_resolved": n_resolved,
        "n_censored": n_censored,
        "censored_pct": (n_censored / n_total * 100) if n_total else 0.0,
        "p_phase1": p_p1,
        "p_phase2_given_p1": p_p2,
        "p_funded": p_funded,
        "median_grind_p1p2": int(np.median(grinds)) if grinds else None,
    }


if __name__ == "__main__":
    M_all = build_3sleeve_matrix(lo="2022", hi="2026")
    risks = [0.005, 0.0075, 0.010, 0.0125]
    gates = [
        (None, None, "NONE (baseline)"),
        ("vr5", 0, "vr5_low"),
        ("trend20", 1, "trend20_mid"),
        ("rv20", 1, "rv20_mid"),
    ]
    print("=" * 110)
    print("STEP 10 — REGIME GATE × FTMO 2-step UNCAPPED")
    print("=" * 110)
    rows = []
    for r in risks:
        # Compute the full uncapped simulation ONCE per risk, then reuse for each gate
        full_run = simulate_real_path_container(M_all, "ftmo_2step_uncapped", block_cap_pct=r)
        for feat, terc, label in gates:
            out = gated_uncapped(M_all, r, feat, terc, precomputed_full=full_run)
            if out is None:
                continue
            rows.append({
                "risk_pct": r * 100,
                "gate": label,
                "n_total": out["n_paths"],
                "n_resolved": out["n_resolved"],
                "censored_pct": out["censored_pct"],
                "p1_pct": out["p_phase1"] * 100 if not np.isnan(out["p_phase1"]) else float("nan"),
                "p2_given_p1_pct": (out["p_phase2_given_p1"] * 100
                                     if (out["p_phase2_given_p1"] is not None
                                         and not np.isnan(out["p_phase2_given_p1"])) else float("nan")),
                "p_funded_pct": out["p_funded"] * 100 if not np.isnan(out["p_funded"]) else float("nan"),
                "median_grind": out["median_grind_p1p2"],
            })
    df = pd.DataFrame(rows)
    df.to_csv("optim_step10_gate_uncapped.csv", index=False)
    # Pretty pivot
    piv = df.pivot(index="risk_pct", columns="gate", values="p_funded_pct").round(1)
    cols_order = ["NONE (baseline)", "rv20_mid", "trend20_mid", "vr5_low"]
    piv = piv[[c for c in cols_order if c in piv.columns]]
    print("\np_funded by (risk × gate):")
    print(piv.to_string())
    piv2 = df.pivot(index="risk_pct", columns="gate", values="censored_pct").round(1)
    piv2 = piv2[[c for c in cols_order if c in piv2.columns]]
    print("\ncensored_pct by (risk × gate):")
    print(piv2.to_string())

    # Ablation L19: delta gate vs none per (risk)
    print("\nL19 ABLATION (Δ vs baseline at SAME risk):")
    for r in risks:
        baseline = df[(df["risk_pct"] == r * 100) & (df["gate"] == "NONE (baseline)")]
        if len(baseline) == 0:
            continue
        baseline_pf = baseline.iloc[0]["p_funded_pct"]
        print(f"\n  risk={r*100:.2f}% baseline p(funded) = {baseline_pf:.1f}%")
        for feat, terc, label in gates[1:]:
            row = df[(df["risk_pct"] == r * 100) & (df["gate"] == label)]
            if len(row) == 0:
                continue
            delta = row.iloc[0]["p_funded_pct"] - baseline_pf
            cen_delta = row.iloc[0]["censored_pct"] - baseline.iloc[0]["censored_pct"]
            print(f"    + {label:>12s}: p_funded={row.iloc[0]['p_funded_pct']:.1f}% "
                  f"Δ={delta:+.1f}pt censure={row.iloc[0]['censored_pct']:.1f}% (Δcens={cen_delta:+.1f}pt)")
