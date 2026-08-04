"""Q4c — pair the REALISED J1 leverage with the SAME DAY's true intraday excursion.

Answers: how much of the -5% daily budget does J1 alone consume on an ordinary day,
and how much of that consumption is invisible to the M5-close simulator?
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

SCRATCH = Path("<SCRATCH>"
               "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/j1cache")

d = pd.read_parquet(SCRATCH / "usdjpy_daily_prague.parquet").loc["2013-10-01":]
d = d[d.n_m1 > 200]
true_mae = (d["low"] / d["open"] - 1.0).rename("true")
sim_mae = (d["m5_lo"] / d["open"] - 1.0).rename("sim")

for tag, f in [("pre-v2.8 (margin cap only)", "lev_nocap.parquet"),
               ("v2.8 leg cap 12x", "lev_cap12.parquet")]:
    lv = pd.read_parquet(SCRATCH / f)
    lv["date"] = pd.to_datetime(lv["date"])
    # position posted at 22:05 on `date` is live through the NEXT account day
    nxt = pd.Series(d.index, index=d.index).shift(-1)
    lv["hold_day"] = lv["date"].map(nxt)
    j = lv.dropna(subset=["hold_day"]).join(
        pd.concat([true_mae, sim_mae], axis=1), on="hold_day").dropna()
    j["cons_true"] = (-j.true * j.lev_j1) / 0.05
    j["cons_sim"] = (-j.sim * j.lev_j1) / 0.05
    print(f"\n### {tag} — fraction of the 5% DAILY BUDGET consumed by J1 alone")
    print(f"  N = {len(j):,} account-days")
    qs = [50, 75, 90, 95, 99, 100]
    t = pd.DataFrame({
        "true (M1)": [np.percentile(j.cons_true, q) for q in qs],
        "sim (M5 close)": [np.percentile(j.cons_sim, q) for q in qs]},
        index=[f"p{q}" for q in qs])
    print((t * 100).round(1).to_string() + "   [% of the daily budget]")
    for thr, lab in [(1.0, "FULL budget (-5%) gone on J1 alone"),
                     (0.70, "past the breaker line (30% budget left)")]:
        pt = (j.cons_true >= thr).mean()
        ps = (j.cons_sim >= thr).mean()
        print(f"  p({lab}): TRUE {pt*100:5.2f} %   SIM {ps*100:5.2f} %   "
              f"-> sim understates by {(1-ps/max(pt,1e-9))*100:.0f} %")
    # invisible depth in equity terms
    inv = (j.cons_sim - j.cons_true) * 5.0     # in % of equity
    print(f"  equity invisible to the M5-close sim: mean {inv.mean():.3f} pt, "
          f"p99 {np.percentile(inv, 99):.3f} pt, max {inv.max():.3f} pt of equity")
    worst = j.nlargest(5, "cons_true")[["hold_day", "lev_j1", "true", "sim",
                                        "cons_true", "cons_sim"]]
    worst["true"] *= 100
    worst["sim"] *= 100
    print("  5 worst account-days:")
    print(worst.round(3).to_string(index=False))
