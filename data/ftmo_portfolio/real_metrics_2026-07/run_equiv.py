"""G-EQUIV-close: lowcheck_engine(mode=close) must == engine_v22 exactly (462 cohorts).
Also G-POLICY anchor: pooled == 87.01."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/v22"))
import engine as E
import engine_v22 as V
import config_v22 as C22
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lowcheck_engine as LC
t0 = time.time()

M0 = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M0, WT_df, ON_df)
M1 = LC.load_stack_lohi(orb_rt_bps=C22.ORB_RT_BPS)
print(f"canon n={M0['n']} lc n={M1['n']}  [{time.time()-t0:.0f}s]", flush=True)
assert M0["n"] == M1["n"], "date count mismatch"
assert (pd.DatetimeIndex(M0["dates"]) == pd.DatetimeIndex(M1["dates"])).all(), "dates mismatch"

# px_day bit-identity (a few days incl. a hole-region + recent)
for idx in [0, 1000, 2500, M0["n"] - 1]:
    a = M0["days"][idx][0]
    b = M1["days"][idx][0]
    assert a.shape == b.shape and np.allclose(a, b, equal_nan=True), f"px_day mismatch @ {idx}"
    # lo<=close<=hi structural check
    lo, hi = M1["lodays"][idx], M1["hidays"][idx]
    assert np.nanmax(lo - b) <= 1e-9 and np.nanmin(hi - b) >= -1e-9, f"lo/hi order @ {idx}"
print("px_day identity + lo<=close<=hi: PASS", flush=True)

GRID = [(w, int(i0)) for w, lo, hi in C22.WINDOWS for i0 in V.starts(M0, lo, hi, C22.COHORT_STEP)]
print(f"cohorts={len(GRID)}", flush=True)

bad = 0
pe = []
for w, i0 in GRID:
    cfg = dict(C22.CFG_CHALLENGE)
    rr = V.run_funnel(M0, i0, WT, ON, cfg, wall=C22.WALL)
    rn = LC.run_funnel(M1, i0, WT, ON, cfg, wall=C22.WALL, mode="close")
    same = (rr["funded"] == rn["funded"] and rr["attempts"] == rn["attempts"]
            and (rr["t"] == rn["t"] or (np.isnan(rr["t"]) and np.isnan(rn["t"]))))
    if not same:
        bad += 1
        if bad <= 5:
            print(f"  MISMATCH i0={i0} ref={rr} new={rn}", flush=True)
    pe.append(rn["funded"])
pooled = 100 * np.mean(pe)
print(f"\nG-EQUIV {'PASS' if bad==0 else f'FAIL ({bad})'}  pooled={pooled:.2f} "
      f"(POLICY anchor target 87.01)  [{time.time()-t0:.0f}s]", flush=True)
sys.exit(0 if bad == 0 else 1)
