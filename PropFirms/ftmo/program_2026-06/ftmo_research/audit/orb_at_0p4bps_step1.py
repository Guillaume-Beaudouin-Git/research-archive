"""ORB V2+E7 @ 0.4 bps — Step 1: mean_R + monotonicity + by-year regime.

Inputs: data/ftmo_research/audit/nq_v2_trades.parquet (4013 trades, V2 baseline).
Approach: linearly interpolate per-trade cost from r_1bps and r_2bps columns to obtain r_0.4bps.
Then add E7 lift (+0.015 R/trade canonical, doc4) to get V2+E7 @ 0.4 bps.

We DO NOT touch the signal. We DO NOT re-fit. We just re-cost.
"""
import numpy as np
import pandas as pd

LEDGER = "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/nq_v2_trades.parquet"
E7_LIFT_R = 0.015   # doc4 canonical (ORB_reconciliation_2026-06.md l.224)
COST_BPS = 0.4

df = pd.read_parquet(LEDGER).reset_index()
print(f"Ledger: {df.shape}  cols={df.columns.tolist()}")
print(f"\nKey columns: r_gross / r_1bps / r_2bps / r_3bps")

# Sanity: monotonicity per-trade
r_g  = df["r_gross"].astype(float)
r_1  = df["r_1 bps RT (aggressive)"].astype(float)
r_2  = df["r_2 bps RT (median)"].astype(float)
r_3  = df["r_3 bps RT (conservative)"].astype(float)

print(f"\nMean R aggregate (V2 BASELINE, no E7):")
print(f"  @ 0 bps (gross) : {r_g.mean():+.4f}")
print(f"  @ 1 bps         : {r_1.mean():+.4f}")
print(f"  @ 2 bps         : {r_2.mean():+.4f}")
print(f"  @ 3 bps         : {r_3.mean():+.4f}")
print(f"  Reference doc4: baseline 1/2/3 bps = +0.027 / +0.004 / −0.018")
print(f"  Monotonicity check: 0 > 1 > 2 > 3 ?  "
      f"{r_g.mean() > r_1.mean() > r_2.mean() > r_3.mean()}")

# Per-trade cost slope (R per bps) = r_1 - r_2 = cost at 1 bps (since r_c = r_g - c × cost_unit)
per_trade_cost_unit = r_1 - r_2   # = cost_unit_R per 1 bps
print(f"\nPer-trade cost_unit (R per 1 bps): mean={per_trade_cost_unit.mean():.5f}  "
      f"std={per_trade_cost_unit.std():.5f}  min={per_trade_cost_unit.min():.5f}  max={per_trade_cost_unit.max():.5f}")
# Cross-check: r_2 - r_3 should equal cost_unit too
diff_23 = r_2 - r_3
print(f"  r_2 - r_3 (should = cost_unit): mean={diff_23.mean():.5f}  std={diff_23.std():.5f}")

# Interpolate per-trade @ 0.4 bps
# r_c = r_g - c × cost_unit  →  r_0.4 = r_g - 0.4 × cost_unit = r_2 + (2 - 0.4) × cost_unit = r_2 + 1.6 × cost_unit
r_0p4_baseline = r_2 + 1.6 * per_trade_cost_unit
r_0p4_v2e7 = r_0p4_baseline + E7_LIFT_R

print("\n" + "=" * 78)
print(f"V2 BASELINE @ {COST_BPS} bps RT")
print("=" * 78)
print(f"  mean_R       = {r_0p4_baseline.mean():+.4f}")
print(f"  median_R     = {r_0p4_baseline.median():+.4f}")
print(f"  std          = {r_0p4_baseline.std():.4f}")
print(f"  hit_rate     = {(r_0p4_baseline > 0).mean():.2%}")
print(f"  max_win      = {r_0p4_baseline.max():+.4f}")
print(f"  max_loss     = {r_0p4_baseline.min():+.4f}")
print(f"  Monotone ?  @0.4 > @1 > @2 > @3 : "
      f"{r_0p4_baseline.mean() > r_1.mean() > r_2.mean() > r_3.mean()}")

