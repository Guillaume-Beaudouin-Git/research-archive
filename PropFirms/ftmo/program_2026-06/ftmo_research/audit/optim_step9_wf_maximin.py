"""
optim_step9_wf_maximin.py — WF maximin sizing for FTMO 2-step uncapped.

5 contiguous folds over 2022-2026. For each (risk, fold):
  - p(funded) on resolved starts within the fold
  - n_resolved, censored_pct per fold

Reports:
  - mean(p_funded) across folds at each risk
  - min(p_funded) across folds at each risk (maximin)
  - argmax mean vs argmax maximin
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container


def make_wf_folds(M: pd.DataFrame, n_folds: int = 5) -> list:
    n = len(M)
    fs = n // n_folds
    folds = []
    for k in range(n_folds):
        lo = k * fs
        hi = (k + 1) * fs if k < n_folds - 1 else n
        folds.append((f"fold{k+1}_{M.index[lo].date()}_{M.index[hi-1].date()}",
                       M.iloc[lo:hi]))
    return folds


def wf_uncapped(M: pd.DataFrame, risks: list[float], n_folds: int = 5) -> pd.DataFrame:
    folds = make_wf_folds(M, n_folds)
    rows = []
    for r in risks:
        # Full sample
        full_out = simulate_real_path_container(M, "ftmo_2step_uncapped", block_cap_pct=r)
        full_pf = full_out["p_funded"] * 100 if not np.isnan(full_out["p_funded"]) else float("nan")
        full_cens = full_out["censored_pct"]
        row = {"risk_pct": r * 100,
                "FULL_p_funded": full_pf, "FULL_censored_pct": full_cens,
                "FULL_n_resolved": full_out["n_resolved"]}
        # Per-fold
        per_fold_pf = []
        per_fold_cens = []
        per_fold_n = []
        for k, (fname, fold) in enumerate(folds):
            out = simulate_real_path_container(fold, "ftmo_2step_uncapped", block_cap_pct=r)
            pf = out["p_funded"] * 100 if not np.isnan(out["p_funded"]) else float("nan")
            per_fold_pf.append(pf)
            per_fold_cens.append(out["censored_pct"])
            per_fold_n.append(out["n_resolved"])
            row[f"fold{k+1}_pf"] = pf
            row[f"fold{k+1}_cens"] = out["censored_pct"]
            row[f"fold{k+1}_nres"] = out["n_resolved"]
        # Summary
        pf_arr = np.array([x for x in per_fold_pf if not np.isnan(x)])
        if len(pf_arr):
            row["WF_mean_pf"] = pf_arr.mean()
            row["WF_min_pf"] = pf_arr.min()
            row["WF_max_pf"] = pf_arr.max()
            row["WF_std_pf"] = pf_arr.std()
        else:
            row["WF_mean_pf"] = float("nan")
            row["WF_min_pf"] = float("nan")
            row["WF_max_pf"] = float("nan")
            row["WF_std_pf"] = float("nan")
        row["WF_mean_cens"] = np.mean(per_fold_cens)
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    M_all = build_3sleeve_matrix(lo="2022", hi="2026")
    print(f"Data: {len(M_all)} days, {len(M_all)//5} per fold")
    risks = [0.0025, 0.005, 0.0075, 0.010, 0.0125, 0.015]
    print("=" * 110)
    print("STEP 9 — WF MAXIMIN — FTMO 2-step uncapped, per-fold p(funded)")
    print("=" * 110)
    df = wf_uncapped(M_all, risks, n_folds=5)
    df.to_csv("optim_step9_wf_uncapped.csv", index=False)
    cols = ["risk_pct", "FULL_p_funded", "FULL_censored_pct",
            "fold1_pf", "fold2_pf", "fold3_pf", "fold4_pf", "fold5_pf",
            "WF_mean_pf", "WF_min_pf", "WF_max_pf", "WF_std_pf", "WF_mean_cens"]
    print(df[cols].round(1).to_string(index=False))

    # Argmax
    print()
    if "WF_mean_pf" in df.columns and not df["WF_mean_pf"].isna().all():
        am_mean = df.loc[df["WF_mean_pf"].idxmax()]
        am_min = df.loc[df["WF_min_pf"].idxmax()]
        print(f"Argmax mean WF p(funded) = {am_mean['WF_mean_pf']:.1f}% @ risk={am_mean['risk_pct']:.2f}% "
              f"(min fold = {am_mean['WF_min_pf']:.1f}%, mean cens = {am_mean['WF_mean_cens']:.1f}%)")
        print(f"Argmax min  WF p(funded) = {am_min['WF_min_pf']:.1f}% @ risk={am_min['risk_pct']:.2f}% "
              f"(mean = {am_min['WF_mean_pf']:.1f}%, mean cens = {am_min['WF_mean_cens']:.1f}%)")
        if am_mean["risk_pct"] == am_min["risk_pct"]:
            print(f"\n  -> Mean-optimal and maximin-optimal AGREE at risk={am_mean['risk_pct']:.2f}%")
        else:
            print(f"\n  -> Mean-optimal ({am_mean['risk_pct']:.2f}%) and maximin-optimal "
                  f"({am_min['risk_pct']:.2f}%) DIVERGE")
            print(f"     - Mean: high E[p_funded] but worse worst-case")
            print(f"     - Maximin: lower E[p_funded] but better worst-case → robust choice")
