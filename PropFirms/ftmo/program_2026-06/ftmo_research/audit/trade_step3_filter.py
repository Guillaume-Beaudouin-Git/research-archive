"""
trade_step3_filter.py — Entry filter design + L19 ablation.

Top features from Step 2:
  - time_to_break_5min  (ρ = -0.265, monotonic, preserves tail)
  - or_range / or_range_atr_ratio (ρ = -0.26, monotonic, low=big-R)

Filter candidates (≤2 conditions per L10):
  F1: time_to_break_5min <= X         (fast breakout only)
  F2: or_range_atr_ratio <= Y         (small range only)
  F3: F1 AND F2                       (small + fast)
  F4: F1 OR F2                        (looser - retain more trades)

Evaluate on:
  - mean R, std R, Sharpe
  - top-decile capture (preservation of tail)
  - trade count (cost gate L11 reminder)
  - per-sleeve breakdown
  - per-fold (WF) breakdown

Then re-run uncapped FTMO simulation with the filter and report p(funded) at
the relevant sizings (0.50%, 0.75%, 1.0%, 1.25%).
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd

from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from trade_features import extract_all_trades, SLEEVES


# --- Threshold optimisation ---

def sweep_threshold_single(df: pd.DataFrame, feature: str,
                            direction: str = "leq",
                            quantiles: list[float] = None) -> pd.DataFrame:
    """For a single-feature filter, sweep cutoffs and report stats."""
    if quantiles is None:
        quantiles = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    rows = []
    baseline_top10 = (df["r_realised"] >= df["r_realised"].quantile(0.90)).sum()
    for q in quantiles:
        cutoff = df[feature].quantile(q)
        if direction == "leq":
            keep = df[feature] <= cutoff
        else:
            keep = df[feature] >= cutoff
        sub = df[keep]
        if len(sub) < 30:
            continue
        rows.append({
            "feature": feature,
            "direction": direction,
            "quantile": q,
            "cutoff": cutoff,
            "n_keep": len(sub),
            "trade_retention_pct": len(sub) / len(df) * 100,
            "mean_R": sub["r_realised"].mean(),
            "std_R": sub["r_realised"].std(),
            "delta_mean_R": sub["r_realised"].mean() - df["r_realised"].mean(),
            "top_decile_in_bin_pct": (sub["r_realised"] >= df["r_realised"].quantile(0.90)).mean() * 100,
            "top_decile_capture_pct": ((sub["r_realised"] >= df["r_realised"].quantile(0.90)).sum()
                                        / max(1, baseline_top10) * 100),
            "hit_rate_pct": (sub["r_realised"] > 0).mean() * 100,
        })
    return pd.DataFrame(rows)


def sweep_two_feature_AND(df: pd.DataFrame, f1: str, f2: str,
                          q1_list=None, q2_list=None,
                          dir1="leq", dir2="leq") -> pd.DataFrame:
    if q1_list is None:
        q1_list = [0.3, 0.5, 0.7, 0.9]
    if q2_list is None:
        q2_list = [0.3, 0.5, 0.7, 0.9]
    baseline_top10 = (df["r_realised"] >= df["r_realised"].quantile(0.90)).sum()
    rows = []
    for q1 in q1_list:
        c1 = df[f1].quantile(q1)
        for q2 in q2_list:
            c2 = df[f2].quantile(q2)
            keep1 = df[f1] <= c1 if dir1 == "leq" else df[f1] >= c1
            keep2 = df[f2] <= c2 if dir2 == "leq" else df[f2] >= c2
            sub = df[keep1 & keep2]
            if len(sub) < 30:
                continue
            rows.append({
                "f1": f1, "q1": q1, "c1": c1,
                "f2": f2, "q2": q2, "c2": c2,
                "n_keep": len(sub),
                "trade_retention_pct": len(sub) / len(df) * 100,
                "mean_R": sub["r_realised"].mean(),
                "delta_mean_R": sub["r_realised"].mean() - df["r_realised"].mean(),
                "top_decile_capture_pct": (sub["r_realised"] >= df["r_realised"].quantile(0.90)).sum()
                                            / max(1, baseline_top10) * 100,
                "hit_rate_pct": (sub["r_realised"] > 0).mean() * 100,
            })
    return pd.DataFrame(rows)


# --- Convert filtered trades back to a daily R matrix for FTMO simulation ---

def trades_to_M_matrix(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert per-trade DataFrame (with `date` index, `sleeve`, `r_realised`)
    back to the wide format used by ftmo_engine: rows=date, cols=sleeve, vals=R.
    Days where the filter rejects a sleeve become NaN (no trade that day).
    """
    pivot = trades_df.pivot_table(values="r_realised", index=trades_df.index,
                                    columns="sleeve", aggfunc="first")
    # Ensure column order matches engine expectations
    cols = ["GER40_1000_30m", "US100_1630_30m", "GER40_1630_15m"]
    for c in cols:
        if c not in pivot.columns:
            pivot[c] = np.nan
    pivot = pivot[cols]
    return pivot


