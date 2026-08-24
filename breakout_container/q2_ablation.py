"""Q2/Q3 — funded container ablation (THE test). Reuses the audited harness (lib_inject).
Baseline reproduction gate (0.9791/$1442) -> dose grid {0.10,0.25,0.50,1.0} x {lower-bound,
realistic} cost x {primary day-start, conservative combined-low}. Triplets + Δ vs baseline."""
import sys, time, json
from pathlib import Path
import numpy as np, pandas as pd
import lib_inject as LI

HERE = Path(__file__).resolve().parent; CACHE = HERE/"_cache"; RES = HERE/"results"
t0 = time.time()
DOSES = [0.10, 0.25, 0.50, 1.0]
VOLT = 0.10                      # "1.0x dose" = breakout vol-targeted to 10%/yr standalone

M = LI.load_stack()
WT, ON = LI.V.align(M, *LI.E.build_signals())
fst = LI.fstarts(M)
print(f"stack n={M['n']}  FUNDED_WINDOWS cohorts n={len(fst)} [{time.time()-t0:.0f}s]")

# ---- baseline (brk OFF) reproduction gate ----
base = LI.funded_run(M, WT, ON, False, 0.0, fst)
s0, fv0, me0 = base["survive252"], base["fundedV"], base["min_eq_med"]
ok = abs(s0 - 0.9791) <= 0.005 and abs(fv0 - 1442) <= 30
print(f"BASELINE book-only: survive252 {s0*100:.2f}%  fundedV ${fv0:.0f}  min_eq_med ${me0:.0f}  "
      f"[target 97.91%/$1442]  {'REPRODUCED ✓' if ok else 'MISMATCH ✗'}")

cost_series = {"lb": pd.read_parquet(CACHE/"brk_pooled_lb.parquet"),
               "rl": pd.read_parquet(CACHE/"brk_pooled_rl.parquet")}
curve = {}
for cost, series in cost_series.items():
    vol = series["net"].std() * np.sqrt(252); lev_scale = VOLT / vol
    print(f"\n### cost={cost} (breakout net vol {vol*100:.1f}%/yr → VT lev_scale {lev_scale:.2f} for 1.0x=10%vol) ###")
    for variant, comb in [("primary", False), ("combined", True)]:
        cov = LI.set_brk(M, series, lev_scale)
        print(f"  [{variant}] dose | survive252 | Δsurv | fundedV | Δextract | min_eq | net-positive?")
        for d in DOSES:
            r = LI.funded_run(M, WT, ON, True, d, fst, combined=comb)
            ds = r["survive252"] - s0; de = r["fundedV"] - fv0
            netpos = (ds >= -0.025) and (de > 0)
            curve[f"{cost}_{variant}_{d}"] = dict(survive252=r["survive252"], d_surv=ds, fundedV=r["fundedV"],
                                                  d_extract=de, min_eq=r["min_eq_med"], net_positive=bool(netpos))
            print(f"         {d:>4.2f} | {r['survive252']*100:>8.2f}% | {ds*100:>+5.1f} | ${r['fundedV']:>6.0f} | "
                  f"{de:>+8.0f} | ${r['min_eq_med']:>6.0f} | {'YES' if netpos else 'no'}", flush=True)

# ---- verdict ----
netpos = [k for k, v in curve.items() if v["net_positive"]]
# the decisive cell: realistic cost, primary variant, any dose net-positive?
rl_primary_netpos = [k for k in netpos if k.startswith("rl_primary")]
best = max(curve.items(), key=lambda kv: (kv[1]["d_surv"], kv[1]["d_extract"]))
print(f"\nnet-positive cells (Δsurv≥−2.5pt AND Δextract>0): {netpos if netpos else 'NONE'}")
print(f"  → at REALISTIC cost, PRIMARY variant: {rl_primary_netpos if rl_primary_netpos else 'NONE'}")
print(f"best cell by (Δsurv,Δextract): {best[0]} → Δsurv {best[1]['d_surv']*100:+.1f}pt Δextract {best[1]['d_extract']:+.0f}")
if rl_primary_netpos: verdict = "(a) IMPROVES — first viable container candidate"
elif all(v["d_surv"] < -0.025 for k, v in curve.items() if "rl_primary" in k): verdict = "(b) DILUTES like the overnight family"
else: verdict = "(c) NEUTRAL — decorrelated but no net-positive at realistic cost"
print(f"\nVERDICT Q2/Q3: {verdict}")
json.dump(dict(baseline=dict(survive252=s0, fundedV=fv0, min_eq=me0, reproduced=bool(ok)),
               curve=curve, netpos=netpos, rl_primary_netpos=rl_primary_netpos, verdict=verdict),
          open(RES/"q2_ablation.json","w"), indent=1)
print(f"saved q2 [{time.time()-t0:.0f}s]")
