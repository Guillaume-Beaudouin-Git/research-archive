"""
trade_step2_conditional.py — Conditional analysis: feature → R (and top-decile capture).

For each feature, compute:
  - Spearman IC with R_realised
  - Mean R per tercile (low / mid / high) of the feature
  - Hit rate per tercile (= % R > 0)
  - Top-decile capture: % of trades in the top-decile-R that fall in each tercile
  - Cluster-by-day SE on the mean (via block bootstrap by trading day)

⚠ A feature that increases hit-rate but decreases mean-R is a tail-killer → REJECT.
We compute both columns explicitly to make this visible.

Output: trade_step2_features.csv ranking features by mean-R signal and tail preservation.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


FEATURES = [
    "or_range_atr_ratio", "or_range", "gap_abs", "gap_pct",
    "dist_twap_at_break_R", "time_to_break_5min", "or_touches",
    "or_vol_5m_std", "dist_to_pdh_R", "dist_to_pdl_R",
    "overnight_range_ratio", "prior_day_return", "gap_concord", "prior_day_concord",
    "day_of_week",
]


def cluster_se_mean(values: np.ndarray, dates: np.ndarray, n_boot: int = 1000,
                    seed: int = 1) -> float:
    """Standard error of the mean using block bootstrap by day."""
    if len(values) == 0:
        return float("nan")
    df = pd.DataFrame({"v": values, "d": dates})
    days = df["d"].unique()
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(n_boot):
        sampled_days = rng.choice(days, size=len(days), replace=True)
        sub = df[df["d"].isin(sampled_days)]
        means.append(sub["v"].mean())
    return float(np.std(means))


def spearman_clustered(x: np.ndarray, y: np.ndarray, dates: np.ndarray) -> dict:
    """Spearman correlation + clustered (by-day) SE on it."""
    mask = ~np.isnan(x) & ~np.isnan(y)
    if mask.sum() < 30:
        return {"rho": float("nan"), "p": float("nan"), "se_day": float("nan")}
    rho, p = stats.spearmanr(x[mask], y[mask])
    # Block-bootstrap day-level SE
    df = pd.DataFrame({"x": x[mask], "y": y[mask], "d": dates[mask]})
    days = df["d"].unique()
    rng = np.random.default_rng(7)
    rhos = []
    for _ in range(500):
        sampled = rng.choice(days, size=len(days), replace=True)
        sub = df[df["d"].isin(sampled)]
        if len(sub) > 30:
            r, _ = stats.spearmanr(sub["x"].values, sub["y"].values)
            rhos.append(r)
    se = float(np.std(rhos)) if rhos else float("nan")
    return {"rho": float(rho), "p": float(p), "se_day": se}


def conditional_table(df: pd.DataFrame, feat: str, target: str = "r_realised") -> pd.DataFrame:
    """Bin by tercile and report mean R, hit rate, count, top-decile capture."""
    sub = df.dropna(subset=[feat, target]).copy()
    if len(sub) < 30:
        return pd.DataFrame()
    # Top-decile R threshold across the WHOLE dataset (not subset)
    top10_thresh = df[target].quantile(0.90)
    # Terciles
    try:
        sub["tercile"] = pd.qcut(sub[feat], 3, labels=["low", "mid", "high"], duplicates="drop")
    except ValueError:
        # Discrete feature with insufficient unique values for terciles
        unique_vals = sub[feat].nunique()
        if unique_vals <= 1:
            return pd.DataFrame()
        if unique_vals == 2:
            # Binary feature -> just split low/high
            sub["tercile"] = sub[feat].map(lambda x: "low" if x == sub[feat].min() else "high")
        else:
            sub["tercile"] = pd.qcut(sub[feat].rank(method="first"), 3,
                                       labels=["low", "mid", "high"])
    if sub["tercile"].nunique() < 2:
        return pd.DataFrame()
    rows = []
    for terc, g in sub.groupby("tercile", observed=True):
        n = len(g)
        if n == 0:
            continue
        mean_R = g[target].mean()
        hit_rate = (g[target] > 0).mean() * 100
        win_avg = g.loc[g[target] > 0, target].mean() if (g[target] > 0).any() else 0
        loss_avg = g.loc[g[target] < 0, target].mean() if (g[target] < 0).any() else 0
        # Top-decile R capture: % of trades in g that are in the top-decile R overall
        top_decile_share = (g[target] >= top10_thresh).mean() * 100
        # Concentration: fraction of the top-decile R trades sample-wide that fall in this bin
        top_decile_concentration = (g[target] >= top10_thresh).sum() / max(
            1, (df[target] >= top10_thresh).sum()
        ) * 100
        se_mean = cluster_se_mean(g[target].values, g.index.values, n_boot=500)
        rows.append({
            "feature": feat,
            "tercile": str(terc),
            "n": n,
            "mean_R": mean_R,
            "se_mean_day": se_mean,
            "hit_rate_pct": hit_rate,
            "avg_win_R": win_avg,
            "avg_loss_R": loss_avg,
            "top10_share_in_bin_pct": top_decile_share,
            "top10_concentration_pct": top_decile_concentration,
        })
    return pd.DataFrame(rows)


def analyze_all(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run conditional + Spearman analysis for all features."""
    ic_rows = []
    cond_rows = []
    for feat in FEATURES:
        if feat not in df.columns:
            continue
        # Spearman
        sp = spearman_clustered(df[feat].values, df["r_realised"].values,
                                 df.index.values)
        ic_rows.append({"feature": feat, **sp,
                         "n_nonnull": int(df[feat].notna().sum())})
        # Conditional
        cond_df = conditional_table(df, feat)
        if not cond_df.empty:
            cond_rows.append(cond_df)
    ic = pd.DataFrame(ic_rows).sort_values("rho", key=lambda s: s.abs(), ascending=False)
    cond = pd.concat(cond_rows, ignore_index=True) if cond_rows else pd.DataFrame()
    return ic, cond