def apply_filter_to_matrix(trades_df: pd.DataFrame, filter_mask: pd.Series,
                            sleeve_align_with: pd.DataFrame) -> pd.DataFrame:
    """
    Given the trades df and a Boolean mask (True = keep), build a daily matrix
    aligned with the unfiltered baseline matrix's date index.
    """
    kept = trades_df[filter_mask].copy()
    M_filtered = trades_to_M_matrix(kept)
    # Reindex to match baseline calendar
    M_filtered = M_filtered.reindex(sleeve_align_with.index)
    return M_filtered


if __name__ == "__main__":
    print("Loading trade dataset...")
    df = pd.read_parquet("trade_dataset.parquet")
    print(f"  {len(df)} trades 2022-2025")
    print()

    # ---- Single-feature threshold sweeps ----
    print("=" * 90)
    print("F1 — time_to_break_5min ≤ Xth quantile (KEEP fast breakouts)")
    print("=" * 90)
    f1_sweep = sweep_threshold_single(df, "time_to_break_5min", direction="leq",
                                       quantiles=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    print(f1_sweep[["quantile","cutoff","n_keep","trade_retention_pct","mean_R",
                    "delta_mean_R","top_decile_in_bin_pct","top_decile_capture_pct",
                    "hit_rate_pct"]].round(3).to_string(index=False))
    f1_sweep.to_csv("trade_step3_F1.csv", index=False)
    print()

    print("=" * 90)
    print("F2 — or_range_atr_ratio ≤ Xth quantile (KEEP small-range)")
    print("=" * 90)
    f2_sweep = sweep_threshold_single(df, "or_range_atr_ratio", direction="leq",
                                       quantiles=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    print(f2_sweep[["quantile","cutoff","n_keep","trade_retention_pct","mean_R",
                    "delta_mean_R","top_decile_in_bin_pct","top_decile_capture_pct",
                    "hit_rate_pct"]].round(3).to_string(index=False))
    f2_sweep.to_csv("trade_step3_F2.csv", index=False)
    print()

    # ---- Two-feature AND sweep ----
    print("=" * 90)
    print("F3 — time_to_break_5min ≤ qa  AND  or_range_atr_ratio ≤ qb")
    print("=" * 90)
    f3 = sweep_two_feature_AND(df, "time_to_break_5min", "or_range_atr_ratio",
                                q1_list=[0.3, 0.5, 0.7], q2_list=[0.3, 0.5, 0.7])
    print(f3.round(3).to_string(index=False))
    f3.to_csv("trade_step3_F3.csv", index=False)
    print()

    # ---- Pick the best F1 cutoff and the best F3 combo, run on FTMO sim ----
    print("=" * 90)
    print("STEP 3b — FTMO uncapped p(funded) with the FILTER (real-path, contigu)")
    print("=" * 90)

    # Build baseline M (unfiltered) for alignment
    M_baseline = build_3sleeve_matrix(lo="2022", hi="2025")
    print(f"  Baseline M shape = {M_baseline.shape}")

    # Filter configurations to test
    configs = [
        ("BASELINE (no filter)", None),
        ("F1_q0.5 (time_to_break ≤ median)", lambda d: d["time_to_break_5min"] <= d["time_to_break_5min"].quantile(0.5)),
        ("F1_q0.4", lambda d: d["time_to_break_5min"] <= d["time_to_break_5min"].quantile(0.4)),
        ("F1_q0.6", lambda d: d["time_to_break_5min"] <= d["time_to_break_5min"].quantile(0.6)),
        ("F2_q0.5 (or_range_atr ≤ median)", lambda d: d["or_range_atr_ratio"] <= d["or_range_atr_ratio"].quantile(0.5)),
        ("F2_q0.7", lambda d: d["or_range_atr_ratio"] <= d["or_range_atr_ratio"].quantile(0.7)),
        ("F3 AND (ttb ≤0.5 AND or ≤0.5)", lambda d: (d["time_to_break_5min"] <= d["time_to_break_5min"].quantile(0.5))
                                                     & (d["or_range_atr_ratio"] <= d["or_range_atr_ratio"].quantile(0.5))),
        ("F4 OR (ttb ≤0.5 OR or ≤0.5)", lambda d: (d["time_to_break_5min"] <= d["time_to_break_5min"].quantile(0.5))
                                                    | (d["or_range_atr_ratio"] <= d["or_range_atr_ratio"].quantile(0.5))),
    ]
    risks = [0.005, 0.0075, 0.010, 0.0125]
    results = []
    for cfg_name, mask_fn in configs:
        if mask_fn is None:
            M = M_baseline
            mean_R = df["r_realised"].mean()
            n_trades = len(df)
            top10_cap = 100.0  # baseline = full top decile
        else:
            mask = mask_fn(df)
            filtered = df[mask]
            mean_R = filtered["r_realised"].mean()
            n_trades = len(filtered)
            baseline_top10 = (df["r_realised"] >= df["r_realised"].quantile(0.90)).sum()
            top10_cap = (filtered["r_realised"] >= df["r_realised"].quantile(0.90)).sum() / baseline_top10 * 100
            M = apply_filter_to_matrix(df, mask, M_baseline)
            # Replace baseline columns by filtered (NaN where filter rejected)

        # Run uncapped FTMO at each sizing
        for r in risks:
            out = simulate_real_path_container(M, "ftmo_2step_uncapped", block_cap_pct=r)
            results.append({
                "config": cfg_name,
                "risk_pct": r * 100,
                "n_trades": n_trades,
                "mean_R": mean_R,
                "top10_capture_pct": top10_cap,
                "p_funded_pct": out["p_funded"] * 100 if not np.isnan(out["p_funded"]) else float("nan"),
                "p1_pct": out["p_phase1"] * 100 if not np.isnan(out["p_phase1"]) else float("nan"),
                "censored_pct": out["censored_pct"],
                "n_resolved": out["n_resolved"],
                "median_grind": out["median_grind_p1p2"],
            })
    res_df = pd.DataFrame(results)
    res_df.to_csv("trade_step3_pfunded.csv", index=False)
    # Pretty print
    print()
    piv = res_df.pivot(index="config", columns="risk_pct", values="p_funded_pct").round(1)
    # Preserve config order
    piv = piv.loc[[c[0] for c in configs]]
    print(piv.to_string())
    print()
    # Δ vs baseline at same sizing
    base_row = res_df[res_df["config"] == "BASELINE (no filter)"].set_index("risk_pct")
    print("L19 ABLATION — Δ p_funded vs BASELINE at same sizing")
    for cfg in [c[0] for c in configs if c[0] != "BASELINE (no filter)"]:
        for r in risks:
            base = base_row.loc[r * 100, "p_funded_pct"]
            row = res_df[(res_df["config"] == cfg) & (res_df["risk_pct"] == r * 100)].iloc[0]
            delta = row["p_funded_pct"] - base
            print(f"  {cfg:<45} risk={r*100:.2f}% p_funded={row['p_funded_pct']:.1f}% "
                  f"Δ={delta:+.1f}pt (n_trades={int(row['n_trades'])}, top10_cap={row['top10_capture_pct']:.0f}%, "
                  f"cens={row['censored_pct']:.1f}%, med_grind={row['median_grind']})")
