"""Q3 — the trap: conditional bust rate after a fresh cycle-peak (gain->lever->drawdown),
asymmetry ON vs OFF. Q4 daily plateau is read directly off the main table."""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import book_funded_dynamic as B
import q_funded_sizing as Q
V, C22, E = B.V, B.C22, B.E

M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals(); WT, ON = E.align_signals(M, WT_df, ON_df)
st = Q.cohorts(M, horizon=504)
out = {}
for asym in (False, True):
    B.DIAG["bust_days_since_peak"].clear()
    cfg = dict(C22.CFG_FUNDED, vm=1.0, alpha=4.0, asym=asym, c_keep=0.20, ramp=0.02, vm_cap=3.0)
    n_bust = 0
    for s in st:
        r = B.run_funded_dyn(M, int(s), WT, ON, dict(cfg, diag=True), horizon=504,
                             wd_every=C22.FUNDED_WD_EVERY)
        if r["busted"]:
            n_bust += 1
    dsp = np.array(B.DIAG["bust_days_since_peak"])
    near = float((dsp <= 10).mean()) if len(dsp) else float("nan")
    out[f"asym{int(asym)}"] = dict(n_bust=n_bust, busts_within_10d_of_peak=round(near, 3),
                                   median_days_since_peak=float(np.median(dsp)) if len(dsp) else None)
    print(f"asym={asym} (alpha=4, most aggressive): n_bust {n_bust}  "
          f"frac busts within 10d of fresh peak {near:.2f}  median days-since-peak "
          f"{np.median(dsp) if len(dsp) else None}")
(HERE.parent / "results" / "q3_trap.json").write_text(json.dumps(out, indent=2))
print("written q3_trap.json")
