"""EV per unit of time on the phase-2 decision.

Phase 1 is SUNK (validated 2026-08-05). The object to maximise is the value of
standing at the start of phase 2, as a function of (vm, horizon):

    EV(vm,H) = p2 * (V + fee)                      value of getting funded
             - (1 - p2) * C_restart                cost of rebuilding a P1 pass
             - g * E[days consumed]                time is funded income not earned

  V        = $782, the AUDITED trader share of a funded account on the DEPLOYED MONO
             book (wall_decision_2026-08 §3; NOT the $2,529 gross-4-sleeve figure).
  fee      = $107, refunded on the first payout.
  g        = $4.14/day, the measured rate of the enterprise under lever A.
  C_restart= fee/p1 + g * T_restart, both MEASURED here: p1 and the P1 attempt length
             come from the same harness at the deployed vm.

Reported alongside: the assumption-light $/day = p2*(V+fee)/E[days], which ranks the
same way but ignores the cost of dying.
"""
import numpy as np
import pandas as pd

import p2_lib as L

E = L.E
V_TRADER, FEE, G = 782.0, 107.0, 4.14
RETRY_BD, GAP_BD, BD2CAL = 2, 3, 7.0 / 5.0

M = L.market()
WT, ON = L.book_mono(M)
L.set_pace(91, on=True)
starts = L.cohort_starts(M, runway_td=60, step=7)

# ---- phase 1, single attempt at the deployed vm, its own 91-day wall
p1res = L.resolve(M, WT, ON, starts, vm_spec=14.0, target=E.TARGET1, cap=91)
p1 = float((p1res["out"] == "pass").mean())
d1 = float(p1res["cal_days"].mean())
T_restart = d1 / p1 + (1.0 / p1 - 1.0) * RETRY_BD * BD2CAL + GAP_BD * BD2CAL
C_restart = FEE / p1 + G * T_restart
print(f"phase 1 @vm14, wall 91: p1={p1:.4f}  mean cal days/attempt={d1:.1f}")
print(f"T_restart={T_restart:.1f} cal days   C_restart=${C_restart:,.0f}")
pd.DataFrame([dict(p1=p1, mean_cal_days_p1_attempt=d1, T_restart_cal=T_restart,
                   C_restart_usd=C_restart, V=V_TRADER, fee=FEE, g=G)]
             ).to_csv(L.TAB / "econ_inputs.csv", index=False)

g = pd.read_csv(L.TAB / "grid_phase2.csv")
rows = []
for _, r in g.iterrows():
    p2, dd = r.p_pass, r.mean_cal_all
    for vname, Vv in (("weak_IS_347", 347.0), ("pooled_782", V_TRADER),
                      ("strong_OOS_1195", 1195.0)):
        Cr = FEE / p1 + G * T_restart
        ev = p2 * (Vv + FEE) - (1 - p2) * Cr - G * dd
        rows.append(dict(weeks=int(r.weeks), vm_spec=int(r.vm_spec), V=vname,
                         p_pass=p2, mean_days=dd, EV=ev, EV_per_day=ev / dd,
                         naive_per_day=p2 * (Vv + FEE) / dd))
ev = pd.DataFrame(rows)
ev.to_csv(L.TAB / "econ_phase2.csv", index=False)

for vname in ("weak_IS_347", "pooled_782", "strong_OOS_1195"):
    sub = ev[ev.V == vname].pivot(index="weeks", columns="vm_spec", values="EV")
    print(f"\n=== EV ($, net of time at ${G}/day and of the restart cost) — V {vname} ===")
    print(sub.round(0).to_string())

sub = ev[ev.V == "pooled_782"].pivot(index="weeks", columns="vm_spec", values="EV")
print("\n=== marginal EV of ONE more week (pooled V) ===")
print(sub.diff().round(1).to_string())
