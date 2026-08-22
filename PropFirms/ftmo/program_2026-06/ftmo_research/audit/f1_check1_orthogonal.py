"""
f1_check1_orthogonal.py — Test whether time_to_break edge is independent of or_range.

If F1 boost is just an or_range denominator artifact (small OR → big R-multiple),
then conditioning on or_range should make ttb edge vanish.

Tests:
  1. Spearman corr(time_to_break_5min, or_range) and (ttb, or_range_atr_ratio)
  2. 3x3 cross-table: rows=or_range tercile, cols=ttb tercile, cells=mean R
  3. OLS regression: R ~ ttb + or_range + interaction, HAC-clustered SE by day
  4. ttb edge inside each or_range tercile separately
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


def cluster_spearman(x, y, days, n_boot=500, seed=7):
    """Spearman rho + day-cluster bootstrap SE."""
    mask = ~np.isnan(x) & ~np.isnan(y)
    rho, p = stats.spearmanr(x[mask], y[mask])
    df = pd.DataFrame({"x": x[mask], "y": y[mask], "d": days[mask]})
    days_u = df["d"].unique()
    rng = np.random.default_rng(seed)
    rhos = []
    for _ in range(n_boot):
        s = rng.choice(days_u, size=len(days_u), replace=True)
        sub = df[df["d"].isin(s)]
        if len(sub) > 30:
            r, _ = stats.spearmanr(sub["x"], sub["y"])
            rhos.append(r)
    se = float(np.std(rhos)) if rhos else float("nan")
    return {"rho": float(rho), "p": float(p), "se_day": se}


def add_z(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df = df.copy()
    df[col + "_z"] = (df[col] - df[col].mean()) / df[col].std(ddof=1)
    return df


def regression_clustered(df: pd.DataFrame, formula_cols: list[str]) -> pd.DataFrame:
    """
    OLS R ~ formula_cols with cluster-by-day SE.
    Returns a DataFrame: feature, coef, se_cluster, t_stat, p_val
    """
    y = df["r_realised"].values
    X = df[formula_cols].values
    X = sm.add_constant(X)
    # Cluster by date
    cluster = pd.to_datetime(df.index).normalize().astype(np.int64).values
    mod = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": cluster})
    rows = [{"feature": "const", "coef": mod.params[0], "se_clu": mod.bse[0],
             "t": mod.tvalues[0], "p": mod.pvalues[0]}]
    for i, name in enumerate(formula_cols):
        rows.append({"feature": name, "coef": mod.params[i+1], "se_clu": mod.bse[i+1],
                     "t": mod.tvalues[i+1], "p": mod.pvalues[i+1]})
    return pd.DataFrame(rows), mod


if __name__ == "__main__":
    df = pd.read_parquet("trade_dataset.parquet")
    days = pd.to_datetime(df.index).normalize()
    print(f"Trades: {len(df)} (2022-2025, 3 sleeves pooled)")
    print()

    # ---- 1. Correlations ----
    print("=" * 90)
    print("CHECK 1.1 — Spearman corr(time_to_break, or_range / or_range_atr_ratio)")
    print("=" * 90)
    for col in ["or_range", "or_range_atr_ratio"]:
        r = cluster_spearman(df["time_to_break_5min"].values, df[col].values,
                              days.values)
        print(f"  Spearman(time_to_break, {col:>22}): rho={r['rho']:+.4f}  "
              f"SE_day={r['se_day']:.4f}  p={r['p']:.4f}")
    print()

    # ---- 2. 3x3 cross-table of mean R ----
    print("=" * 90)
    print("CHECK 1.2 — 3x3 table: mean R by (or_range_atr tercile × ttb tercile)")
    print("=" * 90)
    df2 = df.dropna(subset=["time_to_break_5min", "or_range_atr_ratio"]).copy()
    df2["or_range_tercile"] = pd.qcut(df2["or_range_atr_ratio"], 3,
                                       labels=["narrow", "mid", "wide"])
    # ttb is discrete with many ties at 0
    df2["ttb_tercile"] = pd.qcut(df2["time_to_break_5min"].rank(method="first"), 3,
                                  labels=["fast", "mid", "slow"])

    table_mean = df2.pivot_table(index="or_range_tercile", columns="ttb_tercile",
                                   values="r_realised", aggfunc="mean", observed=True)
    table_n = df2.pivot_table(index="or_range_tercile", columns="ttb_tercile",
                                values="r_realised", aggfunc="count", observed=True)
    print("\nMean R per cell:")
    print(table_mean.round(3).to_string())
    print("\nCount per cell:")
    print(table_n.to_string())
    print()

    # ---- 2b. ttb edge INSIDE each or_range bucket ----
    print("=" * 90)
    print("CHECK 1.2b — TTB edge (fast - slow) INSIDE each or_range tercile")
    print("=" * 90)
    print(f"{'or_range bucket':>16}  {'mean R fast':>11}  {'mean R mid':>10}  "
          f"{'mean R slow':>11}  {'Δ fast-slow':>12}  {'n':>4}")
    for bucket in ["narrow", "mid", "wide"]:
        sub = df2[df2["or_range_tercile"] == bucket]
        mr_fast = sub[sub["ttb_tercile"] == "fast"]["r_realised"].mean()
        mr_mid = sub[sub["ttb_tercile"] == "mid"]["r_realised"].mean()
        mr_slow = sub[sub["ttb_tercile"] == "slow"]["r_realised"].mean()
        delta = mr_fast - mr_slow
        n = len(sub)
        print(f"{bucket:>16}  {mr_fast:>+11.3f}  {mr_mid:>+10.3f}  "
              f"{mr_slow:>+11.3f}  {delta:>+12.3f}  {n:>4}")
    print()

    # ---- 3. Regression R ~ ttb + or_range + interaction (HAC-cluster by day) ----
    print("=" * 90)
    print("CHECK 1.3 — OLS R ~ ttb_z + or_range_z [+ interaction], cluster-by-day SE")
    print("=" * 90)
    df_reg = df.dropna(subset=["time_to_break_5min", "or_range_atr_ratio", "r_realised"]).copy()
    df_reg = add_z(df_reg, "time_to_break_5min")
    df_reg = add_z(df_reg, "or_range_atr_ratio")
    df_reg["interaction_ttb_x_or"] = df_reg["time_to_break_5min_z"] * df_reg["or_range_atr_ratio_z"]

    print("\n--- Model A: R ~ ttb_z (univariate) ---")
    reg_a, _ = regression_clustered(df_reg, ["time_to_break_5min_z"])
    print(reg_a.round(4).to_string(index=False))

    print("\n--- Model B: R ~ or_range_z (univariate) ---")
    reg_b, _ = regression_clustered(df_reg, ["or_range_atr_ratio_z"])
    print(reg_b.round(4).to_string(index=False))

    print("\n--- Model C: R ~ ttb_z + or_range_z (additive) ---")
    reg_c, _ = regression_clustered(df_reg, ["time_to_break_5min_z", "or_range_atr_ratio_z"])
    print(reg_c.round(4).to_string(index=False))

    print("\n--- Model D: R ~ ttb_z + or_range_z + interaction (full) ---")
    reg_d, _ = regression_clustered(df_reg, ["time_to_break_5min_z",
                                              "or_range_atr_ratio_z",
                                              "interaction_ttb_x_or"])
    print(reg_d.round(4).to_string(index=False))

    print()
    print("=" * 90)
    print("CHECK 1 — VERDICT")
    print("=" * 90)
    # ttb coefficient in models A vs C vs D
    coef_a = reg_a[reg_a["feature"] == "time_to_break_5min_z"].iloc[0]
    coef_c = reg_c[reg_c["feature"] == "time_to_break_5min_z"].iloc[0]
    coef_d = reg_d[reg_d["feature"] == "time_to_break_5min_z"].iloc[0]
    print(f"\nttb coefficient evolution:")
    print(f"  Model A (univariate): coef={coef_a['coef']:+.4f}, t={coef_a['t']:+.3f}, p={coef_a['p']:.4f}")
    print(f"  Model C (+or_range):  coef={coef_c['coef']:+.4f}, t={coef_c['t']:+.3f}, p={coef_c['p']:.4f}")
    print(f"  Model D (+interact):  coef={coef_d['coef']:+.4f}, t={coef_d['t']:+.3f}, p={coef_d['p']:.4f}")

    coef_retain = abs(coef_c["coef"]) / abs(coef_a["coef"]) * 100 if coef_a["coef"] != 0 else float("nan")
    print(f"\n  -> ttb effect retention after controlling for or_range: {coef_retain:.1f}%")
    if coef_retain >= 60 and abs(coef_c["t"]) > 2:
        print("  -> ttb is an INDEPENDENT edge ✓")
    elif coef_retain >= 30:
        print("  -> ttb is PARTIALLY independent (some shared variance with or_range)")
    else:
        print("  -> ttb is mostly explained by or_range — likely a DENOMINATOR ARTIFACT ⚠")
