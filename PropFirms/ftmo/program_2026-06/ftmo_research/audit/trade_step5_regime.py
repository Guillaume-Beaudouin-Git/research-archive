"""
trade_step5_regime.py — Decompose filter effect by fold (regime).

Does F1 (time_to_break ≤ q0.5) reduce trades specifically during the chop fold
(fold2 = 2022-11 → 2023-10)?  If so, it attacks the slow_bust mechanism directly.

Check:
  - n_trades per fold (filter retention by fold)
  - mean R per fold (does it boost the chop fold?)
  - bust_total reduction in chop fold
  - DD reduction by fold
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from trade_step3b_wf import make_wf_folds, trades_to_M_matrix


def regime_decomp(df_trades: pd.DataFrame, M_baseline: pd.DataFrame,
                   quantile: float = 0.5, n_folds: int = 5) -> pd.DataFrame:
    folds = make_wf_folds(M_baseline, n_folds)
    # Use IN-SAMPLE threshold for this comparison (we test attribution by fold,
    # not threshold robustness — that's step3b)
    threshold = df_trades["time_to_break_5min"].quantile(quantile)
    rows = []
    for k, (fname, fold_M) in enumerate(folds):
        fold_lo = fold_M.index[0]
        fold_hi = fold_M.index[-1]
        fold_trades_baseline = df_trades[(df_trades.index >= fold_lo) & (df_trades.index <= fold_hi)]
        keep = fold_trades_baseline["time_to_break_5min"] <= threshold
        fold_trades_filtered = fold_trades_baseline[keep]

        # Baseline metrics per fold
        base_mean_R = fold_trades_baseline["r_realised"].mean()
        filt_mean_R = fold_trades_filtered["r_realised"].mean() if len(fold_trades_filtered) > 0 else float("nan")

        # Compounded equity (block-cap 0.50%) per fold for DD
        M_filt = trades_to_M_matrix(fold_trades_filtered).reindex(fold_M.index)
        am_cols = ["GER40_1000_30m"]
        pm_cols = ["US100_1630_30m", "GER40_1630_15m"]
        for c in am_cols + pm_cols:
            if c not in fold_M.columns:
                fold_M[c] = np.nan
            if c not in M_filt.columns:
                M_filt[c] = np.nan
        # Baseline DD
        risk_block = 0.005
        am_b = fold_M[am_cols].fillna(0.0).sum(axis=1) * risk_block
        pm_b = (fold_M[pm_cols].fillna(0.0) * (risk_block/2)).sum(axis=1)
        daily_b = (am_b + pm_b).fillna(0.0)
        eq_b = (1 + daily_b).cumprod()
        dd_b = (eq_b / eq_b.cummax() - 1).min() * 100
        # Filtered DD
        am_f = M_filt[am_cols].fillna(0.0).sum(axis=1) * risk_block
        pm_f = (M_filt[pm_cols].fillna(0.0) * (risk_block/2)).sum(axis=1)
        daily_f = (am_f + pm_f).fillna(0.0)
        eq_f = (1 + daily_f).cumprod()
        dd_f = (eq_f / eq_f.cummax() - 1).min() * 100
        # FTMO p_funded comparison (real-path uncapped)
        out_b = simulate_real_path_container(fold_M, "ftmo_2step_uncapped", block_cap_pct=0.005)
        out_f = simulate_real_path_container(M_filt, "ftmo_2step_uncapped", block_cap_pct=0.005)

        rows.append({
            "fold": fname,
            "n_baseline": len(fold_trades_baseline),
            "n_filtered": len(fold_trades_filtered),
            "retention_pct": len(fold_trades_filtered) / max(1, len(fold_trades_baseline)) * 100,
            "mean_R_baseline": base_mean_R,
            "mean_R_filtered": filt_mean_R,
            "delta_mean_R": (filt_mean_R - base_mean_R) if not np.isnan(filt_mean_R) else float("nan"),
            "max_dd_baseline_pct": dd_b,
            "max_dd_filtered_pct": dd_f,
            "p_funded_baseline_pct": out_b["p_funded"] * 100 if not np.isnan(out_b["p_funded"]) else float("nan"),
            "p_funded_filtered_pct": out_f["p_funded"] * 100 if not np.isnan(out_f["p_funded"]) else float("nan"),
            "cens_base_pct": out_b["censored_pct"],
            "cens_filt_pct": out_f["censored_pct"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df_trades = pd.read_parquet("trade_dataset.parquet")
    M_baseline = build_3sleeve_matrix(lo="2022", hi="2025")
    print("=" * 110)
    print("STEP 5 — Decomposition by fold (regime). F1 = time_to_break ≤ in-sample median.")
    print("=" * 110)
    df = regime_decomp(df_trades, M_baseline, quantile=0.5)
    df.to_csv("trade_step5_regime.csv", index=False)
    print(df.round(2).to_string(index=False))
    print()
    # Highlight chop fold
    chop_row = df[df["fold"].str.contains("2022-11|fold2", regex=True)].iloc[0] if any(df["fold"].str.contains("2022-11|fold2", regex=True)) else None
    print()
    print("LEGEND:")
    print("  fold1 = 2022 H1-H2 (Russia war, bear trending)")
    print("  fold2 = late 2022 → 2023 (CHOP fold)")
    print("  fold3 = late 2023 → 2024 (chop tail + trending)")
    print("  fold4 = 2024 (trending)")
    print("  fold5 = 2025 (trending)")
    print()
    print("The chop fold is where slow_bust dominates. If the filter reduces DD here ")
    print("AND lifts p_funded, it's attacking the right mechanism. But beware N≈1: ")
    print("the filter is fitted on 2022-25 which contains this single chop episode.")
