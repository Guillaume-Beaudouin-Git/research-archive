"""Lever B in isolation: change WALL_DAYS in the spec (the Pace denominator) while the
human keeps abandoning at 91. Needed for the two-lever matrix; the deployed coupling
cannot separate them."""
from __future__ import annotations
import multiprocessing as mp
from pathlib import Path
import numpy as np, pandas as pd
import pace_lib as P

OUT = Path(__file__).resolve().parent.parent / "outputs"
CFG = dict(P.CFG_LIVE, fix_deadlock=True)
RUNWAY, N_PLACEBO, BLOCK = 275, 12, 10


def _init():
    P.init()


def _job(a):
    kind, denom, draw = a
    M, _, _ = P.init()
    starts = P.cohort_starts(M, RUNWAY, 7)
    signs = None
    if kind == "placebo":
        signs = P.block_signs(M["n"], BLOCK, np.random.default_rng(20_000 + draw))
    r = P.eval_wall(91, "frozen", denom, signs, starts, cfg=CFG, one_try=True)
    r["kind"], r["draw"] = kind, draw
    for k in ("funded_flags", "onetry_flags", "floor_flags", "daily_flags"):
        r[k] = r[k].tolist()
    return r


if __name__ == "__main__":
    jobs = [("real", d, -1) for d in (65, 91, 130, 182, 270, 360)]
    jobs += [("placebo", d, k) for d in (91, 182) for k in range(N_PLACEBO)]
    with mp.Pool(8, initializer=_init) as pool:
        res = pool.map(_job, jobs, chunksize=1)
    df = pd.DataFrame(res)
    fl = {k: df.pop(k) for k in ("funded_flags", "onetry_flags", "floor_flags", "daily_flags")}
    df.to_csv(OUT / "bonly_raw.csv", index=False)
    for k, v in fl.items():
        np.save(OUT / f"bonly_{k}.npy", np.array(v.tolist(), dtype=bool))
    print(df[df.kind == "real"].to_string(float_format=lambda x: f"{x:.4f}"))
