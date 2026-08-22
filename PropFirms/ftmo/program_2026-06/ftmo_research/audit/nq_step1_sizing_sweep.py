"""
nq_step1_sizing_sweep.py — Baseline FTMO 2-step uncapped on NQ 2010-2026.

Sweep:
  - 2 execution models: EXEC_0 (legacy), EXEC_NEXT_OPEN (clean)
  - 4 sizings: 0.50%, 0.75%, 1.00%, 1.25% per trade
  - 2 cost scenarios: CFD (3 pts/RT, default FTMO) and Futures (0.11 pts/RT, sensitivity)

Report p_funded chained P1+P2, censure %, median grind, bust mode by regime.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from nq_orb_backtest import extract_trades, add_regime_tags, load_nq_5min, COST_POINTS_CFD, COST_POINTS_FUTURES
from nq_sim import simulate_2step_uncapped, trades_to_daily_R


def run_sweep(exec_model: str, cost_pts: float, risks: list[float]) -> pd.DataFrame:
    """Extract trades + run FTMO sim for each sizing."""
    df_trades = extract_trades(or_bars=6, exec_model=exec_model, cost_pts=cost_pts)
    df_trades = add_regime_tags(df_trades)
    # Build a complete date index (all RTH days, even those without a trade get NaN)
    df_5m = load_nq_5min()
    all_dates = pd.DatetimeIndex(sorted(set(pd.Timestamp(d) for d in df_5m.index.date)))
    daily_R = pd.Series(index=all_dates, dtype=float)
    daily_R.loc[df_trades.index] = df_trades["r_realised"].values
    rows = []
    for r in risks:
        out = simulate_2step_uncapped(daily_R, block_cap_pct=r)
        out["risk_pct"] = r * 100
        out["exec_model"] = exec_model
        out["cost_pts"] = cost_pts
        out["n_trades"] = len(df_trades)
        out["mean_R"] = df_trades["r_realised"].mean()
        out["hit_rate_pct"] = (df_trades["r_realised"] > 0).mean() * 100
        rows.append(out)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    risks = [0.005, 0.0075, 0.010, 0.0125]
    print("=" * 100)
    print("STEP 1 — NQ 2010-2026 sizing sweep (single sleeve, FTMO 2-step uncapped)")
    print("=" * 100)

    all_results = []
    for exec_model in ["EXEC_0", "EXEC_NEXT_OPEN"]:
        for cost_pts in [COST_POINTS_CFD, COST_POINTS_FUTURES]:
            cost_label = "CFD_3pts" if cost_pts == COST_POINTS_CFD else "Futures_0.11pts"
            print(f"\n--- {exec_model} | cost={cost_label} ---")
            df_res = run_sweep(exec_model, cost_pts, risks)
            df_res["cost_label"] = cost_label
            all_results.append(df_res)
            cols = ["risk_pct", "n_total", "n_resolved", "censored_pct",
                     "p_phase1", "p_phase2_given_p1", "p_funded_pct",
                     "median_grind_p1", "bust_total_pct_resolved",
                     "fail_p2_total_pct_resolved", "mean_R", "hit_rate_pct"]
            show = df_res[cols].copy()
            show["p_phase1"] = (show["p_phase1"] * 100).round(1)
            show["p_phase2_given_p1"] = (show["p_phase2_given_p1"] * 100).round(1)
            print(show.round(2).to_string(index=False))

    all_df = pd.concat(all_results, ignore_index=True)
    all_df.to_csv("nq_step1_sizing_sweep.csv", index=False)
    print("\nSaved -> nq_step1_sizing_sweep.csv")

    # Headline comparison
    print("\n" + "=" * 100)
    print("HEADLINE — p_funded by (exec_model × cost × sizing)")
    print("=" * 100)
    piv = all_df.pivot_table(index=["exec_model", "cost_label"], columns="risk_pct",
                              values="p_funded_pct", aggfunc="first")
    print(piv.round(1).to_string())
