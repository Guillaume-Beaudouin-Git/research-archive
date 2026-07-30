"""Step 1b — falsification battery on the H1 result. Runs BEFORE any performance claim.

The winter>>summer gap under the legacy UTC spec is CONFOUNDED with calendar month
(US DST ~ Mar-Nov). Three checks that are NOT:
  (i)   hourly drift profile in exchange (ET) clock, winter vs summer -> peak alignment;
  (ii)  DST-transition natural experiment: +/- 4 weeks around the switch, same season,
        clock changes;
  (iii) bar availability per UTC hour x DST -> does the CFD even quote the exchange
        reopen hour in summer? (decisive for SOYBEAN)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import (OUT, REPO, SLEEVES, _nth_weekday, hac_t, load_h1, sharpe, us_dst,
                    window_returns)

pd.set_option("display.width", 240, "display.max_rows", 300)

# ---------------------------------------------------------- (i) ET-clock profile
print("=== (i) mean hourly drift (bps) by EXCHANGE (ET) hour, winter vs summer ===")
for name, sp in SLEEVES.items():
    h1 = load_h1(sp["cfd"])
    h1 = h1[h1.index >= pd.Timestamp(sp["sample_start"])]
    lr = np.log(h1["close"] / h1["close"].shift(1)).dropna()
    d = us_dst(lr.index)
    et = (lr.index.hour - np.where(d, 4, 5)) % 24
    g = (pd.DataFrame({"lr": lr.to_numpy() * 1e4, "et": et, "dst": d})
         .groupby(["et", "dst"])["lr"].agg(["mean", "count"]).unstack())
    g.columns = ["winter_bps", "summer_bps", "n_winter", "n_summer"]
    top = g.sort_values("winter_bps", ascending=False).head(4)
    print(f"\n--- {name} (reopen = 18:00 ET metals/energy, 20:00 ET grains)")
    print(g.round(2).to_string())
    print("  top-4 winter ET hours:", list(top.index))

# --------------------------------------- (ii) DST-transition natural experiment
print("\n\n=== (ii) DST transition natural experiment (+/- 4 weeks, same season) ===")
rows = []
for name, sp in SLEEVES.items():
    h1 = load_h1(sp["cfd"])
    h1 = h1[h1.index >= pd.Timestamp(sp["sample_start"])]
    winA = window_returns(h1, sp["start_utc_winter"], sp["hours"], anchor="utc")
    winB = window_returns(h1, sp["start_utc_winter"], sp["hours"], anchor="exchange")
    years = np.unique(winA.index.year)
    for label, month, nth in (("mar_switch", 3, 2), ("nov_switch", 11, 1)):
        pre, post_A, post_B = [], [], []
        for y in years:
            sw = _nth_weekday(int(y), month, 6, nth)
            lo, hi = sw - pd.Timedelta(weeks=4), sw + pd.Timedelta(weeks=4)
            pre.append(winA[(winA.index >= lo) & (winA.index < sw)])
            post_A.append(winA[(winA.index >= sw) & (winA.index < hi)])
            post_B.append(winB[(winB.index >= sw) & (winB.index < hi)])
        pre = pd.concat(pre); post_A = pd.concat(post_A); post_B = pd.concat(post_B)
        if min(len(pre), len(post_A), len(post_B)) < 40:
            continue
        rows.append(dict(sleeve=name, switch=label,
                         n_pre=len(pre), pre_bps=round(1e4 * pre.mean(), 2),
                         n_post=len(post_A),
                         postA_bps=round(1e4 * post_A.mean(), 2),
                         postB_bps=round(1e4 * post_B.mean(), 2),
                         n_postB=len(post_B)))
tr = pd.DataFrame(rows)
print(tr.to_string(index=False))
print("""
Reading: 'pre' and 'post' are the SAME season (+/-4 weeks around the switch).
 - mar_switch: pre = winter clock (A==B aligned), post = summer (A misaligned, B aligned).
 - nov_switch: pre = summer (A misaligned, B aligned), post = winter (A==B aligned).
If the anchor is the exchange clock: postA << pre in March and postA >> preA in November,
while B stays flat across the switch. If the anchor is UTC: A is flat across the switch.""")
tr.to_csv(OUT / "step1b_dst_transition.csv", index=False)

# ------------------------------------------- (iii) bar availability by UTC hour
print("\n\n=== (iii) CFD bar availability per UTC hour x DST (fraction of days quoted) ===")
avail_rows = []
for name, sp in SLEEVES.items():
    h1 = load_h1(sp["cfd"])
    h1 = h1[h1.index >= pd.Timestamp(sp["sample_start"])]
    d = us_dst(h1.index)
    df = pd.DataFrame({"h": h1.index.hour, "day": h1.index.normalize(), "dst": d})
    for regime, m in (("winter", ~d), ("summer", d)):
        sub = df[m]
        ndays = sub["day"].nunique()
        cnt = sub.groupby("h")["day"].nunique() / max(ndays, 1)
        for h in range(24):
            avail_rows.append(dict(sleeve=name, dst=regime, utc_hour=h,
                                   frac_days_quoted=round(float(cnt.get(h, 0.0)), 3)))
av = pd.DataFrame(avail_rows)
piv = av.pivot_table(index="utc_hour", columns=["sleeve", "dst"], values="frac_days_quoted")
print(piv.to_string())
av.to_csv(OUT / "step1b_bar_availability.csv", index=False)
