"""THE DELIVERABLE — two-lever decision matrix.

  Lever A = abandon-and-rebuy POLICY (stop retiring an attempt at day 91).
            Zero code. `WALL_DAYS` is not an operational deadline (first pass, §1-2).
  Lever B = `WALL_DAYS` in the frozen spec, i.e. the Pace DENOMINATOR.
            Live code -> freeze chain + Saturday window.

Four cells, all on the SAME 432 cohorts, all against the deployed baseline:
  rien   horizon  91, denominator  91
  A only horizon 182, denominator  91   (the interaction the first pass flagged)
  B only horizon  91, denominator 182
  A+B    horizon 182, denominator 182
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import econ2
import pace_lib as P

OUT = Path(__file__).resolve().parent.parent / "outputs"
TAB = Path(__file__).resolve().parent.parent / "tables"
pd.set_option("display.width", 250)

G = pd.read_csv(OUT / "grid2_raw.csv")
B = pd.read_csv(OUT / "bonly_raw.csv")
GF = {k: np.load(OUT / f"grid2_{k}_flags.npy") for k in ("funded", "onetry", "floor")}
BF = {k: np.load(OUT / f"bonly_{k}_flags.npy") for k in ("funded", "onetry", "floor")}


def row_of(df, **kw):
    q = np.ones(len(df), bool)
    for k, v in kw.items():
        q &= (df[k] == v).to_numpy()
    i = np.flatnonzero(q)
    assert len(i) == 1, (kw, len(i))
    return int(i[0]), df.iloc[int(i[0])]


CELLS = {}
i, r = row_of(G, kind="real", wall=91, mode="coupled", draw=-1)
CELLS["rien   (h 91, denom 91)"] = ("G", i, r, 91)
i, r = row_of(G, kind="AnoB", wall=182, mode="frozen", pace_denom=91, draw=-1)
CELLS["A only (h 182, denom 91)"] = ("G", i, r, 182)
i, r = row_of(B, kind="real", wall=91, mode="frozen", pace_denom=182, draw=-1)
CELLS["B only (h 91, denom 182)"] = ("B", i, r, 91)
i, r = row_of(G, kind="real", wall=182, mode="coupled", draw=-1)
CELLS["A+B    (h 182, denom 182)"] = ("G", i, r, 182)

FL = {"G": GF, "B": BF}
base_src, base_i, base_r, base_w = CELLS["rien   (h 91, denom 91)"]

V = econ2.V_BASE
rows = []
for name, (src, i, r, wall) in CELLS.items():
    cycle = r.p_campaign * r.mean_days + (1 - r.p_campaign) * wall
    ev = r.p_campaign * (V + econ2.FEE) - r.avg_attempts * econ2.FEE
    d = {}
    for met in ("funded", "onetry", "floor"):
        a, b = FL[src][met][i], FL[base_src][met][base_i]
        dd, lo, hi = P.block_boot_delta(a, b, P.cohort_block_len(cycle))
        d[met] = (dd * 100, lo * 100, hi * 100)
    rows.append(dict(
        option=name, p_campaign=r.p_campaign * 100,
        d_p_campaign=d["funded"][0], ci=f"[{d['funded'][1]:+.2f}, {d['funded'][2]:+.2f}]",
        p_1try=r.p_one_try * 100, d_p_1try=d["onetry"][0],
        p_floor_1try=r.d_bust_floor * 100, d_p_floor=d["floor"][0],
        floor_ci=f"[{d['floor'][1]:+.2f}, {d['floor'][2]:+.2f}]",
        attempts=r.avg_attempts,
        median_days_funded=r.median_days, cycle_days=cycle,
        usd_per_day=ev / cycle, ev_cycle=ev,
    ))
M = pd.DataFrame(rows)
M["d_usd_per_day"] = M.usd_per_day - M.usd_per_day.iloc[0]
M["d_cycle_days"] = M.cycle_days - M.cycle_days.iloc[0]
M["d_median_days"] = M.median_days_funded - M.median_days_funded.iloc[0]
M.to_csv(TAB / "two_lever_matrix.csv", index=False)

print("=" * 130)
print(f"TWO-LEVER MATRIX — deployed MONO book, corrected harness, V = ${V:,.0f} "
      f"(trader share, MONO pooled)")
print("=" * 130)
print(M[["option", "p_campaign", "d_p_campaign", "ci", "p_1try", "d_p_1try",
         "p_floor_1try", "d_p_floor", "floor_ci"]]
      .to_string(index=False, float_format=lambda x: f"{x:+.2f}"))
print()
print(M[["option", "attempts", "median_days_funded", "d_median_days", "cycle_days",
         "d_cycle_days", "usd_per_day", "d_usd_per_day"]]
      .to_string(index=False, float_format=lambda x: f"{x:+.2f}"))

# EV/time robustness of the matrix ranking across the whole audited V range
print("\n$/day of each option across the audited V range:")
out = []
for lab, v in econ2.V_GRID.items():
    o = {"V scenario": lab, "V": v}
    for name, (src, i, r, wall) in CELLS.items():
        cyc = r.p_campaign * r.mean_days + (1 - r.p_campaign) * wall
        o[name.split()[0]] = (r.p_campaign * (v + econ2.FEE)
                              - r.avg_attempts * econ2.FEE) / cyc
    o["best"] = max(("rien", "A", "B", "A+B"), key=lambda k: o[k])
    out.append(o)
R = pd.DataFrame(out)
R.to_csv(TAB / "matrix_by_V.csv", index=False)
print(R.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

# B-only denominator sweep (all at horizon 91) — is B resolvable at all?
print("\nLever B in isolation — Pace denominator swept at a FIXED horizon of 91:")
b = B[B.kind == "real"][["pace_denom", "p_campaign", "p_one_try", "d_bust_floor",
                         "d_bust_daily", "median_days", "avg_attempts"]]
bi, _ = row_of(B, kind="real", wall=91, mode="frozen", pace_denom=91)
ci = []
for _, rr in b.iterrows():
    j, _ = row_of(B, kind="real", wall=91, mode="frozen", pace_denom=int(rr.pace_denom))
    dd, lo, hi = P.block_boot_delta(BF["funded"][j], BF["funded"][bi], 7)
    ci.append(f"{dd*100:+.2f} [{lo*100:+.2f}, {hi*100:+.2f}]")
b = b.copy()
b["d_p_campaign_vs_91"] = ci
b.to_csv(TAB / "lever_B_sweep.csv", index=False)
print(b.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
