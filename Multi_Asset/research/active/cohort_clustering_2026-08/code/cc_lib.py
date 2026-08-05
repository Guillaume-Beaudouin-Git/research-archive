"""Cohort-clustering harness — reuses the phase-2 sizing machine verbatim.

Nothing about the simulator is re-implemented here. `p2_lib` is imported from the
worktree checkout (it is tracked); only the OUTPUT paths are redirected so this
study writes into its own directory. The engine and the market caches are read
from the MAIN checkout by absolute path, READ-ONLY (they are gitignored, hence
absent from a fresh worktree).

Base case, unchanged from `phase2_sizing_2026-08`:
  DEPLOYED MONO book (gold w=0, J1 off), phase 2 (target +5 %), daily -5 % on the
  EQUITY path, STATIC -10 % floor, min_trading_days = 4 with the micro-ORB counter
  ARMED (the deployed spec), p2_mult = 1.2, Pace denominator frozen at 91.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
P2 = STUDY.parent / "phase2_sizing_2026-08" / "code"
sys.path.insert(0, str(P2))

import p2_lib as L  # noqa: E402

OUT = STUDY / "outputs"
TAB = STUDY / "tables"
OUT.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)
L.OUT, L.TAB = OUT, TAB

E, V = L.E, L.V
STEP = 7          # trading days between cohort starts (463 cohorts, as inherited)
RUNWAY = 60       # trading days of runway required of every cohort
BLOCK_SIGNS = 10  # trading days of sign persistence in the placebo


def stack():
    """Market stack + deployed MONO book + frozen Pace denominator."""
    M = L.market()
    WT, ON = L.book_mono(M)
    L.set_pace(91, on=True)
    starts = L.cohort_starts(M, runway_td=RUNWAY, step=STEP)
    dates = pd.DatetimeIndex(M["dates_idx"])
    sd = pd.DatetimeIndex([dates[i] for i in starts])
    return M, WT, ON, starts, sd


def outcome_at(res: pd.DataFrame, H: int) -> pd.Series:
    """Outcome collapsed on calendar horizon H (exact identity, cf. p2_lib)."""
    within = res["cal_days"] <= H
    o = res["out"].where(within, "not_reached")
    return o.replace({"timeout": "not_reached"}).reset_index(drop=True)


# ------------------------------------------------------------------ clustering
def runs(x: np.ndarray) -> np.ndarray:
    """Lengths of maximal constant runs of a 1-D label array."""
    if len(x) == 0:
        return np.array([], int)
    b = np.flatnonzero(x[1:] != x[:-1])
    return np.diff(np.concatenate(([-1], b, [len(x) - 1])))


def cluster_stats(lab: np.ndarray) -> dict:
    """Summary of how strongly identical outcomes group along the start axis."""
    r = runs(lab)
    y = (lab == "pass").astype(float) if lab.dtype.kind in "OU" else lab.astype(float)
    n = len(y)
    out = dict(n_runs=len(r), mean_run=float(r.mean()), max_run=int(r.max()),
               p_run_ge5=float((r >= 5).mean()))
    for k in (1, 2, 3, 4, 6, 8):
        if n > k and y.std() > 0:
            out[f"ac{k}"] = float(np.corrcoef(y[:-k], y[k:])[0, 1])
        else:
            out[f"ac{k}"] = np.nan
    # variance ratio of the pass count in non-overlapping windows of q cohorts
    for q in (4, 8, 13):
        m = n // q
        if m >= 3:
            w = y[:m * q].reshape(m, q).sum(axis=1)
            exp = q * y.mean() * (1 - y.mean())
            out[f"vr{q}"] = float(w.var(ddof=1) / exp) if exp > 0 else np.nan
        else:
            out[f"vr{q}"] = np.nan
    out["p_bar"] = float(y.mean())
    return out


def n_eff(sd: pd.DatetimeIndex, H_cal: int) -> float:
    """Independent windows: total span / horizon (non-overlapping tiling)."""
    span = (sd[-1] - sd[0]).days + H_cal
    return span / H_cal
