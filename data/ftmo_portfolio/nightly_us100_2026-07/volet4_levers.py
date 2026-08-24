#!/usr/bin/env python3
"""Volet 4 — remedy levers, QUANTIFIED (Δp(pass) vs the mono baseline).

The reversal (proven in volet1b): mono fails by return-STARVATION (drift 0.29 vs
0.80%/day), so the remedy is ADDING return engines, not cutting US100 risk. Quantify
each lever from the SAME audited engine, isolating contributions:
  MONO1  US100 only                     (Monday loss-night reality, pre-restamp)
  +GER40 US100+GER40 (=MONO2)           (monday_restamp deployed 2026-07-14)
  +J1    US100+GER40+J1 (gold=0)        (dé-gater J1 when USD/JPY out of zone)
  +GOLD  US100+GER40+gold (J1=0)        (gold signal wakes up)
  FULL   4 legs                         (all engines live)
Plus horizon lever (from volet1b sweep) for reference.

READ-ONLY. Engine imported from MAIN dir, NEVER mutated.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
import engine as E

LO, HI, STEP = "2014-01-01", "2024-12-31", 10
M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)

def us100_only(Mbase):
    Mx = dict(Mbase); Mx["days"] = [(px.copy(), b) for (px, b) in Mbase["days"]]
    for px, b in Mx["days"]:
        px[:, 3] = np.nan
    return Mx

WT_full = WT.copy()
WT_zero = np.zeros_like(WT)
WT_jponly = WT.copy(); WT_jponly[:, 0] = 0.0     # gold=0, J1 real
WT_goldonly = WT.copy(); WT_goldonly[:, 1] = 0.0  # J1=0, gold real
M_us100 = us100_only(M)

CFGS = [
    ("MONO1  US100 only",           M_us100, WT_zero),
    ("+GER40 (restamp) =MONO2",     M,       WT_zero),
    ("+J1    US100+GER40+J1",       M,       WT_jponly),
    ("+GOLD  US100+GER40+gold",     M,       WT_goldonly),
    ("FULL   4 legs",               M,       WT_full),
]

st = E.cohort_starts(M, pd.Timestamp(LO), pd.Timestamp(HI), STEP)
print(f"cohorts {len(st)}  ({LO}..{HI} step {STEP})\n")
print("=" * 74)
print("VOLET 4 — remedy levers @ wall=91d (Δ vs MONO1 baseline)")
print("=" * 74)
print(f"{'config':28s} {'p(pass)':>8s} {'Δ vs mono1':>11s} {'mean t_fund':>12s}")
base = None
for label, Mx, WTx in CFGS:
    rr = [E.run_funnel(Mx, int(i0), WTx, ON, E.CFG_V2, wall=91) for i0 in st]
    p = np.mean([r["funded"] for r in rr]) * 100
    tf = [r["t"] for r in rr if r["funded"] and np.isfinite(r["t"])]
    if base is None:
        base = p
    print(f"{label:28s} {p:7.1f}% {p-base:+10.1f}pt {np.median(tf):9.0f}d")
print("\n[each lever ADDS a return engine -> raises drift -> raises p(pass); "
      "cutting US100 size would LOWER drift -> strictly worse]")
