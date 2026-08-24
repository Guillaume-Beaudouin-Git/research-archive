"""Q4 — SOYBEAN funded format (no target, no wall; daily -5% + static -10% barriers stay).

Standalone (book off), soy on, run_funded (horizon 504 td, withdraw every 14 td). Sweep K x
{V0 base, V1 stop -2.5%, V3 stop+skip}. p(survive 126/252 td ~ 6/12 mo), E[withdrawals], E[net].
Isolates whether the stop/skip eat the edge (compare V0 vs V1 vs V3). Funded cohorts over the
soy-active window 2018-06 -> 2024-06 (step 12; >=480 td runway each). Reuses soy_inject/run_funded.
"""
import json, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soy_inject as SI
V, C22, E = SI.V, SI.C22, SI.E

OUT = HERE.parent / "results"
KGRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
VARIANTS = {"V0_base": dict(X=None, skip_usda=False),
            "V1_stop": dict(X=0.025, skip_usda=False),
            "V3_stop_skip": dict(X=0.025, skip_usda=True)}
SPREAD = 2.0


def main():
    t0 = time.time()
    M = SI.load_soy_stack(spread_bps=SPREAD)
    WT0, ON0 = SI.book_off_signals(M)
    fstarts = V.starts(M, "2018-06-01", "2024-06-30", C22.FUNDED_STEP)
    print(f"funded cohorts (soy-active 2018-06..2024-06, step {C22.FUNDED_STEP}): {len(fstarts)}")

    res = {"spread_bp": SPREAD, "n_funded_cohorts": len(fstarts), "horizon_td": C22.FUNDED_HORIZON}
    sweep = {}
    print(f"\n{'variant':<14}{'K':>4} {'pSurv6mo':>9}{'pSurv12mo':>10}{'E[wd]$':>9}{'E[net]$':>9}"
          f"{'pBust':>7}{'medLife':>8}")
    for vname, vk in VARIANTS.items():
        net, low, traded, _ = SI.build_soy_arrays(M, K=1.0, spread_bps=SPREAD, **vk)  # placeholder
        sweep[vname] = {}
        for K in KGRID:
            net, low, traded, _ = SI.build_soy_arrays(M, K=K, spread_bps=SPREAD, **vk)
            SI.set_soy(M, net, low, traded)
            cfg = dict(C22.CFG_FUNDED, on_w=0.0, orb_risk=0.0, soy_on=True, soy_lev=1.0)
            lives, busted, wds, nets = [], [], [], []
            for i0 in fstarts:
                r = V.run_funded(M, int(i0), WT0, ON0, cfg,
                                 horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
                lives.append(r["life"]); busted.append(r["busted"])
                wds.append(r["wd"]); nets.append(r["wd"] + r["residual"])
            lives = np.array(lives); busted = np.array(busted)
            rec = dict(K=K,
                       p_survive_126=round(float((lives >= 126).mean()), 4),
                       p_survive_252=round(float((lives >= 252).mean()), 4),
                       E_wd=round(float(np.mean(wds)), 0), E_net=round(float(np.mean(nets)), 0),
                       p_bust=round(float(busted.mean()), 4),
                       med_life=int(np.median(lives)))
            sweep[vname][K] = rec
            print(f"{vname:<14}{K:>4} {rec['p_survive_126']*100:>8.1f}%{rec['p_survive_252']*100:>9.1f}%"
                  f"{rec['E_wd']:>9.0f}{rec['E_net']:>9.0f}{rec['p_bust']*100:>6.1f}%{rec['med_life']:>8}")
            SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
    res["sweep"] = sweep

    # funded-viable check (per frozen threshold): exists K with p_survive_252>=0.60 AND E[wd]>0
    best = None
    for vname in ("V1_stop", "V3_stop_skip", "V0_base"):
        for K in KGRID:
            r = sweep[vname][K]
            if r["p_survive_252"] >= 0.60 and r["E_wd"] > 0:
                if best is None or r["E_net"] > best[2]:
                    best = (vname, K, r["E_net"], r["p_survive_252"])
    res["funded_viable_candidate"] = (None if best is None else
                                      dict(variant=best[0], K=best[1], E_net=best[2], p_survive_252=best[3]))
    print("\n=== funded-viable (p_survive_252>=0.60 AND E[wd]>0) ===")
    print(f"  {'NONE' if best is None else best}")

    (OUT / "q4_funded.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q4_funded.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
