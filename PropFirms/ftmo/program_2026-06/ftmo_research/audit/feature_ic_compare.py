"""
feature_ic_compare.py — IC tables BEFORE (buggy CFD 2022-2025) vs AFTER (clean NQ 2010-2026).

For each feature, compute:
  - Spearman rho (rank IC), Spearman t-stat (= rho * sqrt(N-2) / sqrt(1-rho^2))
  - Pearson rho (linear IC) for cross-check
  - Delta mean-R for top-quintile vs full-sample (Q5 minus baseline)
  - Top-decile R capture: % of top-decile R captured in the top-quintile-of-feature
  - HAC lag-6 t-stat from OLS R = a + b*feature_z (z-scored) + e

Subsets:
  - ALL
  - LONG
  - SHORT

Outputs:
  - feature_ic_before_buggy_cfd.csv
  - feature_ic_after_clean_nq.csv
  - feature_ic_compare_output.txt
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as scstats

ROOT = Path(__file__).resolve().parent
DS_BEFORE = ROOT / "trade_dataset.parquet"            # CFD buggy 2022-2025
DS_AFTER = ROOT / "trade_dataset_nq.parquet"          # NQ clean 2010-2026

# ---------------------------------------------------------------------------
# HAC lag-6 t-stat for univariate regression R = a + b*feature_z + e
# ---------------------------------------------------------------------------

def hac_t_univariate(x: np.ndarray, y: np.ndarray, lag: int = 6) -> tuple[float, float, float]:
    """OLS slope with Newey-West HAC SE for y on z-scored x.

    Returns (beta, se, tstat).
    """
    m = ~(np.isnan(x) | np.isnan(y))
    x = x[m]
    y = y[m]
    n = len(x)
    if n < 30 or x.std() == 0:
        return (np.nan, np.nan, np.nan)
    xz = (x - x.mean()) / x.std()
    X = np.column_stack([np.ones(n), xz])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    # Newey-West HAC
    S = (X * resid[:, None]).T @ (X * resid[:, None])
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1)
        S_L = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
        S = S + w * (S_L + S_L.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(cov[1, 1])
    t = beta[1] / se if se > 0 else np.nan
    return (float(beta[1]), float(se), float(t))


def feature_diagnostics(df: pd.DataFrame, feat: str, target: str = "r_realised") -> dict:
    """Per-feature diagnostics on a subset (df).

    Returns dict with IC + Q5 delta + top-decile capture + HAC-t.
    """
    if feat not in df.columns or target not in df.columns:
        return {"feature": feat, "n": 0}
    x = df[feat].values.astype(float)
    y = df[target].values.astype(float)
    m = ~(np.isnan(x) | np.isnan(y))
    x = x[m]
    y = y[m]
    n = len(x)
    if n < 30 or np.std(x) == 0:
        return {"feature": feat, "n": n, "rho_spearman": np.nan,
                "t_spearman": np.nan, "rho_pearson": np.nan,
                "delta_R_Q5": np.nan, "delta_R_Q1": np.nan,
                "topdec_capture": np.nan, "hac_t": np.nan}
    rho_s, _ = scstats.spearmanr(x, y)
    rho_p, _ = scstats.pearsonr(x, y)
    t_spearman = rho_s * np.sqrt(n - 2) / np.sqrt(max(1e-12, 1 - rho_s**2))
    # Q5 = top 20% of feature value
    q80 = np.quantile(x, 0.80)
    q20 = np.quantile(x, 0.20)
    mean_R = y.mean()
    Q5_mean = y[x >= q80].mean() if (x >= q80).any() else np.nan
    Q1_mean = y[x <= q20].mean() if (x <= q20).any() else np.nan
    delta_R_Q5 = Q5_mean - mean_R if not np.isnan(Q5_mean) else np.nan
    delta_R_Q1 = Q1_mean - mean_R if not np.isnan(Q1_mean) else np.nan
    # Top-decile R capture: of the top-decile-R trades, what fraction lie in Q5 of feature?
    top_dec_R = np.quantile(y, 0.90)
    top_dec_mask = y >= top_dec_R
    Q5_mask = x >= q80
    if top_dec_mask.sum() == 0:
        topdec_capture = np.nan
    else:
        topdec_capture = (top_dec_mask & Q5_mask).sum() / top_dec_mask.sum() * 100  # %
        # baseline expectation if random: 20%
    _, _, hac_t = hac_t_univariate(x, y)
    return {
        "feature": feat,
        "n": n,
        "rho_spearman": round(float(rho_s), 4),
        "t_spearman": round(float(t_spearman), 3),
        "rho_pearson": round(float(rho_p), 4),
        "delta_R_Q5": round(float(delta_R_Q5), 4),
        "delta_R_Q1": round(float(delta_R_Q1), 4),
        "topdec_capture_pct": round(float(topdec_capture), 1),  # vs baseline 20
        "hac_t": round(float(hac_t), 3),
    }


# Features to audit — only those present in BOTH datasets.
COMMON_FEATURES = [
    "or_range", "or_range_atr_ratio", "or_vol_5m_std", "or_touches",
    "time_to_break_5min", "dist_twap_at_break_R", "dist_to_pdh_R",
    "dist_to_pdl_R", "overnight_range_ratio", "prior_day_return",
    "gap_abs", "gap_pct", "gap_dir", "gap_concord", "prior_day_concord",
    "day_of_week",
]
# Features unique to AFTER (volume-based, NQ-only)
NEW_FEATURES_AFTER = [
    "or_vol_total", "or_vol_ratio_20d", "or_vol_skew", "or_vol_concord",
    "dist_vwap_at_break_R", "vol_pre_break", "pre_break_range_R",
    "time_to_break_buggy",   # to show the bug magnitude on clean data
]


def build_ic_table(df: pd.DataFrame, features: list[str], target: str,
                    label: str) -> pd.DataFrame:
    rows = []
    for subset_name, sub in [("ALL", df),
                              ("LONG", df[df["breakout_dir"] == 1]),
                              ("SHORT", df[df["breakout_dir"] == -1])]:
        for f in features:
            d = feature_diagnostics(sub, f, target=target)
            d["subset"] = subset_name
            d["dataset"] = label
            rows.append(d)
    cols = ["dataset", "subset", "feature", "n", "rho_spearman", "t_spearman",
            "rho_pearson", "delta_R_Q5", "delta_R_Q1",
            "topdec_capture_pct", "hac_t"]
    return pd.DataFrame(rows)[cols]


if __name__ == "__main__":
    print(f"Loading BEFORE (buggy CFD): {DS_BEFORE}")
    before = pd.read_parquet(DS_BEFORE)
    print(f"  {len(before)} trades; target = r_realised (cost=CFD 3.0pt, same-bar exec)")
    print()
    print(f"Loading AFTER (clean NQ): {DS_AFTER}")
    after = pd.read_parquet(DS_AFTER)
    print(f"  {len(after)} trades; targets = r_exec_level (legacy same-bar) "
          f"AND r_exec_nextopen (clean)")
    print()

    print("=" * 110)
    print("IC TABLE — BEFORE (buggy CFD 2022-2025)")
    print("=" * 110)
    ic_before = build_ic_table(before, COMMON_FEATURES, "r_realised", "BEFORE_CFD_buggy_samebar")
    print(ic_before.to_string(index=False))
    ic_before.to_csv(ROOT / "feature_ic_before_buggy_cfd.csv", index=False)
    print()

    print("=" * 110)
    print("IC TABLE — AFTER (clean NQ 2010-2026), target = r_exec_nextopen (clean exec)")
    print("=" * 110)
    ic_after_no = build_ic_table(after, COMMON_FEATURES + NEW_FEATURES_AFTER,
                                  "r_exec_nextopen", "AFTER_NQ_clean_nextopen")
    print(ic_after_no.to_string(index=False))
    ic_after_no.to_csv(ROOT / "feature_ic_after_clean_nq_nextopen.csv", index=False)
    print()

    print("=" * 110)
    print("IC TABLE — AFTER (clean NQ 2010-2026), target = r_exec_level (legacy same-bar)")
    print("=" * 110)
    ic_after_lv = build_ic_table(after, COMMON_FEATURES + NEW_FEATURES_AFTER,
                                  "r_exec_level", "AFTER_NQ_clean_samebar")
    print(ic_after_lv.to_string(index=False))
    ic_after_lv.to_csv(ROOT / "feature_ic_after_clean_nq_samebar.csv", index=False)
    print()

    # Side-by-side comparison on COMMON_FEATURES, ALL subset, |t_HAC| ranked
    print("=" * 110)
    print("SIDE-BY-SIDE — ALL subset, common features, ranked by |hac_t| BEFORE")
    print("=" * 110)
    b_all = ic_before[ic_before["subset"] == "ALL"].set_index("feature")
    a_all = ic_after_no[ic_after_no["subset"] == "ALL"].set_index("feature")
    rows = []
    for f in COMMON_FEATURES:
        if f not in b_all.index or f not in a_all.index:
            continue
        rows.append({
            "feature": f,
            "n_before": int(b_all.loc[f, "n"]),
            "rho_before": b_all.loc[f, "rho_spearman"],
            "t_before": b_all.loc[f, "t_spearman"],
            "hac_t_before": b_all.loc[f, "hac_t"],
            "n_after": int(a_all.loc[f, "n"]),
            "rho_after": a_all.loc[f, "rho_spearman"],
            "t_after": a_all.loc[f, "t_spearman"],
            "hac_t_after": a_all.loc[f, "hac_t"],
        })
    cmp_df = pd.DataFrame(rows)
    cmp_df["abs_t_before"] = cmp_df["t_before"].abs()
    cmp_df = cmp_df.sort_values("abs_t_before", ascending=False)
    print(cmp_df.drop(columns="abs_t_before").to_string(index=False))
    cmp_df.to_csv(ROOT / "feature_ic_side_by_side.csv", index=False)
    print()

    print("=" * 110)
    print("SUMMARY — How many features survive |t_HAC| > 2.5 ?")
    print("=" * 110)
    for subset in ["ALL", "LONG", "SHORT"]:
        b = ic_before[(ic_before["subset"] == subset) & ic_before["feature"].isin(COMMON_FEATURES)]
        a = ic_after_no[(ic_after_no["subset"] == subset) & ic_after_no["feature"].isin(COMMON_FEATURES)]
        b_pass = b[b["hac_t"].abs() > 2.5]
        a_pass = a[a["hac_t"].abs() > 2.5]
        print(f"  {subset:6s} : before={len(b_pass):>2d}/{len(b)}  after={len(a_pass):>2d}/{len(a)}")
        if len(b_pass):
            print(f"           BEFORE features w/ |hac_t|>2.5: {b_pass['feature'].tolist()}")
        if len(a_pass):
            print(f"           AFTER  features w/ |hac_t|>2.5: {a_pass['feature'].tolist()}")
    print()

    print("=" * 110)
    print("Bug magnitude: time_to_break_5min vs time_to_break_buggy on NQ")
    print("=" * 110)
    print("Both on the SAME clean NQ dataset and the SAME R target (r_exec_nextopen):")
    for s in ["ALL", "LONG", "SHORT"]:
        sub = ic_after_no[(ic_after_no["subset"] == s) &
                          (ic_after_no["feature"].isin(["time_to_break_5min", "time_to_break_buggy"]))]
        print(f"\n  {s}:")
        print(sub.to_string(index=False))
