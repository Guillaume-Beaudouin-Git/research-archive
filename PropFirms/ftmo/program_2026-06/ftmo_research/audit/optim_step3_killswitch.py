"""
optim_step3_killswitch.py — Kill-switch sweep + L19 ablation.

Two parameters:
  - killswitch_daily_pct  ∈ {None, 2, 2.5, 3, 4}%  : halt remaining day after intraday -X%
  - killswitch_total_pct  ∈ {None, 6, 7, 8}%      : halt the attempt entirely after -Y% total

Tested across 2 containers (the realistic ones):
  - ftmo_2phase   @ best baseline risk = 1.25%
  - 1phase_static @ best baseline risk = 1.25%

L19 ablation:
  Each (kd, kt) cell compared against the SAME container at the SAME risk
  WITHOUT kill-switch (the "baseline rescaled at the same leverage" required by L19).

WF 5 folds. Report:
  - mean across folds
  - min/max
  - per-fold values for fold3 (chop) — the failure-mode fold
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container, CONTAINERS
from optim_step2_finegrid import make_wf_folds


def killswitch_wf(M: pd.DataFrame, container: str, risk: float,
                  kd_grid: list[float | None], kt_grid: list[float | None],
                  n_folds: int = 5) -> pd.DataFrame:
    """
    For each (kd, kt) pair, compute p_funded per fold + summary.
    Baseline (kd=None, kt=None) is automatically included for L19 ablation.
    """
    folds = make_wf_folds(M, n_folds)
    rows = []
    for kd in kd_grid:
        for kt in kt_grid:
            per_fold_pf = []
            per_fold_bust = []
            per_fold_killed = []
            for fname, fold in folds:
                rp = simulate_real_path_container(
                    fold, container, block_cap_pct=risk,
                    killswitch_daily_pct=kd, killswitch_total_pct=kt
                )
                per_fold_pf.append(rp["p_funded"] * 100)
                per_fold_bust.append(rp["p1_bust_total_pct"])
                per_fold_killed.append(rp["p1_killed_pct"])
            full_rp = simulate_real_path_container(
                M, container, block_cap_pct=risk,
                killswitch_daily_pct=kd, killswitch_total_pct=kt
            )
            rows.append({
                "container": container,
                "risk_pct": risk * 100,
                "killswitch_daily_pct": (kd * 100) if kd is not None else None,
                "killswitch_total_pct": (kt * 100) if kt is not None else None,
                "FULL_p_funded": full_rp["p_funded"] * 100,
                "FULL_p1": full_rp["p_phase1"] * 100,
                "FULL_killed_pct": full_rp["p1_killed_pct"],
                "FULL_bust_total_pct": full_rp["p1_bust_total_pct"],
                "FULL_timeout_pct": full_rp["p1_timeout_pct"],
                "WF_mean_p_funded": np.mean(per_fold_pf),
                "WF_min_p_funded": np.min(per_fold_pf),
                "WF_max_p_funded": np.max(per_fold_pf),
                "WF_std_p_funded": np.std(per_fold_pf),
                "fold1": per_fold_pf[0],
                "fold2": per_fold_pf[1],
                "fold3_chop": per_fold_pf[2],  # 2023-08 to 2024-05 chop window
                "fold4": per_fold_pf[3],
                "fold5": per_fold_pf[4],
            })
    return pd.DataFrame(rows)


def print_summary(df: pd.DataFrame, baseline_row: pd.Series):
    print(f"\nL19 ABLATION TABLE (baseline = no killswitch, same risk)")
    print(f"  Baseline FULL p_funded = {baseline_row['FULL_p_funded']:.1f}%  "
          f"WF mean = {baseline_row['WF_mean_p_funded']:.1f}%  "
          f"WF min = {baseline_row['WF_min_p_funded']:.1f}%  "
          f"fold3_chop = {baseline_row['fold3_chop']:.1f}%")
    print()
    cols = ["killswitch_daily_pct", "killswitch_total_pct",
            "FULL_p_funded", "FULL_killed_pct", "FULL_bust_total_pct", "FULL_timeout_pct",
            "WF_mean_p_funded", "WF_min_p_funded", "WF_max_p_funded",
            "fold3_chop"]
    # Add Delta vs baseline col
    df2 = df.copy()
    df2["Δ_vs_baseline"] = df2["FULL_p_funded"] - baseline_row["FULL_p_funded"]
    df2["Δ_fold3_chop"] = df2["fold3_chop"] - baseline_row["fold3_chop"]
    show_cols = cols + ["Δ_vs_baseline", "Δ_fold3_chop"]
    print(df2[show_cols].round(1).to_string(index=False))


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    kd_grid = [None, 0.02, 0.025, 0.03, 0.04]
    kt_grid = [None, 0.06, 0.07, 0.08]

    for container, risk in [("ftmo_2phase", 0.0125),
                             ("1phase_static", 0.0125)]:
        print("=" * 100)
        print(f"STEP 3 KILLSWITCH SWEEP — container={container}, risk={risk*100}%")
        print("=" * 100)
        df = killswitch_wf(M_full, container, risk, kd_grid, kt_grid, n_folds=5)
        df.to_csv(f"optim_step3_ks_{container}.csv", index=False)
        baseline = df[(df["killswitch_daily_pct"].isna()) & (df["killswitch_total_pct"].isna())].iloc[0]
        print_summary(df, baseline)

    print("\nSaved -> optim_step3_ks_ftmo_2phase.csv, optim_step3_ks_1phase_static.csv")
