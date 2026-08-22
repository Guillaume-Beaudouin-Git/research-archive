"""Merges the 5 axis result files into grille_resultats.csv and computes the
t-distribution summary (mean/median/tail counts) + Monte-Carlo max-order-statistic
comparison for n=115, written to t_distribution.json."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd

FILES = ["axis_A_results.csv", "axis_B_results.csv", "axis_C_results.csv",
        "axis_D_results.csv", "axis_E_results.csv"]

COLS = ["block", "sym", "freq", "entry", "exit", "k", "threshold", "bracket_mult",
       "trail_mult", "provisional", "n_trades", "gross_sr", "gross_t",
       "gross_bps_per_trade", "gross_wf", "gross_dsr", "long_sr", "long_t",
       "short_sr", "short_t", "net_sr", "net_t", "win_rate", "avg_hold_min",
       "avg_bars_held", "avg_wsum", "frac_all_rungs_filled", "frac_sl", "frac_tp",
       "frac_time", "frac_trail"]


def main():
    frames = [pd.read_csv(f) for f in FILES]
    out = pd.concat(frames, ignore_index=True, sort=False)
    out = out[[c for c in COLS if c in out.columns]]
    out.to_csv("grille_resultats.csv", index=False)

    tvec = out["gross_t"].dropna().to_numpy(float)
    n = len(tvec)
    rng = np.random.default_rng(0)
    draws = rng.standard_normal((20000, n))
    max_abs = np.abs(draws).max(axis=1)
    summary = {
        "n_cells": int(n),
        "mean_t": float(tvec.mean()),
        "median_t": float(np.median(tvec)),
        "n_gt_2_5": int((tvec > 2.5).sum()),
        "n_lt_neg_2_5": int((tvec < -2.5).sum()),
        "max_t": float(tvec.max()),
        "min_t": float(tvec.min()),
        "max_abs_t": float(np.abs(tvec).max()),
        "frac_positive": float((tvec > 0).mean()),
        "iid_E_max_abs_t_20000mc": float(max_abs.mean()),
        "iid_P95_max_abs_t_20000mc": float(np.percentile(max_abs, 95)),
        "gross_t": tvec.tolist(),
    }
    with open("t_distribution.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"n={n}  mean={summary['mean_t']:.3f}  median={summary['median_t']:.3f}  "
         f"t>2.5:{summary['n_gt_2_5']}  t<-2.5:{summary['n_lt_neg_2_5']}  "
         f"max|t|={summary['max_abs_t']:.3f}  iid E[max|t|]={summary['iid_E_max_abs_t_20000mc']:.3f}  "
         f"iid P95={summary['iid_P95_max_abs_t_20000mc']:.3f}")

    print("\nPer-block means:")
    print(out.groupby("block")["gross_t"].agg(["mean", "count",
                                              lambda s: (s > 2.5).sum(),
                                              lambda s: (s < -2.5).sum()]))


if __name__ == "__main__":
    main()
