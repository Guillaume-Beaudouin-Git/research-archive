"""Sensitivities of the decision table.

S1  swap drift measured on the live account (spec_bounds_breach = 1):
       US100 long -630.80 vs anchor -637.16  (x0.9900)
       GER40 long -442.75 vs anchor -393.88  (x1.1241)
    plus a uniform x1.12 stress on both index legs.
S2  cost of the index leg: the sim charges 2.2 bps RT; COST_AUDIT measures
    US100 1.80 / GER40 1.73 -> spread_mul 0.80.
S3  Pace denominator: frozen 91 (deployed) vs COUPLED to the horizon vs OFF.
S4  breaker slippage `brk_slip` = 1 M5 range against the position — a partial,
    admittedly crude, probe of the intra-M5 tail the engine cannot see.
S5  the FULL 4-sleeve book (gold + J1 re-armed) — CONTREFACTUEL, not the base case.
"""
import time

import numpy as np
import pandas as pd

import p2_lib as L

E = L.E
t0 = time.time()
VMS = [8, 10, 12, 14, 18, 22, 28]
HORIZONS = [14, 21, 28, 35, 49, 70]

M0 = L.market()
starts = L.cohort_starts(M0, runway_td=60, step=7)
WT0, ON0 = L.book_mono(M0)

DRIFT = [1.0, 1.0, 630.80 / 637.16, 442.75 / 393.88]
STRESS = [1.0, 1.0, 1.12, 1.12]

ARMS = [
    ("base            (anchor swaps, 2.2 bps, pace denom 91)", dict()),
    ("S1a live swap drift (US100 x0.99, GER40 x1.124)", dict(leg_swap_mul=DRIFT)),
    ("S1b swap stress  (both index legs x1.12)", dict(leg_swap_mul=STRESS)),
    ("S1c swap stress  (all legs x1.25)", dict(swap_mul=1.25)),
    ("S2  measured index cost (2.2 -> 1.8 bps)", dict(spread_mul=1.80 / 2.20)),
    ("S3a pace denominator COUPLED to horizon", dict(pace="coupled")),
    ("S3b pace OFF", dict(pace="off")),
    ("S4  breaker slippage 1 x M5 range", dict(cfg=dict(brk_slip=1.0))),
    ("S5  FULL 4-sleeve book (contrefactuel)", dict(book="full")),
]

rows = []
for name, kw in ARMS:
    M = L.market(swap_mul=kw.get("swap_mul", 1.0),
                 spread_mul=kw.get("spread_mul", 1.0),
                 leg_swap_mul=kw.get("leg_swap_mul"))
    WT, ON = (L.book_full(M) if kw.get("book") == "full" else L.book_mono(M))
    cfg = dict(L.CFG_LIVE, **kw.get("cfg", {}))
    pace = kw.get("pace", "frozen")
    for vm in VMS:
        if pace == "coupled":
            for H in HORIZONS:                # denominator moves with the horizon
                L.set_pace(H, on=True)
                r = L.resolve(M, WT, ON, starts, vm_spec=float(vm), cfg=cfg, cap=H + 1)
                s = L.horizon_stats(r, H)
                rows.append(dict(arm=name, vm_spec=vm, weeks=H // 7, H_cal=H,
                                 p_pass=s["p_pass"], p_daily=s["p_daily"],
                                 p_floor=s["p_floor"], p_nr=s["p_not_reached"],
                                 med_cal=s["med_cal"]))
            continue
        L.set_pace(91, on=(pace != "off"))
        r = L.resolve(M, WT, ON, starts, vm_spec=float(vm), cfg=cfg)
        for H in HORIZONS:
            s = L.horizon_stats(r, H)
            rows.append(dict(arm=name, vm_spec=vm, weeks=H // 7, H_cal=H,
                             p_pass=s["p_pass"], p_daily=s["p_daily"],
                             p_floor=s["p_floor"], p_nr=s["p_not_reached"],
                             med_cal=s["med_cal"]))
    print(f"  {name:<52} {time.time()-t0:6.1f}s")

s = pd.DataFrame(rows)
s.to_csv(L.TAB / "sensitivity_phase2.csv", index=False)
piv = s.pivot_table(index="arm", columns=["weeks"], values="p_pass",
                    aggfunc=lambda x: np.nan)  # placeholder
for wk in (2, 5, 10):
    sub = s[s.weeks == wk].pivot(index="arm", columns="vm_spec", values="p_pass")
    print(f"\n=== p(pass) at {wk} weeks ===")
    print(sub.round(4).to_string())
print(f"\nelapsed {time.time()-t0:.1f}s")
