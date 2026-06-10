"""v2.2 Part A — acceptance gate: challenge IS/OOS/pooled + identity + coverage.
STOP if pooled outside [86, 91]."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine_v22 as V
import config_v22 as C22
E = V.E

TAB = HERE / "tables"; TAB.mkdir(exist_ok=True)
t0 = time.time()

M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)

V.COUNTERS.update(micro_fires=0, backstop_fires=0)
rows = []
for win, lo, hi in C22.WINDOWS:
    st = E.cohort_starts(M, lo, hi, C22.COHORT_STEP)
    for i0 in st:
        r = V.run_funnel(M, int(i0), WT, ON, C22.CFG_CHALLENGE, wall=C22.WALL)
        rows.append(dict(win=win, start=M["dates"][int(i0)], funded=r["funded"],
                         attempts=r["attempts"], t=r["t"], micro=r["micro"]))
d = pd.DataFrame(rows)
d.to_csv(TAB / "challenge_cohorts_v22.csv", index=False)

p_is = d[d.win == "IS"].funded.mean()
p_oos = d[d.win == "OOS"].funded.mean()
pooled = d.funded.mean()
print(f"v2.2 CHALLENGE: IS {p_is*100:.1f} / OOS {p_oos*100:.1f} / pooled {pooled*100:.2f}"
      f"  att {d.attempts.mean():.2f}  med_t IS {d[d.win=='IS'].loc[lambda x: x.funded,'t'].median():.0f}"
      f" OOS {d[d.win=='OOS'].loc[lambda x: x.funded,'t'].median():.0f}"
      f"  [{time.time()-t0:.0f}s]")
print(f"micro-ORB fires: {V.COUNTERS['micro_fires']} day-trades; "
      f"cohorts with >=1 micro fire: {(d.micro > 0).mean()*100:.1f}%; "
      f"backstop fires: {V.COUNTERS['backstop_fires']}")
print(f"cash-conservation identity: asserted per attempt (no assertion raised = exact)")

if not (0.86 <= pooled <= 0.91):
    print(f"*** ACCEPTANCE FAIL: pooled {pooled*100:.2f} outside [86, 91] — STOP ***")
    sys.exit(1)
print("ACCEPTANCE PASS: pooled in [86, 91] (expected ~88-89)")