def compute_top_decile_delta(df: pd.DataFrame, feat: str, mask_keep_fn) -> dict:
    """
    Compute Δ mean-R and Δ top-decile-R capture for a filter that KEEPS trades
    matching mask_keep_fn(df).
    """
    keep = mask_keep_fn(df)
    sub = df[keep & df[feat].notna()]
    if len(sub) < 30:
        return {}
    top10_thresh = df["r_realised"].quantile(0.90)
    baseline_top10 = (df["r_realised"] >= top10_thresh).sum()
    filtered_top10 = (sub["r_realised"] >= top10_thresh).sum()
    return {
        "n_baseline": len(df),
        "n_filtered": len(sub),
        "trade_retention_pct": len(sub) / len(df) * 100,
        "mean_R_baseline": df["r_realised"].mean(),
        "mean_R_filtered": sub["r_realised"].mean(),
        "delta_mean_R": sub["r_realised"].mean() - df["r_realised"].mean(),
        "hit_rate_baseline_pct": (df["r_realised"] > 0).mean() * 100,
        "hit_rate_filtered_pct": (sub["r_realised"] > 0).mean() * 100,
        "top_decile_baseline_n": int(baseline_top10),
        "top_decile_filtered_n": int(filtered_top10),
        "top_decile_capture_pct": filtered_top10 / max(1, baseline_top10) * 100,
        "top_decile_delta_in_bin_pct": (sub["r_realised"] >= top10_thresh).mean() * 100
                                       - (df["r_realised"] >= top10_thresh).mean() * 100,
    }


if __name__ == "__main__":
    df = pd.read_parquet("trade_dataset.parquet")
    print(f"Loaded {len(df)} trades 2022-2025")
    print()

    # ---- IC summary ----
    ic, cond = analyze_all(df)
    ic.to_csv("trade_step2_ic.csv", index=False)
    cond.to_csv("trade_step2_conditional.csv", index=False)
    print("=" * 90)
    print("STEP 2 — SPEARMAN IC (day-clustered SE) feature ↔ R_realised")
    print("=" * 90)
    cols = ["feature", "rho", "se_day", "p", "n_nonnull"]
    print(ic[cols].round(4).to_string(index=False))
    print()

    # ---- Conditional table ----
    print("=" * 110)
    print("STEP 2 — CONDITIONAL: tercile bins → mean R, hit rate, top-decile R capture")
    print("=" * 110)
    show_cols = ["feature", "tercile", "n", "mean_R", "se_mean_day",
                 "hit_rate_pct", "avg_win_R", "avg_loss_R",
                 "top10_share_in_bin_pct", "top10_concentration_pct"]
    print(cond[show_cols].round(3).to_string(index=False))
    print()

    # ---- Feature monotonic ranking ----
    print("=" * 90)
    print("STEP 2 — Monotonic ranking (Δ mean-R from low to high tercile)")
    print("=" * 90)
    mono_rows = []
    for feat in cond["feature"].unique():
        sub = cond[cond["feature"] == feat]
        if len(sub) < 3:
            continue
        lo = sub[sub["tercile"] == "low"].iloc[0]
        mid = sub[sub["tercile"] == "mid"].iloc[0]
        hi = sub[sub["tercile"] == "high"].iloc[0]
        mono_rows.append({
            "feature": feat,
            "mean_R_low": lo["mean_R"],
            "mean_R_mid": mid["mean_R"],
            "mean_R_high": hi["mean_R"],
            "delta_high_minus_low": hi["mean_R"] - lo["mean_R"],
            "top10_low": lo["top10_share_in_bin_pct"],
            "top10_high": hi["top10_share_in_bin_pct"],
            "monotone": (lo["mean_R"] < mid["mean_R"] < hi["mean_R"])
                          or (lo["mean_R"] > mid["mean_R"] > hi["mean_R"]),
        })
    mono = pd.DataFrame(mono_rows).sort_values("delta_high_minus_low",
                                                key=lambda s: s.abs(), ascending=False)
    print(mono.round(3).to_string(index=False))
    mono.to_csv("trade_step2_monotonic.csv", index=False)

    # ---- Per-sleeve breakdown for top features ----
    top_feats = mono.head(5)["feature"].tolist()
    print()
    print("=" * 90)
    print("STEP 2 — Per-sleeve breakdown of top-5 features")
    print("=" * 90)
    for feat in top_feats:
        print(f"\n=== {feat} ===")
        for sleeve in df["sleeve"].unique():
            sub = df[df["sleeve"] == sleeve]
            cond_s = conditional_table(sub, feat)
            if cond_s.empty:
                continue
            print(f"  Sleeve {sleeve}:")
            for _, row in cond_s.iterrows():
                print(f"    {row['tercile']:>5}: n={int(row['n']):>4}, mean_R={row['mean_R']:+.3f}, "
                      f"hit={row['hit_rate_pct']:>5.1f}%, top10={row['top10_share_in_bin_pct']:>5.1f}%")
