"""
optim_step3b_fine_ks.py — Finer-grain kill-switch test.

The original KD={2..4}% never triggers because per-day intraday loss caps at
~1.5% (AM block max loss). Test KD on a finer grid {0.5, 0.75, 1.0, 1.25%}
where it CAN trigger and skip the PM block.

This is the realistic 'skip PM if AM is bad' lever.

Also re-test KT on a wider range to confirm it stays harmful at higher caps.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from optim_step2_finegrid import make_wf_folds


def fine_ks_sweep(M: pd.DataFrame, container: str, risk: float,
                   kd_grid: list[float | None], kt_grid: list[float | None],
                   n_folds: int = 5) -> pd.DataFrame:
    folds = make_wf_folds(M, n_folds)
    rows = []
    for kd in kd_grid:
        for kt in kt_grid:
            per_fold_pf = []
            for fname, fold in folds:
                rp = simulate_real_path_container(
                    fold, container, block_cap_pct=risk,
                    killswitch_daily_pct=kd, killswitch_total_pct=kt
                )
                per_fold_pf.append(rp["p_funded"] * 100)
            full_rp = simulate_real_path_container(
                M, container, block_cap_pct=risk,
                killswitch_daily_pct=kd, killswitch_total_pct=kt
            )
            rows.append({
                "container": container, "risk_pct": risk * 100,
                "kd_pct": (kd * 100) if kd is not None else None,
                "kt_pct": (kt * 100) if kt is not None else None,
                "FULL_p_funded": full_rp["p_funded"] * 100,
                "FULL_killed_pct": full_rp["p1_killed_pct"],
                "FULL_bust_total_pct": full_rp["p1_bust_total_pct"],
                "FULL_timeout_pct": full_rp["p1_timeout_pct"],
                "WF_mean": np.mean(per_fold_pf),
                "WF_min": np.min(per_fold_pf),
                "fold3_chop": per_fold_pf[2],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    kd_fine = [None, 0.005, 0.0075, 0.010, 0.0125, 0.015]
    kt_fine = [None, 0.05, 0.06, 0.07, 0.08, 0.09]

    for container, risk in [("ftmo_2phase", 0.0125),
                             ("1phase_static", 0.0125)]:
        print("=" * 100)
        print(f"STEP 3b FINER KILL-SWITCH — container={container}, risk={risk*100}%")
        print("=" * 100)
        df = fine_ks_sweep(M_full, container, risk, kd_fine, kt_fine, n_folds=5)
        df.to_csv(f"optim_step3b_fine_{container}.csv", index=False)
        baseline = df[(df["kd_pct"].isna()) & (df["kt_pct"].isna())].iloc[0]
        print(f"Baseline (no killswitch) FULL p_funded = {baseline['FULL_p_funded']:.1f}%, "
              f"WF mean = {baseline['WF_mean']:.1f}%, WF min = {baseline['WF_min']:.1f}%")
        # Pivot for readability
        df_pivot = df.fillna({"kd_pct": -1, "kt_pct": -1})
        piv = df_pivot.pivot(index="kd_pct", columns="kt_pct",
                              values="FULL_p_funded").round(1)
        piv.index = ["NONE" if x == -1 else f"{x}%" for x in piv.index]
        piv.columns = ["NONE" if x == -1 else f"{x}%" for x in piv.columns]
        print("\nFULL_p_funded by (KD, KT):")
        print(piv.to_string())
        # Top improvements
        df["delta"] = df["FULL_p_funded"] - baseline["FULL_p_funded"]
        df["delta_chop"] = df["fold3_chop"] - baseline["fold3_chop"]
        top = df[df["delta"] > 0].sort_values("delta", ascending=False).head(10)
        if len(top):
            print("\nTop improvements vs baseline (positive Δ p_funded):")
            print(top[["kd_pct","kt_pct","FULL_p_funded","WF_mean","fold3_chop","delta","delta_chop"]].round(1).to_string(index=False))
        else:
            print("\n(No (KD, KT) combination beats baseline — kill-switch is a dead lever)")

    print("\nSaved -> optim_step3b_fine_ftmo_2phase.csv, optim_step3b_fine_1phase_static.csv")
