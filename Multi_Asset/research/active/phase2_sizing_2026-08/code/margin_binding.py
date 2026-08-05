"""Is `vm` actually the sizing knob in phase 2? Arithmetic first, then measurement.

At 22:05 the MONO book holds BOTH index legs at `on_w * scale * eq`, and the 60 %
margin cap is enforced at the LIVE Swing rate (6.6667 % on indices):

    need = 2 * on_w * scale * eq * 0.066667 = 0.08 * scale * eq  <=  0.60 * eq
    =>  scale <= 7.5     (scale = vm_eff * taper * glide * pace)

With `vm_eff = vm_spec * p2_mult`, the cap binds whenever
`vm_spec * 1.2 * taper * glide * pace > 7.5`, i.e. from `vm_spec > 6.25` at a fresh
$10,000 account. Above that, raising vm changes NOTHING until taper drops the scale
back under 7.5 — which happens only at

    eq < FLOOR + INIT * 0.02 * 7.5 / (1.2*vm_spec)

This script prints that frontier, then MEASURES it: realised leg notional/equity at
the 22:05 posting, and the share of postings where the cap binds.
"""
import numpy as np
import pandas as pd

import p2_lib as L

E = L.E
MRATE_IDX = E.MRATE_SWING[2]
CAP = L.CFG_LIVE["margin_cap"]
ONW = L.CFG_LIVE["on_w"]
SCALE_MAX = CAP / (2 * ONW * MRATE_IDX)

rows = []
for vm in [2, 3, 4, 5, 6, 6.25, 7, 8, 10, 12, 14, 18, 22, 28]:
    eff = vm * L.CFG_LIVE["p2_mult"]
    room_thr = L.CFG_LIVE["taper"] * SCALE_MAX / eff       # taper needed to un-bind
    eq_thr = E.FLOOR + E.INIT * min(room_thr, L.CFG_LIVE["taper"])
    rows.append(dict(vm_spec=vm, vm_eff=eff,
                     binds_at_10000=eff > SCALE_MAX,
                     eq_below_which_vm_matters=(eq_thr if eff > SCALE_MAX else np.nan),
                     leg_notional_over_eq=ONW * min(eff, SCALE_MAX)))
fr = pd.DataFrame(rows)
fr.to_csv(L.TAB / "margin_cap_frontier.csv", index=False)
print(f"scale ceiling imposed by the 60 % margin cap at Swing rates: {SCALE_MAX:.2f}")
print(f"=> vm_spec ceiling = {SCALE_MAX / L.CFG_LIVE['p2_mult']:.2f}\n")
print(fr.round(3).to_string(index=False))

# ---------------------------------------------------------------- measurement
M = L.market()
WT, ON = L.book_mono(M)
L.set_pace(91, on=True)
starts = L.cohort_starts(M, runway_td=60, step=7)

E.MARGIN_LOG.clear()
meas = []
for vm in [4, 6, 8, 14, 28]:
    E.MARGIN_LOG.clear()
    r = L.resolve(M, WT, ON, starts, vm_spec=float(vm),
                  cfg=dict(L.CFG_LIVE, margin_log=True))
    need = np.array(E.MARGIN_LOG)
    meas.append(dict(vm_spec=vm, n_postings=len(need),
                     share_cap_binding=float((need > CAP + 1e-12).mean()),
                     median_need_over_eq=float(np.median(need)),
                     p_pass_35d=float(L.horizon_stats(r, 35)["p_pass"])))
mm = pd.DataFrame(meas)
mm.to_csv(L.TAB / "margin_cap_measured.csv", index=False)
print("\nMEASURED (pre-cap margin need / equity at every posting, phase 2):")
print(mm.round(4).to_string(index=False))
