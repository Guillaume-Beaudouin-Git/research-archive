"""
f1_check2_slip_points.py — Slippage modeled as FIXED POINTS (not R-fraction).

The original analysis used slip_R = fraction of OR (1R). But real slip ≈ fixed
points (spread + market impact, in index points). If F1 tilts toward narrow ORs,
a fixed-point slip eats a much larger R-fraction.

For each trade, R_with_slip_pts = R_baseline - 2 * slip_pts / or_range_points
  (entry slip + exit slip, both adverse)

Sweep slip_pts ∈ {0, 2, 4, 6, 8, 10, 12} points per side.

For each (slip_pts, sizing), compute:
  - mean R, hit rate baseline vs F1
  - p_funded baseline vs F1 (uncapped FTMO 2-step)
  - per-sleeve breakeven slip_pts (where mean R = 0)

This tests if F1 advantage survives when slip is fixed in points instead of R%.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container


# Per-instrument round-trip cost in index points (already in dataset baseline R)
COST_POINTS = {"US100": 3.0, "GER40": 1.5}


def apply_slip_points(df: pd.DataFrame, slip_pts: float) -> pd.DataFrame:
    """
    Adjust R per trade by subtracting 2 * slip_pts / or_range from R_baseline.

    Note: this assumes slip applies to entry (adverse) and exit (adverse on stop fill or close),
    so total adverse points per trade = 2 * slip_pts (regardless of outcome).
    """
    df = df.copy()
    df["r_with_slip_pts"] = df["r_realised"] - 2.0 * slip_pts / df["or_range"]
    return df


def trades_to_M_matrix(trades_df: pd.DataFrame, value_col: str = "r_realised") -> pd.DataFrame:
    pivot = trades_df.pivot_table(values=value_col, index=trades_df.index,
                                    columns="sleeve", aggfunc="first")
    cols = ["GER40_1000_30m", "US100_1630_30m", "GER40_1630_15m"]
    for c in cols:
        if c not in pivot.columns:
            pivot[c] = np.nan
    return pivot[cols]


def evaluate_at_slip_pts(df: pd.DataFrame, slip_pts: float,
                          M_baseline_calendar: pd.DataFrame) -> dict:
    """Compute mean R + p_funded for baseline and F1 filter at given slip_pts."""
    df_slip = apply_slip_points(df, slip_pts)

    # F1 = time_to_break ≤ median
    threshold = df_slip["time_to_break_5min"].quantile(0.5)
    keep = df_slip["time_to_break_5min"] <= threshold

    # Build matrices using r_with_slip_pts
    M_base = trades_to_M_matrix(df_slip, value_col="r_with_slip_pts").reindex(M_baseline_calendar.index)
    M_filt = trades_to_M_matrix(df_slip[keep], value_col="r_with_slip_pts").reindex(M_baseline_calendar.index)

    out = {"slip_pts": slip_pts,
            "n_baseline": int(df_slip["r_with_slip_pts"].notna().sum()),
            "n_filtered": int(df_slip[keep]["r_with_slip_pts"].notna().sum()),
            "mean_R_baseline": float(df_slip["r_with_slip_pts"].mean()),
            "mean_R_filtered": float(df_slip[keep]["r_with_slip_pts"].mean()),
            "hit_rate_base": float((df_slip["r_with_slip_pts"] > 0).mean() * 100),
            "hit_rate_filt": float((df_slip[keep]["r_with_slip_pts"] > 0).mean() * 100),
            "median_or_range_base": float(df_slip["or_range"].median()),
            "median_or_range_filt": float(df_slip[keep]["or_range"].median()),
           }
    # FTMO p_funded at relevant sizings
    for r in [0.005, 0.0075, 0.010, 0.0125]:
        b = simulate_real_path_container(M_base, "ftmo_2step_uncapped", block_cap_pct=r)
        f = simulate_real_path_container(M_filt, "ftmo_2step_uncapped", block_cap_pct=r)
        out[f"BASE_pfunded_{int(r*10000)}bp"] = b["p_funded"] * 100 if not np.isnan(b["p_funded"]) else float("nan")
        out[f"FILT_pfunded_{int(r*10000)}bp"] = f["p_funded"] * 100 if not np.isnan(f["p_funded"]) else float("nan")
    return out


def per_sleeve_breakeven(df: pd.DataFrame) -> pd.DataFrame:
    """Find slip_pts where mean R = 0 for each sleeve (baseline) and F1."""
    threshold = df["time_to_break_5min"].quantile(0.5)
    keep = df["time_to_break_5min"] <= threshold
    rows = []
    for sleeve in ["US100_1630_30m", "GER40_1630_15m", "GER40_1000_30m"]:
        for label, sub in [("BASELINE", df[df["sleeve"] == sleeve]),
                            ("F1", df[(df["sleeve"] == sleeve) & keep])]:
            if len(sub) < 30:
                continue
            mean_R0 = sub["r_realised"].mean()
            # mean R - 2*slip/or_range. We seek slip* such that mean = 0.
            # E[r - 2s/or] = 0 -> s = E[r] / 2 * E[1/or]^-1. But variance matters.
            # Simpler: solve numerically.
            slips = np.linspace(0, 30, 121)
            means = []
            for s in slips:
                m = (sub["r_realised"] - 2.0 * s / sub["or_range"]).mean()
                means.append(m)
            means = np.array(means)
            # find first slip where mean <= 0
            zero_idx = np.where(means <= 0)[0]
            breakeven = slips[zero_idx[0]] if len(zero_idx) else float("inf")
            rows.append({"sleeve": sleeve, "config": label,
                          "mean_R_no_slip": mean_R0,
                          "median_or_range_pts": sub["or_range"].median(),
                          "breakeven_slip_pts_per_side": breakeven})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_parquet("trade_dataset.parquet")
    M_baseline = build_3sleeve_matrix(lo="2022", hi="2025")
    print(f"Trades: {len(df)} ; M_baseline: {len(M_baseline)} days")
    print()

    # ---- 1. Median OR range by sleeve (sets the scale) ----
    print("=" * 90)
    print("CHECK 2.1 — Median OR range (in index points) per sleeve")
    print("=" * 90)
    for sleeve in df["sleeve"].unique():
        sub = df[df["sleeve"] == sleeve]
        sub_f = sub[sub["time_to_break_5min"] <= df["time_to_break_5min"].quantile(0.5)]
        print(f"  {sleeve:>16}: median or_range BASE={sub['or_range'].median():>7.1f} pts ; "
              f"F1={sub_f['or_range'].median():>7.1f} pts")
    print()

    # ---- 2. Per-trade slip sweep ----
    print("=" * 110)
    print("CHECK 2.2 — Slippage POINTS FIXES sweep (per side, applied to entry + exit adversely)")
    print("=" * 110)
    rows = []
    for slip_pts in [0, 2, 4, 6, 8, 10, 12]:
        out = evaluate_at_slip_pts(df, slip_pts, M_baseline)
        rows.append(out)
    res = pd.DataFrame(rows)
    res.to_csv("f1_check2_slip_points.csv", index=False)
    # Pretty print
    show = res[["slip_pts", "mean_R_baseline", "mean_R_filtered", "hit_rate_base", "hit_rate_filt",
                 "BASE_pfunded_50bp", "FILT_pfunded_50bp",
                 "BASE_pfunded_75bp", "FILT_pfunded_75bp",
                 "BASE_pfunded_100bp", "FILT_pfunded_100bp",
                 "BASE_pfunded_125bp", "FILT_pfunded_125bp"]].copy()
    show.columns = ["slip_pts", "meanR_BASE", "meanR_F1", "hit_BASE", "hit_F1",
                     "B_0.50%", "F_0.50%", "B_0.75%", "F_0.75%",
                     "B_1.00%", "F_1.00%", "B_1.25%", "F_1.25%"]
    print(show.round(2).to_string(index=False))
    print()

    # ---- 3. Per-sleeve breakeven ----
    print("=" * 90)
    print("CHECK 2.3 — Breakeven slip POINTS PER SIDE (where mean R = 0)")
    print("=" * 90)
    be = per_sleeve_breakeven(df)
    print(be.round(2).to_string(index=False))
    be.to_csv("f1_check2_breakeven.csv", index=False)
    print()

    # ---- 4. Verdict ----
    print("=" * 90)
    print("CHECK 2 — VERDICT")
    print("=" * 90)
    # F1 vs baseline at slip 4 pts (realistic) and 8 pts (stressed)
    r4 = res[res["slip_pts"] == 4].iloc[0]
    r8 = res[res["slip_pts"] == 8].iloc[0]
    print(f"\nAt slip 4 pts/side (realistic):")
    print(f"  Baseline mean R = {r4['mean_R_baseline']:+.3f}, F1 = {r4['mean_R_filtered']:+.3f}")
    print(f"  p_funded @ 0.75%: BASE = {r4['BASE_pfunded_75bp']:.1f}%, F1 = {r4['FILT_pfunded_75bp']:.1f}%, "
          f"Δ = {r4['FILT_pfunded_75bp'] - r4['BASE_pfunded_75bp']:+.1f}pt")
    print(f"\nAt slip 8 pts/side (stressed):")
    print(f"  Baseline mean R = {r8['mean_R_baseline']:+.3f}, F1 = {r8['mean_R_filtered']:+.3f}")
    print(f"  p_funded @ 0.75%: BASE = {r8['BASE_pfunded_75bp']:.1f}%, F1 = {r8['FILT_pfunded_75bp']:.1f}%, "
          f"Δ = {r8['FILT_pfunded_75bp'] - r8['BASE_pfunded_75bp']:+.1f}pt")
