"""
optim_step5b_gate_risk_sweep.py — Sweep gate × risk to find the joint argmax.

For each (gate, risk) combination on 1phase_static, report FULL p_funded + WF mean.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from optim_step5_regime_gate import get_feature_terciles, full_with_gate, wf_with_gate


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    risks = [0.0075, 0.010, 0.0125, 0.015, 0.0175, 0.020]
    container = "1phase_static"
    gates = [
        ("vr5", 0, "vr5_low"),
        ("trend20", 1, "trend20_mid"),
        ("rv20", 1, "rv20_mid"),
    ]

    rows = []
    for risk in risks:
        # No gate
        rp = simulate_real_path_container(M_full, container, block_cap_pct=risk)
        rows.append({
            "container": container, "risk_pct": risk * 100, "gate": "NONE",
            "FULL_p_funded": rp["p_funded"] * 100,
            "WF_mean_p_funded": None,  # baseline WF in optim_step2_wf.csv
            "n_starts": rp["n_paths"],
        })
        for feat, terc, label in gates:
            res = full_with_gate(M_full, container, risk, feat, terc)
            wf = wf_with_gate(M_full, container, risk, feat, terc, n_folds=5)
            rows.append({
                "container": container, "risk_pct": risk * 100, "gate": label,
                "FULL_p_funded": res["gated_p_funded"],
                "WF_mean_p_funded": wf["p_funded_gated_pct"].mean(),
                "WF_min_p_funded": wf["p_funded_gated_pct"].min(),
                "fold3_chop": wf["p_funded_gated_pct"].iloc[2],
                "n_starts": res["gated_n"],
            })
    df = pd.DataFrame(rows)
    df.to_csv("optim_step5b_gate_risk.csv", index=False)
    piv_full = df.pivot(index="risk_pct", columns="gate", values="FULL_p_funded").round(1)
    print("=" * 80)
    print("FULL_p_funded (1phase_static) by (risk × gate) — in-sample on 2022-2025")
    print("=" * 80)
    print(piv_full.to_string())

    piv_wf = df.pivot(index="risk_pct", columns="gate", values="WF_mean_p_funded").round(1)
    print()
    print("=" * 80)
    print("WF_mean_p_funded (5 folds) — same axis. Use WF mean as honest estimate.")
    print("=" * 80)
    print(piv_wf.to_string())
    print()
    # Best combo
    best = df.dropna(subset=["WF_mean_p_funded"]).loc[df.dropna(subset=["WF_mean_p_funded"])["WF_mean_p_funded"].idxmax()]
    print(f"\nArgmax WF_mean: risk={best['risk_pct']}%, gate={best['gate']}, "
          f"WF mean = {best['WF_mean_p_funded']:.1f}%, FULL = {best['FULL_p_funded']:.1f}%")
