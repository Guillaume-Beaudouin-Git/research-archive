"""Non-regression: hooks OFF => clone identique au moteur committe."""
import mo_common as K, mo_engine as G
import numpy as np, pandas as pd
M, WT, ON = K.load()
V, C22 = K.V, K.C22
for name, cfg in [("v2.2", C22.CFG_CHALLENGE), ("v2.8_swing", C22.CFG_CHALLENGE_V28)]:
    ref, mine = [], []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            a = V.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)
            b = G.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)
            ref.append((a["funded"], a["attempts"], a["t"], a["micro"]))
            mine.append((b["funded"], b["attempts"], b["t"], b["micro"]))
    same = sum(1 for x, y in zip(ref, mine)
               if x[0] == y[0] and x[1] == y[1] and x[3] == y[3]
               and (np.isnan(x[2]) and np.isnan(y[2]) or x[2] == y[2]))
    p = np.mean([r[0] for r in ref])
    print(f"{name}: N={len(ref)} identiques={same}/{len(ref)}  p(campagne)={p*100:.2f}%")
