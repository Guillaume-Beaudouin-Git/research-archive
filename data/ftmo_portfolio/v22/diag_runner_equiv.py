"""Diagnostic: v22 runner with micro_orb=False + fix_deadlock=True must reproduce
the attribution-study no-ORB+fix reference (88.3 pooled). Separates runner-equivalence
from micro-ORB-specific effects."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine_v22 as V
import config_v22 as C22
E = V.E

t0 = time.time()
M = V.load_stack()
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)

cfg = dict(C22.CFG_CHALLENGE, micro_orb=False)   # backstop-only, like audit arm
rows = []
for win, lo, hi in C22.WINDOWS:
    for i0 in V.starts(M, lo, hi, 7):
        r = V.run_funnel(M, int(i0), WT, ON, cfg, wall=91)
        rows.append(dict(win=win, funded=r["funded"]))
d = pd.DataFrame(rows)
print(f"v22 runner, micro OFF + backstop: IS {d[d.win=='IS'].funded.mean()*100:.1f} "
      f"OOS {d[d.win=='OOS'].funded.mean()*100:.1f} pooled {d.funded.mean()*100:.2f} "
      f"(reference cleanroom no-ORB+fix: 88.8/87.8/88.3) [{time.time()-t0:.0f}s]")
