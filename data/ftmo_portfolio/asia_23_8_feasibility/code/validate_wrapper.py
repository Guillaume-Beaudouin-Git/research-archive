"""Validation: patched engine with ASIA OFF must reproduce the canonical pooled 0.87."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asia_inject as AI
V, C22, E = AI.V, AI.C22, AI.E

t0 = time.time()
M = AI.load_asia_stack(spread_bps=1.5)        # ASIA arrays attached but asia_on=False below
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)

V.COUNTERS.update(micro_fires=0, backstop_fires=0)
rows = []
for win, lo, hi in C22.WINDOWS:
    for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
        r = V.run_funnel(M, int(i0), WT, ON, C22.CFG_CHALLENGE, wall=C22.WALL)
        rows.append(dict(win=win, funded=r["funded"], attempts=r["attempts"], t=r["t"]))
d = pd.DataFrame(rows)
p_is = d[d.win == "IS"].funded.mean()
p_oos = d[d.win == "OOS"].funded.mean()
pooled = d.funded.mean()
print(f"ASIA-OFF book: IS {p_is*100:.1f} / OOS {p_oos*100:.1f} / pooled {pooled*100:.2f}"
      f"  att {d.attempts.mean():.2f}  n={len(d)}  [{time.time()-t0:.0f}s]")
print("PASS" if 0.86 <= pooled <= 0.91 else "*** FAIL: wrapper altered the audited book ***")
