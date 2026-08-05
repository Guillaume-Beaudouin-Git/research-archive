"""CORRECTED gradient + asymmetric Pace legs, on a harness that carries the deployed
min-trading-days backstop (`fix_deadlock=True`, the cleanroom stand-in for the spec's
micro-ORB day counter — cross-validated against the v2.2 engine in validate_deadlock.py).

Everything the first pass measured is re-measured here, because the defect it inherited
sits exactly on the channel it priced (the timeout).
"""
from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd

import pace_lib as P

OUT = Path(__file__).resolve().parent.parent / "outputs"
OUT.mkdir(exist_ok=True)

WALLS = [65, 91, 130, 182, 270, 360]
LEG_WALLS = [91, 182]
RUNWAY = 275
N_PLACEBO = 12
BLOCK = 10

CFG = dict(P.CFG_LIVE, fix_deadlock=True)     # <- the correction


def _init():
    P.init()


def _job(a):
    kind, wall, mode, denom, draw = a
    M, _, _ = P.init()
    starts = P.cohort_starts(M, RUNWAY, 7)
    signs = None
    if kind == "placebo":
        rng = np.random.default_rng(20_000 + draw)
        signs = P.block_signs(M["n"], BLOCK, rng)
    r = P.eval_wall(wall, mode, denom, signs, starts, cfg=CFG, one_try=True)
    r["kind"], r["draw"] = kind, draw
    for k in ("funded_flags", "onetry_flags", "floor_flags", "daily_flags"):
        r[k] = r[k].tolist()
    return r


def main():
    M, _, _ = P.init()
    starts = P.cohort_starts(M, RUNWAY, 7)
    print(f"cohorts {len(starts)}  {M['dates'][0].date()} -> {M['dates'][-1].date()}")

    jobs = []
    for w in WALLS:
        jobs.append(("real", w, "coupled", w, -1))       # deployed coupling
        jobs.append(("real", w, "frozen", 91, -1))       # pure HORIZON channel
        jobs.append(("real", w, "off", 91, -1))          # pace removed
        for k in range(N_PLACEBO):                       # zero-edge null, same horizon
            jobs.append(("placebo", w, "coupled", w, k))
            jobs.append(("placebo", w, "off", 91, k))
    for w in LEG_WALLS:
        jobs.append(("real", w, "hi_only", w, -1))
        jobs.append(("real", w, "lo_only", w, -1))
        for k in range(N_PLACEBO):
            jobs.append(("placebo", w, "hi_only", w, k))
            jobs.append(("placebo", w, "lo_only", w, k))
    # A-without-B: abandon horizon 182 with the Pace denominator still pinned at 91
    jobs.append(("AnoB", 182, "frozen", 91, -1))

    with mp.Pool(8, initializer=_init) as pool:
        res = pool.map(_job, jobs, chunksize=1)

    df = pd.DataFrame(res)
    fl = {k: df.pop(k) for k in
          ("funded_flags", "onetry_flags", "floor_flags", "daily_flags")}
    df.to_csv(OUT / "grid2_raw.csv", index=False)
    for k, v in fl.items():
        np.save(OUT / f"grid2_{k}.npy", np.array(v.tolist(), dtype=bool))
    print(df[df.kind != "placebo"].to_string(float_format=lambda x: f"{x:.4f}"))

    # per-cohort duty cycle under the corrected harness
    profs = [P.attempt_profile(starts, w, "coupled", w, cfg=CFG) for w in LEG_WALLS]
    p = P.attempt_profile(starts, 182, "frozen", 91, cfg=CFG, max_cal_phase=182)
    p["mode"] = "AnoB_denom91"
    profs.append(p)
    pd.concat(profs, ignore_index=True).to_csv(
        Path(__file__).resolve().parent.parent / "tables" / "pace_profile2.csv",
        index=False)
    print("saved", OUT / "grid2_raw.csv")


if __name__ == "__main__":
    main()
