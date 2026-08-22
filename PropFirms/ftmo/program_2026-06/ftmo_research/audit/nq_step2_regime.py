"""
nq_step2_regime.py — Decompose baseline p_funded by regime episode on NQ 2010-2026.

For each regime episode, compute:
  - n_trades
  - mean R / hit rate
  - cost-to-R ratio (= cost_pts / median or_range — explains why pre-2017 is hard)
  - p_funded for ANY start within the regime (run sim restricted to regime window)
  - max DD compoundé per regime

Two execution models compared. Two cost scenarios.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from nq_orb_backtest import extract_trades, add_regime_tags, load_nq_5min, COST_POINTS_CFD, COST_POINTS_FUTURES
from nq_sim import simulate_2step_uncapped


REGIMES = [
    ("2010-12_recovery",   "2010-06-07", "2012-12-31"),
    ("2013-14_qe_trend",   "2013-01-01", "2014-12-31"),
    ("2015-16_china_chop", "2015-01-01", "2016-06-30"),
    ("2016H2-17_trend",    "2016-07-01", "2017-12-31"),
    ("2018_vol_shock",     "2018-01-01", "2018-12-31"),
    ("2019_dovish_pivot",  "2019-01-01", "2019-12-31"),
    ("2020_covid",         "2020-01-01", "2020-12-31"),
    ("2021_recovery",      "2021-01-01", "2021-12-31"),
    ("2022_bear",          "2022-01-01", "2022-12-31"),
    ("2023_chop",          "2023-01-01", "2023-12-31"),
    ("2024-26_bull",       "2024-01-01", "2026-05-29"),
]


def regime_analysis(exec_model: str, cost_pts: float, risk: float = 0.0075) -> pd.DataFrame:
    df_trades = extract_trades(or_bars=6, exec_model=exec_model, cost_pts=cost_pts)
    df_5m = load_nq_5min()
    all_dates = pd.DatetimeIndex(sorted(set(pd.Timestamp(d) for d in df_5m.index.date)))
    daily_R = pd.Series(index=all_dates, dtype=float)
    daily_R.loc[df_trades.index] = df_trades["r_realised"].values

    rows = []
    for regime_name, lo, hi in REGIMES:
        # Subset trades and dates
        sub_trades = df_trades.loc[lo:hi]
        sub_dates = all_dates[(all_dates >= pd.Timestamp(lo)) & (all_dates <= pd.Timestamp(hi))]
        sub_daily_R = daily_R.loc[lo:hi]
        if len(sub_trades) < 30:
            continue
        # Compute median OR range (cost-to-R ratio diagnostics)
        median_or_range = sub_trades["or_range"].median()
        cost_to_R = cost_pts / median_or_range
        # Run FTMO sim restricted to this regime window
        sim_out = simulate_2step_uncapped(sub_daily_R, block_cap_pct=risk)
        # Compoundé equity / DD on this period
        pnl = (sub_daily_R.fillna(0.0) * risk)
        eq = (1 + pnl).cumprod()
        max_dd = (eq / eq.cummax() - 1).min() * 100 if len(eq) else float("nan")
        ann_ret = ((eq.iloc[-1]) ** (252 / len(eq)) - 1) * 100 if len(eq) > 30 else float("nan")
        sharpe = pnl.mean() / pnl.std(ddof=1) * np.sqrt(252) if pnl.std(ddof=1) > 0 else float("nan")
        rows.append({
            "regime": regime_name,
            "n_trades": len(sub_trades),
            "n_days": len(sub_dates),
            "mean_R": sub_trades["r_realised"].mean(),
            "hit_rate_pct": (sub_trades["r_realised"] > 0).mean() * 100,
            "median_or_range_pts": median_or_range,
            "cost_to_R_ratio": cost_to_R,
            "p_phase1_pct": sim_out["p_phase1"] * 100 if not np.isnan(sim_out["p_phase1"]) else float("nan"),
            "p_funded_pct": sim_out["p_funded_pct"],
            "censored_pct": sim_out["censored_pct"],
            "median_grind_p1": sim_out["median_grind_p1"],
            "sharpe_ann_daily": sharpe,
            "ann_ret_pct": ann_ret,
            "max_dd_pct": max_dd,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=" * 120)
    print("STEP 2 — NQ ORB baseline decomposition by regime (single sleeve, risk=0.75%)")
    print("=" * 120)
    all_results = []
    for exec_model in ["EXEC_0", "EXEC_NEXT_OPEN"]:
        for cost_pts in [COST_POINTS_CFD, COST_POINTS_FUTURES]:
            cost_label = "CFD_3pts" if cost_pts == COST_POINTS_CFD else "Futures_0.11pts"
            print(f"\n--- {exec_model} | cost={cost_label} ---")
            df = regime_analysis(exec_model, cost_pts, risk=0.0075)
            df["exec_model"] = exec_model
            df["cost_label"] = cost_label
            all_results.append(df)
            cols = ["regime", "n_trades", "mean_R", "hit_rate_pct", "median_or_range_pts",
                     "cost_to_R_ratio", "p_phase1_pct", "p_funded_pct",
                     "censored_pct", "median_grind_p1", "sharpe_ann_daily", "max_dd_pct"]
            print(df[cols].round(3).to_string(index=False))
    full = pd.concat(all_results, ignore_index=True)
    full.to_csv("nq_step2_regime.csv", index=False)
    print("\nSaved -> nq_step2_regime.csv")
