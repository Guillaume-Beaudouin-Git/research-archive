"""Wall gradient on real historical paths + horizon/Pace decomposition + sign placebo.

Three pace modes at every wall W:
  coupled : cfg["max_cal"] = W everywhere  -> what the SIM does today (horizon + Pace move together)
  frozen  : timeout = W, Pace denominator pinned at 91 -> pure HORIZON channel
  off     : timeout = W, Pace multiplier identically 1 -> horizon with the feature removed
Pace channel at wall W = coupled(W) - frozen(W). Feature cost at W = frozen(W) - off(W).
"""
from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd

import wall_lib as W

OUT = Path(__file__).resolve().parent.parent / "outputs"
OUT.mkdir(exist_ok=True)

WALLS = [65, 91, 130, 182, 270, 360]
RUNWAY = 275            # trading days of runway -> same cohort set for EVERY wall
N_PLACEBO = 12
BLOCK = 10              # trading days of persistence in the placebo sign schedule


def _init():
    W.init()


def _job(a):
    kind, wall, mode, denom, draw = a
    M, _, _ = W.init()
    starts = W.cohort_starts(M, RUNWAY, 7)
    signs = None
    if kind == "placebo":
        rng = np.random.default_rng(10_000 + draw)      # same draw id -> same signs at every wall
        signs = W.block_signs(M["n"], BLOCK, rng)
    r = W.eval_wall(wall, mode, denom, signs, starts, one_try=(kind != "placebo" and kind != "placebo_off"))
    r["kind"] = kind
    r["draw"] = draw
    r["pace_denom"] = denom
    r.pop("times_all", None)
    r["funded_flags"] = r["funded_flags"].tolist()
    return r


def main():
    M, _, _ = W.init()
    starts = W.cohort_starts(M, RUNWAY, 7)
    print(f"engine days {M['n']}  {M['dates'][0].date()} -> {M['dates'][-1].date()}")
    print(f"cohorts (runway {RUNWAY} td, step 7) = {len(starts)}")

    jobs = []
    for w in WALLS:
        jobs.append(("real", w, "coupled", w, -1))
        jobs.append(("real", w, "frozen", 91, -1))
        jobs.append(("real", w, "off", 91, -1))
    # Pace denominator sweep at a FIXED horizon (wall = 91): isolates the feature.
    for d in WALLS:
        jobs.append(("denom91", 91, "frozen", d, -1))
    # Placebo: matched-autocorrelation zero-edge null, at every wall, deployed semantics.
    for w in WALLS:
        for k in range(N_PLACEBO):
            jobs.append(("placebo", w, "coupled", w, k))
            jobs.append(("placebo_off", w, "off", 91, k))

    with mp.Pool(8, initializer=_init) as pool:
        res = pool.map(_job, jobs, chunksize=1)

    df = pd.DataFrame(res)
    flags = df.pop("funded_flags")
    df.to_csv(OUT / "grid_raw.csv", index=False)
    np.save(OUT / "funded_flags.npy", np.array(flags.tolist(), dtype=bool))
    print(df[df.kind.isin(("real", "denom91"))].to_string(
        float_format=lambda x: f"{x:.4f}"))
    print("saved", OUT / "grid_raw.csv")


if __name__ == "__main__":
    main()
