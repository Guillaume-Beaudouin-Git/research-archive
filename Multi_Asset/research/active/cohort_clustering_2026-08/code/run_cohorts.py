"""Regenerate the per-cohort resolution frames (real) + the overlap-matched placebo.

The placebo re-runs the FULL cohort machine on a series whose directional drift is
destroyed but whose autocorrelation is matched (+-1 sign schedule persistent in
blocks of 10 trading days, `p2_lib.block_signs`). Everything else is identical:
same cohort starts, same barriers, same costs, same swaps, same volatility path.
=> the placebo carries EXACTLY the same cohort-overlap structure as the real run
   and NO regime. That is the only comparison that can say anything.

usage: run_cohorts.py <vm> <n_placebo>
"""
import sys
import time

import numpy as np
import pandas as pd

import cc_lib as C

L = C.L
vm = float(sys.argv[1])
NPL = int(sys.argv[2]) if len(sys.argv) > 2 else 100
tag = f"vm{vm:g}"

t0 = time.time()
M, WT, ON, starts, sd = C.stack()
STARTS = np.array([str(d.date()) for d in sd])

fr = C.OUT / f"real_{tag}.csv"
if fr.exists():
    print(f"[{tag}] real already on disk, skipped", flush=True)
else:
    real = L.resolve(M, WT, ON, starts, vm_spec=vm)
    real["start_date"] = sd
    real.to_csv(fr, index=False)
    print(f"[{tag}] real done {time.time()-t0:.0f}s  "
          f"{real['out'].value_counts().to_dict()}", flush=True)

outs, cals = [], []
for k in range(NPL):
    rng = np.random.default_rng(310_000 + 977 * int(vm) + k)
    L.set_signs(L.block_signs(M["n"], C.BLOCK_SIGNS, rng))
    r = L.resolve(M, WT, ON, starts, vm_spec=vm)
    L.set_signs(None)
    outs.append(r["out"].to_numpy())
    cals.append(r["cal_days"].to_numpy())
    if (k + 1) % 5 == 0:          # checkpoint: the file is always usable
        np.savez_compressed(C.OUT / f"placebo_{tag}.npz", out=np.array(outs),
                            cal=np.array(cals), start=STARTS)
        print(f"[{tag}] placebo {k+1}/{NPL}  {time.time()-t0:.0f}s", flush=True)

np.savez_compressed(C.OUT / f"placebo_{tag}.npz",
                    out=np.array(outs), cal=np.array(cals), start=STARTS)
print(f"[{tag}] ALL DONE {time.time()-t0:.0f}s", flush=True)
