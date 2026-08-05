"""Does the weekday you START phase 2 on matter?

It has to: the MONO sleeve only takes risk on Mon and Tue nights, so a Wednesday
start burns three sessions before the first risk event. And the main grid steps
cohorts by 7 TRADING days, which pins every cohort to (nearly) the same weekday —
so this also checks that the headline table is not an artefact of one weekday.
"""
import numpy as np
import pandas as pd

import p2_lib as L

E = L.E
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri"]

M = L.market()
WT, ON = L.book_mono(M)
L.set_pace(91, on=True)
dates = pd.DatetimeIndex(M["dates_idx"])

base = L.cohort_starts(M, runway_td=60, step=7)
print("weekday mix of the MAIN grid's cohorts:")
print(pd.Series(dates[base].dayofweek).value_counts().rename(
    index=dict(enumerate(DOW))).to_string())

rows = []
for off in range(5):                       # 5 interleaved cohort sets -> all weekdays
    st = [i for i in range(off, M["n"] - 60, 7)]
    for vm in (8, 14):
        r = L.resolve(M, WT, ON, st, vm_spec=float(vm))
        d = dates[st].dayofweek
        for wd in range(5):
            m = np.asarray(d == wd)
            if m.sum() < 30:
                continue
            sub = r.loc[m].reset_index(drop=True)
            for H in (7, 14, 21, 35, 70):
                s = L.horizon_stats(sub, H)
                rows.append(dict(offset=off, vm_spec=vm, dow=DOW[wd], n=int(m.sum()),
                                 weeks=H // 7, p_pass=s["p_pass"],
                                 med_cal=s["med_cal"], p_floor=s["p_floor"],
                                 p_nr=s["p_not_reached"]))
w = pd.DataFrame(rows)
agg = (w.groupby(["vm_spec", "dow", "weeks"])
        .apply(lambda x: pd.Series(dict(n=x.n.sum(),
                                        p_pass=np.average(x.p_pass, weights=x.n),
                                        med_cal=np.average(x.med_cal.fillna(0), weights=x.n))),
               include_groups=False)
        .reset_index())
agg.to_csv(L.TAB / "start_weekday.csv", index=False)
for vm in (8, 14):
    print(f"\n=== p(pass) by START weekday, vm {vm} ===")
    print((agg[agg.vm_spec == vm].pivot(index="dow", columns="weeks", values="p_pass")
           .reindex(DOW) * 100).round(1).to_string())
print(f"\ncohorts per weekday cell: {int(agg.n.iloc[0])}")
