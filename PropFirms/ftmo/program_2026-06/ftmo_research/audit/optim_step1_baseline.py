"""
optim_step1_baseline.py — Baseline rescalé multi-risk (L19 reference table).

Sweeps risk-per-block ∈ {0.5..3.0%} on the 3-sleeve core, for BOTH
real-path and iid bootstrap, on full 2022-2025. Output is the L19 reference
table that every subsequent modification must be compared against.

Containers covered (sanity check):
  - ftmo_2phase
  - 1phase_static
  - 1phase_trail6
  - 1phase_daily5
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import (
    simulate_real_path_container, simulate_iid_container, CONTAINERS
)


def baseline_sweep(M: pd.DataFrame, containers: list[str],
                   risks: list[float], n_paths_iid: int = 5000,
                   seed: int = 1) -> pd.DataFrame:
    rows = []
    for c in containers:
        for r in risks:
            rp = simulate_real_path_container(M, c, block_cap_pct=r)
            iid = simulate_iid_container(M, c, block_cap_pct=r,
                                         n_paths=n_paths_iid, seed=seed)
            rows.append({
                "container": c,
                "risk_per_block_pct": r * 100,
                "n_real": rp["n_paths"],
                "REAL_p1_pct": rp["p_phase1"] * 100,
                "REAL_p2_cond_pct": (rp["p_phase2_given_p1"] or np.nan) * 100,
                "REAL_p_funded_pct": rp["p_funded"] * 100,
                "REAL_bust_total_pct": rp["p1_bust_total_pct"],
                "REAL_bust_trail_pct": rp["p1_bust_trail_pct"],
                "REAL_bust_daily_pct": rp["p1_bust_daily_pct"],
                "REAL_timeout_pct": rp["p1_timeout_pct"],
                "REAL_med_ttp_p1": rp["median_ttp_p1"],
                "REAL_med_ttp_p2": rp["median_ttp_p2"],
                "IID_p1_pct": iid["p_phase1"] * 100,
                "IID_p2_cond_pct": (iid["p_phase2_given_p1"] or np.nan) * 100,
                "IID_p_funded_pct": iid["p_funded"] * 100,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    risks = [0.005, 0.0075, 0.010, 0.0125, 0.015, 0.0175, 0.020, 0.025, 0.030]
    containers = ["ftmo_2phase", "1phase_static", "1phase_trail6", "1phase_daily5"]

    print("=" * 100)
    print("STEP 1 — L19 BASELINE SWEEP (full 2022-2025, in-sample)")
    print("=" * 100)
    df = baseline_sweep(M_full, containers, risks, n_paths_iid=5000)
    df.to_csv("optim_step1_baseline.csv", index=False)

    # Pretty print per container
    for c in containers:
        sub = df[df["container"] == c].copy()
        print(f"\n### {c}")
        cols_show = ["risk_per_block_pct", "REAL_p1_pct", "REAL_p2_cond_pct",
                     "REAL_p_funded_pct", "REAL_bust_total_pct", "REAL_bust_trail_pct",
                     "REAL_bust_daily_pct", "REAL_timeout_pct",
                     "IID_p1_pct", "IID_p_funded_pct"]
        sub_show = sub[cols_show].round(1)
        # rename for printing
        print(sub_show.to_string(index=False))
        # argmax p_funded
        best_real = sub.loc[sub["REAL_p_funded_pct"].idxmax()]
        best_iid = sub.loc[sub["IID_p_funded_pct"].idxmax()]
        print(f"  -> argmax REAL p_funded: risk={best_real['risk_per_block_pct']:.2f}% "
              f"(p_funded={best_real['REAL_p_funded_pct']:.1f}%)")
        print(f"  -> argmax IID  p_funded: risk={best_iid['risk_per_block_pct']:.2f}% "
              f"(p_funded={best_iid['IID_p_funded_pct']:.1f}%)")

    print("\nSaved -> optim_step1_baseline.csv")