print("\n" + "=" * 78)
print(f"V2+E7 (with +0.015 R lift) @ {COST_BPS} bps RT  ← CANONICAL SPEC")
print("=" * 78)
print(f"  mean_R       = {r_0p4_v2e7.mean():+.4f}")
print(f"  median_R     = {r_0p4_v2e7.median():+.4f}")
print(f"  hit_rate     = {(r_0p4_v2e7 > 0).mean():.2%}")
print()
print(f"  Reference points (V2+E7):")
print(f"    @ 0.4 bps : {r_0p4_v2e7.mean():+.4f}  (this re-cost)")
print(f"    @ 2 bps   : {(r_2 + E7_LIFT_R).mean():+.4f}  (doc4: +0.020)")
print(f"    @ 3 bps   : {(r_3 + E7_LIFT_R).mean():+.4f}  (doc4: -0.003)")
print(f"  Monotonicity holds ?  "
      f"@0.4 > @2 > @3 : {r_0p4_v2e7.mean() > (r_2 + E7_LIFT_R).mean() > (r_3 + E7_LIFT_R).mean()}")

# ===== Year-by-year =====
print("\n" + "=" * 78)
print(f"YEAR-BY-YEAR mean_R @ {COST_BPS} bps RT (V2+E7) — régime fragility test")
print("=" * 78)
df["r_0p4_v2e7"] = r_0p4_v2e7
df["year"] = pd.to_datetime(df["date"]).dt.year
by_year = df.groupby("year").agg(
    n_trades=("r_0p4_v2e7", "size"),
    mean_R=("r_0p4_v2e7", "mean"),
    median_R=("r_0p4_v2e7", "median"),
    hit_rate=("r_0p4_v2e7", lambda x: (x > 0).mean()),
).round({"mean_R": 4, "median_R": 4, "hit_rate": 3})
print(by_year.to_string())
neg_years = (by_year.mean_R < 0).sum()
print(f"\n  Years negative: {neg_years}/{len(by_year)}")
print(f"  Years positive: {(by_year.mean_R > 0).sum()}/{len(by_year)}")
print(f"  Worst year mean_R: {by_year.mean_R.min():+.4f}  ({by_year.mean_R.idxmin()})")
print(f"  Best  year mean_R: {by_year.mean_R.max():+.4f}  ({by_year.mean_R.idxmax()})")

# ===== Regime tag =====
print("\n" + "=" * 78)
print(f"REGIME-TAG mean_R @ {COST_BPS} bps RT (V2+E7)")
print("=" * 78)
by_tag = df.groupby("regime_tag").agg(
    n=("r_0p4_v2e7", "size"),
    mean_R=("r_0p4_v2e7", "mean"),
    hit=("r_0p4_v2e7", lambda x: (x > 0).mean()),
).round({"mean_R": 4, "hit": 3})
print(by_tag.to_string())

# Save daily series for MC step 2
df_dates = pd.DataFrame({
    "date": pd.to_datetime(df["date"]),
    "r_v2e7_0p4": r_0p4_v2e7.values,
    "r_baseline_0p4": r_0p4_baseline.values,
})
df_dates.to_parquet("<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_v2e7_0p4bps_per_trade.parquet")
print(f"\nSaved per-trade series → orb_v2e7_0p4bps_per_trade.parquet")

# Summary table for deliverable
grid = pd.DataFrame({
    "cost_bps": [0.0, 0.4, 1.0, 2.0, 3.0, 4.0],
    "V2_baseline_meanR": [
        r_g.mean(),
        r_0p4_baseline.mean(),
        r_1.mean(),
        r_2.mean(),
        r_3.mean(),
        r_2.mean() - 2 * per_trade_cost_unit.mean(),
    ],
})
grid["V2_E7_meanR"] = grid["V2_baseline_meanR"] + E7_LIFT_R
grid = grid.round({"V2_baseline_meanR": 4, "V2_E7_meanR": 4})
print("\n" + "=" * 78)
print("COST GRID (V2 baseline + V2+E7)")
print("=" * 78)
print(grid.to_string(index=False))
grid.to_csv("<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_v2e7_cost_grid_0p4.csv", index=False)
