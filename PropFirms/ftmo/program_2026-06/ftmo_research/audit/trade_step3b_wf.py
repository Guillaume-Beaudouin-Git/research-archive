"""
trade_step3b_wf.py — Walk-forward validation of the F1 filter.

Critical: the filter threshold was chosen IN-SAMPLE on the full dataset.
We re-run with WF expanding: use only data BEFORE each fold to compute the
threshold, then apply on that fold.

This is the honest test: does the filter generalize?

Folds: same 5 contiguous folds as optim_step9 (~227 days each).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from trade_features import extract_all_trades


def make_wf_folds(M: pd.DataFrame, n_folds: int = 5):
    n = len(M)
    fs = n // n_folds
    folds = []
    for k in range(n_folds):
        lo = k * fs
        hi = (k + 1) * fs if k < n_folds - 1 else n
        folds.append((f"fold{k+1}_{M.index[lo].date()}_{M.index[hi-1].date()}",
                       M.iloc[lo:hi]))
    return folds


def trades_to_M_matrix(trades_df: pd.DataFrame) -> pd.DataFrame:
    pivot = trades_df.pivot_table(values="r_realised", index=trades_df.index,
                                    columns="sleeve", aggfunc="first")
    cols = ["GER40_1000_30m", "US100_1630_30m", "GER40_1630_15m"]
    for c in cols:
        if c not in pivot.columns:
            pivot[c] = np.nan
    return pivot[cols]


def wf_F1(df_trades: pd.DataFrame, M_baseline: pd.DataFrame,
          quantile: float = 0.5, risks: list[float] = None,
          n_folds: int = 5) -> pd.DataFrame:
    """
    For each fold, compute F1 threshold using ONLY trades from prior folds
    (expanding window). Apply to the current fold's trades.
    Then run FTMO uncapped on that fold.
    """
    if risks is None:
        risks = [0.005, 0.0075, 0.010, 0.0125]
    folds = make_wf_folds(M_baseline, n_folds)
    rows = []
    for k, (fname, fold_M) in enumerate(folds):
        # Trades within this fold's date range
        fold_lo = fold_M.index[0]
        fold_hi = fold_M.index[-1]
        # Pre-fold trades for threshold estimation (expanding from start of data)
        pre_trades = df_trades[df_trades.index < fold_lo]
        fold_trades = df_trades[(df_trades.index >= fold_lo) & (df_trades.index <= fold_hi)]
        if len(pre_trades) < 100:
            # Not enough history — skip this fold
            wf_used_in_sample = True
            threshold = df_trades["time_to_break_5min"].quantile(quantile)
        else:
            wf_used_in_sample = False
            threshold = pre_trades["time_to_break_5min"].quantile(quantile)
        # Apply filter to fold trades
        keep = fold_trades["time_to_break_5min"] <= threshold
        kept = fold_trades[keep]
        # Build M matrix
        M_filtered = trades_to_M_matrix(kept)
        M_filtered = M_filtered.reindex(fold_M.index)

        # Baseline (no filter) for L19 comparison
        M_baseline_fold = fold_M
        for r in risks:
            # No-filter baseline
            out_base = simulate_real_path_container(M_baseline_fold, "ftmo_2step_uncapped",
                                                     block_cap_pct=r)
            out_filt = simulate_real_path_container(M_filtered, "ftmo_2step_uncapped",
                                                     block_cap_pct=r)
            rows.append({
                "fold": fname,
                "risk_pct": r * 100,
                "threshold_bars": threshold,
                "wf_in_sample_fallback": wf_used_in_sample,
                "n_trades_baseline": len(fold_trades),
                "n_trades_filtered": len(kept),
                "retention_pct": (len(kept) / max(1, len(fold_trades))) * 100,
                "p_funded_baseline_pct": out_base["p_funded"] * 100 if not np.isnan(out_base["p_funded"]) else float("nan"),
                "p_funded_filtered_pct": out_filt["p_funded"] * 100 if not np.isnan(out_filt["p_funded"]) else float("nan"),
                "delta_pt": (out_filt["p_funded"] - out_base["p_funded"]) * 100 if (not np.isnan(out_filt["p_funded"]) and not np.isnan(out_base["p_funded"])) else float("nan"),
                "cens_base_pct": out_base["censored_pct"],
                "cens_filt_pct": out_filt["censored_pct"],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df_trades = pd.read_parquet("trade_dataset.parquet")
    M_baseline = build_3sleeve_matrix(lo="2022", hi="2025")
    print(f"Trades: {len(df_trades)}; Baseline M: {len(M_baseline)} days")
    print()
    print("=" * 110)
    print("STEP 3b — WF expanding F1 threshold (time_to_break ≤ q0.5)")
    print("=" * 110)
    wf_df = wf_F1(df_trades, M_baseline, quantile=0.5)
    wf_df.to_csv("trade_step3b_wf.csv", index=False)
    # Pivot for readability
    for r in [0.005, 0.0075, 0.010, 0.0125]:
        sub = wf_df[wf_df["risk_pct"] == r * 100]
        print(f"\n--- Risk per block = {r*100:.2f}% ---")
        for _, row in sub.iterrows():
            print(f"  {row['fold'][:30]:30s} thr={row['threshold_bars']:.1f}bars "
                  f"retention={row['retention_pct']:.0f}%  "
                  f"BASE={row['p_funded_baseline_pct']:5.1f}%  "
                  f"FILT={row['p_funded_filtered_pct']:5.1f}%  "
                  f"Δ={row['delta_pt']:+5.1f}pt"
                  f"{' (IN-SAMPLE FALLBACK)' if row['wf_in_sample_fallback'] else ''}")
        # Summary
        deltas = sub["delta_pt"].dropna().values
        if len(deltas):
            print(f"  WF mean Δ = {deltas.mean():+.1f}pt, min Δ = {deltas.min():+.1f}pt, max Δ = {deltas.max():+.1f}pt")
