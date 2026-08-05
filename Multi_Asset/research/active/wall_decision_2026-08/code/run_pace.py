"""GAP 1 — run the asymmetric Pace decomposition + the A-without-B interaction.

Outputs (tables/):
  pace_legs.csv        aggregate contrasts, walls 91 & 182, real + placebo
  pace_profile.csv     per-cohort leg duty cycle + first-attempt outcome
  pace_saturation.csv  the A-without-B configuration (horizon 182, denominator 91)
"""
from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd

import pace_lib as P

OUT = Path(__file__).resolve().parent.parent / "outputs"
TAB = Path(__file__).resolve().parent.parent / "tables"
OUT.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)

WALLS = [91, 182]
MODES = ["coupled", "hi_only", "lo_only", "off"]
RUNWAY = 275
N_PLACEBO = 12
BLOCK = 10


def _init():
    P.init()


def _job(a):
    kind, wall, mode, denom, draw, max_cal_phase = a
    M, _, _ = P.init()
    starts = P.cohort_starts(M, RUNWAY, 7)
    signs = None
    if kind == "placebo":
        rng = np.random.default_rng(20_000 + draw)     # same draw id at every wall/mode
        signs = P.block_signs(M["n"], BLOCK, rng)
    r = P.eval_wall(wall, mode, denom, signs, starts, one_try=True)
    r["kind"] = kind
    r["draw"] = draw
    for k in ("funded_flags", "onetry_flags", "floor_flags", "daily_flags"):
        r[k] = r[k].tolist()
    return r


def main():
    M, _, _ = P.init()
    starts = P.cohort_starts(M, RUNWAY, 7)
    print(f"engine {M['dates'][0].date()} -> {M['dates'][-1].date()}  n={M['n']}")
    print(f"cohorts (runway {RUNWAY} td, step 7) = {len(starts)}")

    jobs = []
    for w in WALLS:
        for m in MODES:
            jobs.append(("real", w, m, w, -1, None))
        for m in MODES:
            for k in range(N_PLACEBO):
                jobs.append(("placebo", w, m, w, k, None))
    # A-without-B: abandon horizon 182, Pace denominator still 91 (saturating).
    jobs.append(("AnoB", 182, "coupled", 91, -1, None))
    jobs.append(("AnoB", 182, "frozen", 91, -1, None))
    jobs.append(("AnoB", 182, "off", 91, -1, None))
    jobs.append(("AnoB", 182, "hi_only", 91, -1, None))
    jobs.append(("AnoB", 182, "lo_only", 91, -1, None))

    with mp.Pool(8, initializer=_init) as pool:
        res = pool.map(_job, jobs, chunksize=1)

    df = pd.DataFrame(res)
    flags = {k: df.pop(k) for k in
             ("funded_flags", "onetry_flags", "floor_flags", "daily_flags")}
    df.to_csv(OUT / "pace_raw.csv", index=False)
    for k, v in flags.items():
        np.save(OUT / f"pace_{k}.npy", np.array(v.tolist(), dtype=bool))
    print(df[df.kind != "placebo"].to_string(float_format=lambda x: f"{x:.4f}"))

    # ---- per-cohort profiles (duty cycle + outcome), deployed & A-without-B ----
    profs = []
    for w in WALLS:
        profs.append(P.attempt_profile(starts, w, "coupled", w))
    p = P.attempt_profile(starts, 182, "frozen", 91, max_cal_phase=182)
    p["mode"] = "AnoB_denom91"
    profs.append(p)
    prof = pd.concat(profs, ignore_index=True)
    prof.to_csv(TAB / "pace_profile.csv", index=False)
    print("\n--- duty cycle by wall (deployed coupling) ---")
    print(prof.groupby(["wall", "mode"])[["f_hi", "f_lo", "mean_x", "max_x"]]
          .mean().to_string(float_format=lambda x: f"{x:.4f}"))
    print("saved", OUT / "pace_raw.csv")


if __name__ == "__main__":
    main()
