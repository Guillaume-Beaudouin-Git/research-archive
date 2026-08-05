"""Main grid: p(phase-2 pass, SINGLE attempt) over horizon x vm, real + placebo.

Base case = DEPLOYED MONO book, Pace denominator frozen at 91 (the frozen spec),
min-trading-days backstop ARMED, Swing margin, EA v2.4 breaker semantics.
"""
import sys
import time

import numpy as np
import pandas as pd

import p2_lib as L

E = L.E
t0 = time.time()

# argv: optional "low" -> the SUB-CAP sweep, where vm is still the binding knob
LOW = len(sys.argv) > 1 and sys.argv[1] == "low"
VMS = [2, 3, 4, 5, 6, 7] if LOW else [4, 6, 8, 10, 12, 14, 16, 18, 22, 28]
TAG = "_low" if LOW else ""
HORIZONS = [7, 14, 21, 28, 35, 42, 49, 56, 63, 70]          # calendar days = 7 x weeks
N_PLACEBO = 30
BLOCK_SIGNS = 10                                            # trading days, matched persistence
ERA_LO = "2021-01-01"

M = L.market()
WT, ON = L.book_mono(M)
L.set_pace(91, on=True)
starts = L.cohort_starts(M, runway_td=60, step=7)
dates = pd.DatetimeIndex(M["dates_idx"])
start_dates = pd.DatetimeIndex([dates[i] for i in starts])
post21 = np.asarray(start_dates >= pd.Timestamp(ERA_LO))
print(f"cohorts {len(starts)}  post-2021 {post21.sum()}")

rows, real_res = [], {}
for vm in VMS:
    res = L.resolve(M, WT, ON, starts, vm_spec=float(vm))            # v2.2 = deployed
    res_cr = L.resolve(M, WT, ON, starts, vm_spec=float(vm),         # cross-check
                       cfg=dict(L.CFG_LIVE, micro_orb=False), engine="clean")
    real_res[vm] = res
    res.to_csv(L.OUT / f"resolve{TAG}_vm{vm}.csv", index=False)

    # placebo: same horizon, same cohorts, zero expected edge, matched persistence
    pl = []
    for k in range(N_PLACEBO):
        rng = np.random.default_rng(70_000 + 977 * vm + k)
        L.set_signs(L.block_signs(M["n"], BLOCK_SIGNS, rng))
        pl.append(L.resolve(M, WT, ON, starts, vm_spec=float(vm)))
        L.set_signs(None)

    for H in HORIZONS:
        s = L.horizon_stats(res, H)
        blk = L.block_for_horizon(H)
        lo, hi = L.block_boot_ci(s["pass_flags"].astype(float), blk, seed=11)
        # placebo distribution of p(pass) at the SAME horizon
        pflags = np.array([L.horizon_stats(p, H)["pass_flags"] for p in pl], float)
        p_pl = pflags.mean(axis=1)
        # paired edge: real - mean placebo, CI from paired block bootstrap on cohorts
        e_lo, e_hi, e_sd = L.paired_block_boot(
            s["pass_flags"].astype(float), pflags.mean(axis=0), blk, seed=12)
        se = L.horizon_stats(res.loc[post21].reset_index(drop=True), H)
        rows.append(dict(
            weeks=H // 7, H_cal=H, vm_spec=vm, vm_eff=vm * L.CFG_LIVE["p2_mult"],
            n=s["n"], block=blk,
            p_pass=s["p_pass"], ci_lo=lo, ci_hi=hi,
            p_placebo=float(p_pl.mean()),
            pl_lo=float(np.quantile(p_pl, .05)), pl_hi=float(np.quantile(p_pl, .95)),
            edge=s["p_pass"] - float(p_pl.mean()),
            edge_lo=e_lo, edge_hi=e_hi, edge_sd=e_sd,
            mde80=2.802 * e_sd,
            p_daily=s["p_daily"], p_floor=s["p_floor"],
            p_abandon=s["p_abandon"], p_not_reached=s["p_not_reached"],
            med_cal=s["med_cal"], p90_cal=s["p90_cal"], med_td=s["med_td"],
            mean_cal_all=s["mean_cal_all"],
            p_pass_post21=se["p_pass"], n_post21=se["n"],
            p_daily_post21=se["p_daily"], p_floor_post21=se["p_floor"],
            p_nr_post21=se["p_not_reached"],
            p_pass_cleanroom=L.horizon_stats(res_cr, H)["p_pass"],
        ))
    print(f"  vm {vm:>3}  done  {time.time()-t0:6.1f}s")

g = pd.DataFrame(rows)
g.to_csv(L.TAB / f"grid_phase2{TAG}.csv", index=False)
print(g.pivot(index="weeks", columns="vm_spec", values="p_pass").round(4).to_string())
print(f"\nelapsed {time.time()-t0:.1f}s")
