"""
phase2_univariate_scan.py — Re-mining univariate, propre.

For each feature × subset (ALL/LONG/SHORT) × target (r_exec_nextopen),
compute:
  - ρ_Spearman, ρ_Pearson, t_HAC (lag 6, Newey-West)
  - Q1 vs Q5 Δ mean-R
  - Top-decile R capture (in Q5 of feature) — KEY metric per brief
  - Regime decomposition (yearly): mean R + Q5 mean R + Δ + topdec capture
    across 5 year-buckets (2010-12, 2013-15, 2016-18, 2019-21, 2022-26)

Outputs:
  - phase2_univariate_main.csv
  - phase2_univariate_regime.csv
  - phase2_univariate_output.txt

Honest convention: target = r_exec_nextopen (clean exec), bug column excluded.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as scstats

ROOT = Path(__file__).resolve().parent
DS = ROOT / "trade_dataset_clean.parquet"


def hac_t_univariate(x: np.ndarray, y: np.ndarray, lag: int = 6) -> float:
    m = ~(np.isnan(x) | np.isnan(y))
    x = x[m]
    y = y[m]
    n = len(x)
    if n < 30 or x.std() == 0:
        return np.nan
    xz = (x - x.mean()) / x.std()
    X = np.column_stack([np.ones(n), xz])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    S = (X * resid[:, None]).T @ (X * resid[:, None])
    for L in range(1, lag + 1):
        w = 1.0 - L / (lag + 1)
        S_L = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
        S = S + w * (S_L + S_L.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(cov[1, 1])
    return float(beta[1] / se) if se > 0 else np.nan


def univariate(df: pd.DataFrame, feat: str, target: str) -> dict:
    x = df[feat].astype(float).values
    y = df[target].astype(float).values
    m = ~(np.isnan(x) | np.isnan(y))
    x = x[m]
    y = y[m]
    n = len(x)
    if n < 30 or np.std(x) == 0:
        return {"n": n, "rho_s": np.nan, "rho_p": np.nan,
                "hac_t": np.nan, "dQ5_R": np.nan, "dQ1_R": np.nan,
                "topdec_capture_pct": np.nan,
                "Q5_n": 0, "Q1_n": 0,
                "Q5_meanR": np.nan, "Q1_meanR": np.nan,
                "mean_R": float(np.mean(y))}
    rho_s, _ = scstats.spearmanr(x, y)
    rho_p, _ = scstats.pearsonr(x, y)
    q80 = np.quantile(x, 0.80)
    q20 = np.quantile(x, 0.20)
    mean_R = float(np.mean(y))
    Q5_mask = x >= q80
    Q1_mask = x <= q20
    Q5_R = float(y[Q5_mask].mean()) if Q5_mask.any() else np.nan
    Q1_R = float(y[Q1_mask].mean()) if Q1_mask.any() else np.nan
    top_dec_R = np.quantile(y, 0.90)
    top_dec_mask = y >= top_dec_R
    topdec_capture = (top_dec_mask & Q5_mask).sum() / top_dec_mask.sum() * 100 if top_dec_mask.any() else np.nan
    return {
        "n": n,
        "rho_s": round(float(rho_s), 4),
        "rho_p": round(float(rho_p), 4),
        "hac_t": round(float(hac_t_univariate(x, y)), 3),
        "mean_R": round(mean_R, 4),
        "Q5_n": int(Q5_mask.sum()),
        "Q5_meanR": round(Q5_R, 4),
        "dQ5_R": round(Q5_R - mean_R, 4),
        "Q1_n": int(Q1_mask.sum()),
        "Q1_meanR": round(Q1_R, 4),
        "dQ1_R": round(Q1_R - mean_R, 4),
        "topdec_capture_pct": round(float(topdec_capture), 1),
    }


# Features to scan: every feature available in clean dataset.
SCAN_FEATURES = [
    # OR descriptors
    "or_range", "or_range_atr_ratio", "or_vol_5m_std",
    "or_vol_total", "or_vol_ratio_20d", "or_vol_skew", "or_vol_concord",
    "or_touches",
    # Pre-entry
    "time_to_break_5min", "dist_twap_at_break_R", "dist_vwap_at_break_R",
    "vol_pre_break", "pre_break_range_R",
    # Daily prior
    "dist_to_pdh_R", "dist_to_pdl_R", "overnight_range_ratio",
    "prior_day_return", "gap_abs", "gap_pct", "gap_dir",
    "gap_concord", "prior_day_concord",
    # Calendar
    "day_of_week",
]


REGIMES = [
    ("2010-2012", "2010", "2012"),
    ("2013-2015", "2013", "2015"),
    ("2016-2018", "2016", "2018"),
    ("2019-2021", "2019", "2021"),
    ("2022-2026", "2022", "2026"),
]


def scan_all(df: pd.DataFrame, target: str = "r_exec_nextopen") -> pd.DataFrame:
    rows = []
    for subset_name, sub in [("ALL", df),
                              ("LONG", df[df["breakout_dir"] == 1]),
                              ("SHORT", df[df["breakout_dir"] == -1])]:
        for f in SCAN_FEATURES:
            if f not in df.columns:
                continue
            r = univariate(sub, f, target)
            r["subset"] = subset_name
            r["feature"] = f
            r["target"] = target
            rows.append(r)
    cols = ["subset", "feature", "target", "n", "rho_s", "rho_p", "hac_t",
            "mean_R", "Q5_n", "Q5_meanR", "dQ5_R",
            "Q1_n", "Q1_meanR", "dQ1_R", "topdec_capture_pct"]
    return pd.DataFrame(rows)[cols]


def regime_decomp(df: pd.DataFrame, feat: str, target: str = "r_exec_nextopen") -> pd.DataFrame:
    """Top quintile of feature value vs baseline by regime year-bucket."""
    rows = []
    for reg_name, lo, hi in REGIMES:
        sub = df.loc[lo:hi]
        if len(sub) < 50:
            rows.append({"feature": feat, "regime": reg_name, "n": len(sub),
                          "skipped": True})
            continue
        x = sub[feat].astype(float).values
        y = sub[target].astype(float).values
        m = ~(np.isnan(x) | np.isnan(y))
        x = x[m]
        y = y[m]
        if len(x) < 30 or x.std() == 0:
            rows.append({"feature": feat, "regime": reg_name, "n": len(x), "skipped": True})
            continue
        q80 = np.quantile(x, 0.80)
        mean_R = float(np.mean(y))
        Q5_R = float(y[x >= q80].mean()) if (x >= q80).any() else np.nan
        top_dec_R = np.quantile(y, 0.90)
        top_dec_mask = y >= top_dec_R
        Q5_mask = x >= q80
        topdec_capture = (top_dec_mask & Q5_mask).sum() / top_dec_mask.sum() * 100 if top_dec_mask.any() else np.nan
        rho_s, _ = scstats.spearmanr(x, y)
        rows.append({
            "feature": feat,
            "regime": reg_name,
            "n": len(x),
            "rho_s": round(float(rho_s), 4),
            "hac_t": round(hac_t_univariate(x, y), 3),
            "mean_R": round(mean_R, 4),
            "Q5_meanR": round(Q5_R, 4) if not np.isnan(Q5_R) else np.nan,
            "dQ5_R": round(Q5_R - mean_R, 4) if not np.isnan(Q5_R) else np.nan,
            "topdec_capture_pct": round(float(topdec_capture), 1),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(f"Loading clean dataset: {DS}")
    df = pd.read_parquet(DS)
    print(f"  {len(df)} trades, {df.index.min()} -> {df.index.max()}")
    print(f"  target = r_exec_nextopen (clean exec)")
    print()

    print("=" * 110)
    print("UNIVARIATE SCAN — all features × ALL/LONG/SHORT")
    print("=" * 110)
    main = scan_all(df, target="r_exec_nextopen")
    print(main.to_string(index=False))
    main.to_csv(ROOT / "phase2_univariate_main.csv", index=False)
    print()

    print("=" * 110)
    print("RANKING — top features by |hac_t| in each subset")
    print("=" * 110)
    for s in ["ALL", "LONG", "SHORT"]:
        sub = main[main["subset"] == s].copy()
        sub["abs_t"] = sub["hac_t"].abs()
        sub = sub.sort_values("abs_t", ascending=False).head(8)
        print(f"\n  {s}:")
        print(sub[["feature", "n", "rho_s", "hac_t", "mean_R", "dQ5_R", "dQ1_R",
                   "topdec_capture_pct"]].to_string(index=False))

    print()
    print("=" * 110)
    print("REGIME DECOMPOSITION — top 6 candidates (|hac_t| ALL > 1.5)")
    print("=" * 110)
    all_sorted = main[main["subset"] == "ALL"].copy()
    all_sorted["abs_t"] = all_sorted["hac_t"].abs()
    all_sorted = all_sorted.sort_values("abs_t", ascending=False)
    # Exclude or_range (artefact) and time_to_break already audited
    blacklist = ["or_range", "or_range_atr_ratio"]
    candidates = [f for f in all_sorted["feature"].tolist()
                   if f not in blacklist][:8]
    print(f"\n  Candidates: {candidates}")
    print()
    regime_rows = []
    for feat in candidates:
        rd = regime_decomp(df, feat, target="r_exec_nextopen")
        rd["candidate"] = feat
        regime_rows.append(rd)
    if regime_rows:
        regime_all = pd.concat(regime_rows, ignore_index=True)
        # Pivot for display
        cols_show = ["candidate", "regime", "n", "rho_s", "hac_t", "mean_R",
                     "Q5_meanR", "dQ5_R", "topdec_capture_pct"]
        regime_all = regime_all[[c for c in cols_show if c in regime_all.columns]]
        print(regime_all.to_string(index=False))
        regime_all.to_csv(ROOT / "phase2_univariate_regime.csv", index=False)

    print()
    print("=" * 110)
    print("DIAGNOSTIC: which features pass top-decile capture > 25% (vs 20 random)?")
    print("=" * 110)
    main_ok = main[(main["topdec_capture_pct"] > 25)].sort_values(
        "topdec_capture_pct", ascending=False)
    if len(main_ok) == 0:
        print("  None at topdec_capture > 25%.")
    else:
        print(main_ok[["subset", "feature", "n", "topdec_capture_pct",
                       "dQ5_R", "hac_t", "rho_s"]].to_string(index=False))

    print()
    print("=" * 110)
    print("DIAGNOSTIC: which features have BOTH |hac_t| > 1.5 AND dQ5_R > 0 AND topdec >= 20?")
    print("=" * 110)
    consistent = main[(main["hac_t"].abs() > 1.5) &
                       (main["dQ5_R"] > 0) &
                       (main["topdec_capture_pct"] >= 20)].sort_values("hac_t", ascending=False)
    if len(consistent) == 0:
        print("  None pass all three.")
    else:
        print(consistent[["subset", "feature", "n", "hac_t", "rho_s",
                          "dQ5_R", "topdec_capture_pct"]].to_string(index=False))
