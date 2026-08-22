"""
nq_v2_bps_cost.py — v2 analysis: cost in bps-constant + gross meanR + regime tags.

Bug fix from v1: a 3-point FIXED cost across 16 years is wrong because NQ went
from 1800 (2010) to 30000 (2026). A CFD spread is ~constant in BPS of notional,
not in points. So 3 fixed pts = 16.7 bps in 2010 vs 1 bp in 2026.

Fix: cost_pts = bps_RT × price_level / 10000, applied per-trade.

This script:
  1. Loads existing trades parquet (EXEC_0 default = same-bar fill at level,
     which IS the realistic fill for a dormant stop order).
  2. Reconstructs r_gross (= R without any cost).
  3. For each cost model: bps_RT ∈ {1, 2, 3}, futures_fixed_pts ∈ {0.11, 1.0},
     computes a new r_net series, runs FTMO 2-step uncapped, by regime.
  4. Tags regimes trending / chop / vol-shock.
  5. Reports gross meanR per regime separately (the diagnostic).
  6. Re-tests rv20_mid gate under new cost.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from nq_orb_backtest import load_nq_5min, COST_POINTS_CFD
from nq_sim import simulate_2step_uncapped


REGIMES = [
    ("2010-12_recovery",   "2010-06-07", "2012-12-31", "trending"),
    ("2013-14_qe_trend",   "2013-01-01", "2014-12-31", "trending"),
    ("2015-16_china_chop", "2015-01-01", "2016-06-30", "chop"),
    ("2016H2-17_trend",    "2016-07-01", "2017-12-31", "trending"),
    ("2018_vol_shock",     "2018-01-01", "2018-12-31", "vol_shock"),
    ("2019_dovish_pivot",  "2019-01-01", "2019-12-31", "trending"),
    ("2020_covid",         "2020-01-01", "2020-12-31", "vol_shock"),
    ("2021_recovery",      "2021-01-01", "2021-12-31", "trending"),
    ("2022_bear",          "2022-01-01", "2022-12-31", "trending"),
    ("2023_chop",          "2023-01-01", "2023-12-31", "chop"),
    ("2024-26_bull",       "2024-01-01", "2026-05-29", "trending"),
]


def add_gross_R_and_regime(df_trades: pd.DataFrame, cost_used: float = COST_POINTS_CFD) -> pd.DataFrame:
    """Add r_gross (= R without cost), regime, regime_tag, level column."""
    df = df_trades.copy()
    df["r_gross"] = df["r_realised"] + cost_used / df["or_range"]
    df["regime"] = "unknown"
    df["regime_tag"] = "unknown"
    for name, lo, hi, tag in REGIMES:
        mask = (df.index >= pd.Timestamp(lo)) & (df.index <= pd.Timestamp(hi))
        df.loc[mask, "regime"] = name
        df.loc[mask, "regime_tag"] = tag
    return df


def apply_cost_bps(r_gross: pd.Series, level: pd.Series, or_range: pd.Series,
                    bps_RT: float) -> pd.Series:
    """Apply bps-constant cost. cost_pts = bps × price / 10000."""
    cost_pts = bps_RT * level / 10000.0
    r_net = r_gross - cost_pts / or_range
    return r_net


def apply_cost_fixed_pts(r_gross: pd.Series, or_range: pd.Series, cost_pts: float) -> pd.Series:
    """Apply fixed-points cost."""
    r_net = r_gross - cost_pts / or_range
    return r_net


def compute_distortion_table(df_trades: pd.DataFrame, fixed_pts_used: float = 3.0,
                              eras: list[tuple[str, str, str]] | None = None) -> pd.DataFrame:
    """Show what "3 fixed pts" represents in bps per era."""
    if eras is None:
        eras = [("2010", "2010-06-07", "2010-12-31"),
                 ("2012", "2012-01-01", "2012-12-31"),
                 ("2015", "2015-01-01", "2015-12-31"),
                 ("2018", "2018-01-01", "2018-12-31"),
                 ("2020", "2020-01-01", "2020-12-31"),
                 ("2023", "2023-01-01", "2023-12-31"),
                 ("2026", "2026-01-01", "2026-05-29")]
    rows = []
    for era_name, lo, hi in eras:
        sub = df_trades.loc[lo:hi]
        if len(sub) == 0:
            continue
        med_level = sub["level"].median()
        med_or_range = sub["or_range"].median()
        bps_equivalent = fixed_pts_used / med_level * 10000.0
        rows.append({
            "era": era_name,
            "n_trades": len(sub),
            "median_NQ_level": med_level,
            "median_or_range_pts": med_or_range,
            f"{fixed_pts_used}_pts_in_bps": bps_equivalent,
            "cost/R_at_3pts_fixed": fixed_pts_used / med_or_range,
            "cost/R_at_2bps": (2 * med_level / 10000.0) / med_or_range,
        })
    return pd.DataFrame(rows)


def regime_table(df_trades: pd.DataFrame, cost_model: str = "gross",
                  bps_RT: float = 2.0, fixed_pts: float = 3.0) -> pd.DataFrame:
    """For each regime, compute meanR under given cost model."""
    if cost_model == "gross":
        r_col = "r_gross"
    elif cost_model.startswith("bps"):
        df_trades = df_trades.copy()
        df_trades[f"r_net_bps{bps_RT}"] = apply_cost_bps(
            df_trades["r_gross"], df_trades["level"], df_trades["or_range"], bps_RT
        )
        r_col = f"r_net_bps{bps_RT}"
    elif cost_model.startswith("fixed"):
        df_trades = df_trades.copy()
        df_trades[f"r_net_fixed{fixed_pts}"] = apply_cost_fixed_pts(
            df_trades["r_gross"], df_trades["or_range"], fixed_pts
        )
        r_col = f"r_net_fixed{fixed_pts}"
    rows = []
    for regime_name, lo, hi, tag in REGIMES:
        sub = df_trades.loc[lo:hi]
        if len(sub) < 30:
            continue
        rows.append({
            "regime": regime_name, "tag": tag, "n_trades": len(sub),
            "mean_R": sub[r_col].mean(),
            "hit_rate_pct": (sub[r_col] > 0).mean() * 100,
            "median_NQ_level": sub["level"].median(),
            "median_or_range": sub["or_range"].median(),
            "cost/R": sub[r_col].mean() and (df_trades[r_col].mean() - sub["r_gross"].mean()) if False else (
                (sub["r_gross"].mean() - sub[r_col].mean())
            ),
        })
    return pd.DataFrame(rows)


def daily_R_series(df_trades: pd.DataFrame, r_col: str,
                    all_dates: pd.DatetimeIndex) -> pd.Series:
    out = pd.Series(index=all_dates, dtype=float)
    out.loc[df_trades.index] = df_trades[r_col].values
    return out


def simulate_by_regime(df_trades: pd.DataFrame, r_col: str,
                        all_dates: pd.DatetimeIndex,
                        risk: float = 0.0075) -> pd.DataFrame:
    daily_R_full = daily_R_series(df_trades, r_col, all_dates)
    rows = []
    for regime_name, lo, hi, tag in REGIMES:
        sub = daily_R_full.loc[lo:hi]
        if len(sub) < 30:
            continue
        out = simulate_2step_uncapped(sub, block_cap_pct=risk)
        rows.append({
            "regime": regime_name, "tag": tag,
            "n_days": len(sub),
            "p_phase1": (out["p_phase1"] * 100) if not np.isnan(out["p_phase1"]) else float("nan"),
            "p_funded_pct": out["p_funded_pct"],
            "censored_pct": out["censored_pct"],
            "median_grind_p1": out["median_grind_p1"],
        })
    return pd.DataFrame(rows)


def headline_sweep_by_cost(df_trades: pd.DataFrame, all_dates: pd.DatetimeIndex,
                            cost_label: str, r_col: str,
                            risks: list[float]) -> pd.DataFrame:
    daily_R = daily_R_series(df_trades, r_col, all_dates)
    rows = []
    for r in risks:
        out = simulate_2step_uncapped(daily_R, block_cap_pct=r)
        rows.append({
            "cost_model": cost_label,
            "risk_pct": r * 100,
            "n_total": out["n_total"], "n_resolved": out["n_resolved"],
            "censored_pct": out["censored_pct"],
            "p_phase1_pct": out["p_phase1"] * 100 if not np.isnan(out["p_phase1"]) else float("nan"),
            "p_funded_pct": out["p_funded_pct"],
            "median_grind_p1": out["median_grind_p1"],
            "mean_R": df_trades[r_col].mean(),
            "hit_rate_pct": (df_trades[r_col] > 0).mean() * 100,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=" * 90)
    print("V2 — Re-cost in bps + gross meanR + regime tags")
    print("=" * 90)
    # Load existing EXEC_0 trades (same-bar = realistic dormant stop fill)
    df_trades = pd.read_parquet("nq_trades_EXEC_0.parquet")
    df_trades = add_gross_R_and_regime(df_trades, cost_used=COST_POINTS_CFD)
    print(f"Loaded {len(df_trades)} trades EXEC_0")
    print(f"Gross meanR (cost=0): {df_trades['r_gross'].mean():+.4f}")
    print(f"Net @ 3pts fixed: {df_trades['r_realised'].mean():+.4f}")
    print()

    # 1. Distortion table
    print("=" * 90)
    print("1. DISTORTION — what '3 fixed pts' represents in bps per era")
    print("=" * 90)
    dist = compute_distortion_table(df_trades, fixed_pts_used=3.0)
    print(dist.round(3).to_string(index=False))
    dist.to_csv("nq_v2_distortion.csv", index=False)
    print()

    # 2. Gross meanR per regime + tag aggregation
    print("=" * 90)
    print("2. GROSS meanR per regime + grouped by tag (cost = 0)")
    print("=" * 90)
    gross = regime_table(df_trades, cost_model="gross")
    print(gross.round(4).to_string(index=False))
    gross.to_csv("nq_v2_gross_per_regime.csv", index=False)
    print()
    # Group by tag
    print("Aggregated by tag (n-weighted):")
    by_tag = df_trades.groupby("regime_tag").agg(
        n=("r_gross", "count"),
        gross_mean=("r_gross", "mean"),
        gross_median=("r_gross", "median"),
        hit_rate=("r_gross", lambda s: (s > 0).mean() * 100),
        median_or_range=("or_range", "median"),
    )
    print(by_tag.round(4).to_string())
    by_tag.to_csv("nq_v2_gross_by_tag.csv")
    print()

    # 3. Net meanR per regime under different cost models
    print("=" * 90)
    print("3. NET meanR per regime under different cost models")
    print("=" * 90)
    for label, fn in [
        ("3 pts FIXED (buggy v1)", lambda d: apply_cost_fixed_pts(d["r_gross"], d["or_range"], 3.0)),
        ("1 bps RT (aggressive)", lambda d: apply_cost_bps(d["r_gross"], d["level"], d["or_range"], 1.0)),
        ("2 bps RT (median)", lambda d: apply_cost_bps(d["r_gross"], d["level"], d["or_range"], 2.0)),
        ("3 bps RT (conservative)", lambda d: apply_cost_bps(d["r_gross"], d["level"], d["or_range"], 3.0)),
        ("Futures 1 pt (realistic)", lambda d: apply_cost_fixed_pts(d["r_gross"], d["or_range"], 1.0)),
    ]:
        df_trades[f"r_{label}"] = fn(df_trades)
    print()

    summary_rows = []
    for cost_label, col in [
        ("3pts_fixed_v1bug", "r_3 pts FIXED (buggy v1)"),
        ("1bps_aggressive", "r_1 bps RT (aggressive)"),
        ("2bps_median", "r_2 bps RT (median)"),
        ("3bps_conservative", "r_3 bps RT (conservative)"),
        ("futures_1pt_realistic", "r_Futures 1 pt (realistic)"),
    ]:
        # per-regime
        for regime_name, lo, hi, tag in REGIMES:
            sub = df_trades.loc[lo:hi]
            if len(sub) < 30:
                continue
            summary_rows.append({
                "cost_model": cost_label, "regime": regime_name, "tag": tag,
                "n_trades": len(sub),
                "mean_R": sub[col].mean(),
                "hit_rate_pct": (sub[col] > 0).mean() * 100,
                "median_NQ_level": sub["level"].median(),
                "median_or_range": sub["or_range"].median(),
            })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv("nq_v2_meanR_by_cost_regime.csv", index=False)
    # Pivot mean_R: regime × cost
    piv = summary.pivot_table(index=["tag", "regime"], columns="cost_model", values="mean_R")
    cols_order = ["3pts_fixed_v1bug", "1bps_aggressive", "2bps_median",
                   "3bps_conservative", "futures_1pt_realistic"]
    piv = piv[[c for c in cols_order if c in piv.columns]]
    print("Mean R per (tag, regime) × cost model:")
    print(piv.round(4).to_string())
    print()

    # 4. cost-to-R stationarity check under bps cost
    print("=" * 90)
    print("4. cost/R RATIO per regime — stationary under bps?")
    print("=" * 90)
    rows = []
    for regime_name, lo, hi, tag in REGIMES:
        sub = df_trades.loc[lo:hi]
        if len(sub) < 30:
            continue
        # cost/R under various models
        cost_3pts_fixed = 3.0 / sub["or_range"].mean()
        med_level = sub["level"].median()
        med_or = sub["or_range"].median()
        cost_2bps = (2.0 * med_level / 10000.0) / med_or
        cost_3bps = (3.0 * med_level / 10000.0) / med_or
        cost_futures_1pt = 1.0 / med_or
        rows.append({
            "regime": regime_name, "tag": tag,
            "median_NQ_level": med_level,
            "median_or_range": med_or,
            "cost/R (3pts fixed v1)": cost_3pts_fixed,
            "cost/R (2bps)": cost_2bps,
            "cost/R (3bps)": cost_3bps,
            "cost/R (futures 1pt)": cost_futures_1pt,
        })
    cost_to_R = pd.DataFrame(rows)
    print(cost_to_R.round(4).to_string(index=False))
    cost_to_R.to_csv("nq_v2_cost_to_R.csv", index=False)
    print()

    # 5. Save the trades with all new columns
    df_trades.to_parquet("nq_v2_trades.parquet")
    print(f"Saved -> nq_v2_trades.parquet")
