"""
nq_step4_wf_maximin.py — WF maximin on NQ 2010-2026 (true regime diversity).

Use the 11 regime episodes as natural folds. For each (sizing, exec, cost):
  - p_funded per regime
  - mean WF p_funded
  - min WF p_funded (maximin)
  - identify argmax mean and argmax maximin

This is the honest WF on 16 years of NQ, no longer 5 contiguous folds on 4y.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from nq_orb_backtest import extract_trades, load_nq_5min, COST_POINTS_CFD, COST_POINTS_FUTURES
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


def wf_by_regime(exec_model: str, cost_pts: float, risks: list[float]) -> pd.DataFrame:
    df_trades = extract_trades(or_bars=6, exec_model=exec_model, cost_pts=cost_pts)
    df_5m = load_nq_5min()
    all_dates = pd.DatetimeIndex(sorted(set(pd.Timestamp(d) for d in df_5m.index.date)))
    daily_R = pd.Series(index=all_dates, dtype=float)
    daily_R.loc[df_trades.index] = df_trades["r_realised"].values
    rows = []
    for r in risks:
        per_regime = {}
        for regime_name, lo, hi in REGIMES:
            sub = daily_R.loc[lo:hi]
            if len(sub) < 30:
                continue
            out = simulate_2step_uncapped(sub, block_cap_pct=r)
            per_regime[regime_name] = out["p_funded_pct"]
        # Aggregate
        all_p = list(per_regime.values())
        finite = [p for p in all_p if not np.isnan(p)]
        mean_p = np.mean(finite) if finite else float("nan")
        min_p = np.min(finite) if finite else float("nan")
        # Also full-sample for reference
        out_full = simulate_2step_uncapped(daily_R, block_cap_pct=r)
        row = {"risk_pct": r * 100,
                "FULL_p_funded": out_full["p_funded_pct"],
                "FULL_censored_pct": out_full["censored_pct"],
                "WF_mean": mean_p, "WF_min": min_p}
        row.update({f"REG_{k}": v for k, v in per_regime.items()})
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    risks = [0.005, 0.0075, 0.010, 0.0125, 0.015]
    print("=" * 130)
    print("STEP 4 — WF maximin per regime on NQ 2010-2026")
    print("=" * 130)
    for exec_model in ["EXEC_NEXT_OPEN"]:  # focus on the clean one
        for cost_pts in [COST_POINTS_CFD, COST_POINTS_FUTURES]:
            cost_label = "CFD_3pts" if cost_pts == COST_POINTS_CFD else "Futures_0.11pts"
            print(f"\n--- {exec_model} | cost={cost_label} ---")
            df = wf_by_regime(exec_model, cost_pts, risks)
            df.to_csv(f"nq_step4_wf_{exec_model}_{cost_label}.csv", index=False)
            # Print a compact version
            cols_keep = ["risk_pct", "FULL_p_funded", "WF_mean", "WF_min"] + \
                          [c for c in df.columns if c.startswith("REG_")]
            print(df[cols_keep].round(1).to_string(index=False))
            # Identify argmax
            if not df["WF_mean"].isna().all():
                am_mean = df.loc[df["WF_mean"].idxmax()]
                am_min = df.loc[df["WF_min"].idxmax()]
                print(f"  argmax mean WF : risk={am_mean['risk_pct']:.2f}% → {am_mean['WF_mean']:.1f}% (min={am_mean['WF_min']:.1f}%)")
                print(f"  argmax min WF  : risk={am_min['risk_pct']:.2f}% → {am_min['WF_min']:.1f}% (mean={am_min['WF_mean']:.1f}%)")
