"""
cost_breakdown.py — Detailed cost decomposition for VRP Phase 3

Reads phase3_cycles.csv produced by backtest.py.
Decomposes costs by category, regime, and vol level.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PARENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARENT))

CYCLES_PATH = PARENT / "phase3_cycles.csv"


def load_cycles() -> pd.DataFrame:
    if not CYCLES_PATH.exists():
        raise FileNotFoundError(f"Run backtest.py first: {CYCLES_PATH}")
    df = pd.read_csv(CYCLES_PATH, parse_dates=["start_date", "end_date"])
    return df


def print_cost_breakdown(df: pd.DataFrame) -> None:
    sep = "─" * 68

    print(f"\n{'═'*68}")
    print(" VRP PHASE 3 — COST BREAKDOWN ANALYSIS")
    print(f"{'═'*68}")
    print(f"\n  Total cycles analyzed: {len(df)}")

    costs = df["cost_options"] + df["cost_spread"] + df["cost_hedge"]
    gross = df["gross_pnl"]
    net   = df["net_pnl"]

    # ── Per-cycle averages ─────────────────────────────────────────────────
    print(f"\n  {sep}")
    print("  PER-CYCLE AVERAGES  (% of underlying notional)")
    print(f"  {sep}")

    items = [
        ("Gross P&L (B-S approx)",  gross,                None),
        ("  Option fees",           df["cost_options"],   "cost"),
        ("  Bid-ask spread",        df["cost_spread"],    "cost"),
        ("  Delta hedge",           df["cost_hedge"],     "cost"),
        ("Total costs",             costs,                "cost"),
        ("Net P&L",                 net,                  None),
    ]
    for label, series, kind in items:
        pct_char = "−" if kind == "cost" else ("+" if series.mean() > 0 else "−")
        print(f"  {label:<28} {pct_char}{series.mean():.4%}  "
              f"(std {series.std():.4%})")

    # Annualized (using actual cycle frequency)
    days_span = (df["end_date"].max() - df["start_date"].min()).days
    cyc_per_yr = len(df) / (days_span / 365)
    print(f"\n  Cycles/year: {cyc_per_yr:.1f}")
    print(f"\n  Annualized  (% underlying notional):")
    for label, series, kind in items:
        ann = series.mean() * cyc_per_yr
        pct_char = "−" if kind == "cost" else ("+" if ann > 0 else "−")
        print(f"    {label:<26} {pct_char}{ann:.2%}/yr")

    # Cost share breakdown
    total_cost_mean = costs.mean()
    if total_cost_mean > 0:
        opt_share    = df["cost_options"].mean() / total_cost_mean
        spread_share = df["cost_spread"].mean()  / total_cost_mean
        hedge_share  = df["cost_hedge"].mean()   / total_cost_mean
        print(f"\n  Cost share of total:")
        print(f"    Option fees  {opt_share:.0%}")
        print(f"    Spread       {spread_share:.0%}")
        print(f"    Hedge        {hedge_share:.0%}")

    # ── Vol-bucketed cost ──────────────────────────────────────────────────
    print(f"\n  {sep}")
    print("  COST vs DVOL BUCKETS  (spread dominates at low vol)")
    print(f"  {sep}")

    df["vol_bucket"] = pd.cut(
        df["dvol_entry"] * 100,
        bins=[0, 40, 60, 80, 200],
        labels=["<40%", "40-60%", "60-80%", ">80%"],
    )
    df["_total_cost"] = costs
    bucket_stats2 = df.groupby("vol_bucket", observed=True).agg(
        n=("net_pnl", "count"),
        gross_mean=("gross_pnl", "mean"),
        cost_mean=("_total_cost", "mean"),
        net_mean=("net_pnl", "mean"),
    )
    print(f"  {'Vol Bucket':<12}  {'N':>5}  {'Gross':>8}  {'Cost':>8}  {'Net':>8}")
    print(f"  {'-'*12}  {'-'*5}  {'-'*8}  {'-'*8}  {'-'*8}")
    for bucket, row in bucket_stats2.iterrows():
        print(f"  {str(bucket):<12}  {int(row['n']):>5}  "
              f"{row['gross_mean']:>8.4%}  {row['cost_mean']:>8.4%}  {row['net_mean']:>8.4%}")

    # ── Early unwinds ──────────────────────────────────────────────────────
    print(f"\n  {sep}")
    print("  EARLY UNWIND BREAKDOWN  (regime filter triggers)")
    print(f"  {sep}")

    early = df[df["early_unwind"]]
    normal = df[~df["early_unwind"]]
    print(f"  Normal cycles  : {len(normal):>5}  net_mean={normal['net_pnl'].mean():.4%}  "
          f"pct_pos={100*(normal['net_pnl']>0).mean():.0f}%")
    if len(early):
        print(f"  Early unwinds  : {len(early):>5}  net_mean={early['net_pnl'].mean():.4%}  "
              f"pct_pos={100*(early['net_pnl']>0).mean():.0f}%")
        print(f"    Mean DD at unwind : {early['dd30_at_entry'].mean():.1%}")
        print(f"    Mean hold days    : {early['hold_days'].mean():.1f}")

    # ── Cost efficiency ratio ──────────────────────────────────────────────
    print(f"\n  {sep}")
    print("  COST EFFICIENCY")
    print(f"  {sep}")
    gross_ann  = gross.mean() * cyc_per_yr
    cost_ann   = costs.mean() * cyc_per_yr
    net_ann    = net.mean()   * cyc_per_yr
    cost_ratio = cost_ann / gross_ann if gross_ann > 0 else float("inf")
    print(f"  Gross annual P&L  (% notional) : {gross_ann:+.2%}")
    print(f"  Total annual costs             : {cost_ann:+.2%}")
    print(f"  Net annual P&L                 : {net_ann:+.2%}")
    print(f"  Cost / Gross ratio             : {cost_ratio:.1%}")
    if net_ann < 0:
        print(f"\n  ⚠  Costs EXCEED gross P&L — strategy not profitable net-of-costs.")
    else:
        print(f"\n  ✓  Net positive: {net_ann:.2%}/yr (% of underlying notional).")
    print()


def main() -> None:
    df = load_cycles()
    print_cost_breakdown(df)


if __name__ == "__main__":
    main()
