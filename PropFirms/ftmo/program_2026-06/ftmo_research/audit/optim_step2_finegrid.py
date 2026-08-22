"""
optim_step2_finegrid.py — Fine-grid sizing sweep + walk-forward sanity check.

Fine-grid sweep risk-per-block pas 0.25% from 0.5% to 3.0%, on:
  - ftmo_2phase
  - 1phase_static
  - 1phase_trail6
  - 1phase_daily5

WF 5 folds on 2022-2025 (contiguous, ~207 days each).
Reports per-fold p_funded so we can see how stable the sizing optimum is.

Note: this is in-sample re sweep params (we pick argmax across folds), but the
per-fold dispersion tells us whether the optimum is structural or driven by one fold.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import (
    simulate_real_path_container, simulate_iid_container, CONTAINERS
)


def fine_sweep_full(M: pd.DataFrame, containers: list[str],
                    risks: np.ndarray, n_paths_iid: int = 5000) -> pd.DataFrame:
    rows = []
    for c in containers:
        for r in risks:
            rp = simulate_real_path_container(M, c, block_cap_pct=r)
            iid = simulate_iid_container(M, c, block_cap_pct=r, n_paths=n_paths_iid)
            rows.append({
                "container": c,
                "risk_pct": r * 100,
                "REAL_p_funded_pct": rp["p_funded"] * 100,
                "REAL_p1_pct": rp["p_phase1"] * 100,
                "IID_p_funded_pct": iid["p_funded"] * 100,
                "n_real": rp["n_paths"],
            })
    return pd.DataFrame(rows)


def make_wf_folds(M: pd.DataFrame, n_folds: int = 5) -> list[tuple[str, pd.DataFrame]]:
    """Contiguous folds for walk-forward."""
    n = len(M)
    fold_size = n // n_folds
    folds = []
    for k in range(n_folds):
        lo_idx = k * fold_size
        hi_idx = (k + 1) * fold_size if k < n_folds - 1 else n
        fold = M.iloc[lo_idx:hi_idx]
        lo_date, hi_date = fold.index[0].date(), fold.index[-1].date()
        folds.append((f"fold{k+1}_{lo_date}_{hi_date}", fold))
    return folds


def wf_sweep(M: pd.DataFrame, container: str, risks: np.ndarray,
             n_folds: int = 5, n_paths_iid: int = 3000) -> pd.DataFrame:
    folds = make_wf_folds(M, n_folds)
    rows = []
    for fold_name, fold in folds:
        for r in risks:
            rp = simulate_real_path_container(fold, container, block_cap_pct=r)
            rows.append({
                "fold": fold_name,
                "container": container,
                "risk_pct": r * 100,
                "n_real": rp["n_paths"],
                "REAL_p_funded_pct": rp["p_funded"] * 100,
                "REAL_p1_pct": rp["p_phase1"] * 100,
                "REAL_bust_total_pct": rp["p1_bust_total_pct"],
                "REAL_bust_trail_pct": rp["p1_bust_trail_pct"],
                "REAL_bust_daily_pct": rp["p1_bust_daily_pct"],
                "REAL_timeout_pct": rp["p1_timeout_pct"],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    risks_fine = np.arange(0.005, 0.0301, 0.0025)  # 0.5% to 3.0% step 0.25%
    containers = ["ftmo_2phase", "1phase_static", "1phase_trail6", "1phase_daily5"]

    print("=" * 100)
    print("STEP 2 (full sample, in-sample fine grid)")
    print("=" * 100)
    df_full = fine_sweep_full(M_full, containers, risks_fine, n_paths_iid=3000)
    df_full.to_csv("optim_step2_full.csv", index=False)
    for c in containers:
        sub = df_full[df_full["container"] == c]
        best = sub.loc[sub["REAL_p_funded_pct"].idxmax()]
        print(f"\n### {c}")
        print(sub[["risk_pct","REAL_p1_pct","REAL_p_funded_pct","IID_p_funded_pct","n_real"]].round(1).to_string(index=False))
        print(f"  -> argmax REAL p_funded @ risk={best['risk_pct']:.2f}% : {best['REAL_p_funded_pct']:.1f}%")

    print("\n" + "=" * 100)
    print("STEP 2 WALK-FORWARD — 5 contiguous folds, per-fold dispersion")
    print("=" * 100)
    wf_all = []
    for c in containers:
        print(f"\n### {c} WF folds")
        df = wf_sweep(M_full, c, risks_fine, n_folds=5)
        # Pivot: rows=risk, cols=fold, values=p_funded
        piv = df.pivot(index="risk_pct", columns="fold", values="REAL_p_funded_pct").round(1)
        # Add summary cols
        piv["mean"] = piv.mean(axis=1).round(1)
        piv["min"] = piv.iloc[:, :5].min(axis=1).round(1)
        piv["max"] = piv.iloc[:, :5].max(axis=1).round(1)
        piv["std"] = piv.iloc[:, :5].std(axis=1).round(1)
        print(piv.to_string())
        wf_all.append(df)
        # argmax by mean across folds (robust sizing)
        best_mean_risk = piv["mean"].idxmax()
        best_mean_val = piv.loc[best_mean_risk, "mean"]
        best_min_val = piv.loc[best_mean_risk, "min"]
        print(f"  -> argmax mean-WF p_funded @ risk={best_mean_risk:.2f}% : "
              f"mean={best_mean_val:.1f}% (min across folds={best_min_val:.1f}%)")

    wf_df = pd.concat(wf_all)
    wf_df.to_csv("optim_step2_wf.csv", index=False)
    print("\nSaved -> optim_step2_full.csv, optim_step2_wf.csv")
