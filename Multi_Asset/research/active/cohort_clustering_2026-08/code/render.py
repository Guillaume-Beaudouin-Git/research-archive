"""Markdown fragments for RESULTS.md, straight from the CSVs. No new computation."""
import sys

import numpy as np
import pandas as pd

import cc_lib as C

VM = sys.argv[1] if len(sys.argv) > 1 else "10"
H = int(sys.argv[2]) if len(sys.argv) > 2 else 56
tag = f"vm{VM}"

tl = pd.read_csv(C.TAB / f"cohort_timeline_{tag}.csv", parse_dates=["start_date"])
sd = pd.DatetimeIndex(tl.start_date)
lab = tl[f"outcome_H{H}"].to_numpy()
code = {"pass": "P", "bust_daily": "d", "bust_floor": "F", "abandon": "a",
        "not_reached": "."}
s = pd.Series([code[x] for x in lab], index=sd)

print(f"### Cohort outcomes by start date — vm {VM}, horizon {H} calendar days\n")
print("`P` pass · `F` static floor -10 % · `d` daily -5 % · `a` abandon "
      "· `.` unresolved inside the horizon\n")
print("```")
print("year | one character per cohort start (7 trading days apart)      | p(pass)")
for yr, g in s.groupby(s.index.year):
    pp = (g == "P").mean()
    print(f"{yr} | {''.join(g.values):<40s} | {pp*100:5.1f}%  (n={len(g)})")
print("```\n")

y = (lab == "pass").astype(float)
tab = pd.DataFrame({
    "quarter": [f"Q{q}" for q in (1, 2, 3, 4)],
    "n": [int((sd.quarter == q).sum()) for q in (1, 2, 3, 4)],
    "p_pass_%": [100 * y[sd.quarter == q].mean() for q in (1, 2, 3, 4)],
})
print(tab.round(1).to_string(index=False))
