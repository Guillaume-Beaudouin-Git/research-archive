"""Q2 — SOYBEAN standalone survival under FTMO 2-step gates.

Sweep K x {V0 baseline, V1 stop -2.5%, V2 skip-USDA, V3 stop+skip} via the validated soy_fp
(lean first-passage; |Δ|<=0 vs bar engine). Triplet (p_funded, attempts, EV) + p_bust +
IS/OOS + intraday-low distribution + the daily-barrier pierce probability from soybean's own
intraday low (the skew -1.9 point). firstpassage.py close-to-close cross-check. Spread {1.5,2,3}bp
+ 26bp "FTMO CFD reality" check. Reuses soy_inject (bar engine for EV/funded), soy_stop, soy_fp.
"""
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soy_inject as SI
import soy_stop as STOP
import soy_fp as FP
V, C22, E = SI.V, SI.C22, SI.E
sys.path.insert(0, str(Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/"
                            "program_2026-06/ftmo_portfolio_audit/code")))
import firstpassage as FPB                       # noqa: E402

OUT = HERE.parent / "results"
KGRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
VARIANTS = {"V0_base": dict(X=None, skip_usda=False),
            "V1_stop": dict(X=0.025, skip_usda=False),
            "V2_skipUSDA": dict(X=None, skip_usda=True),
            "V3_stop_skip": dict(X=0.025, skip_usda=True)}
FEE = 96.0


def funded_value_standalone(M, WT0, ON0, K, X, skip, spread, fstarts):
    """Standalone (book off) funded value over funded cohorts where soy is active."""
    net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=X, skip_usda=skip, spread_bps=spread)
    SI.set_soy(M, net, low, traded)
    cfg = dict(C22.CFG_FUNDED, on_w=0.0, orb_risk=0.0, soy_on=True, soy_lev=1.0)
    vals = []
    for i0 in fstarts:
        r = V.run_funded(M, int(i0), WT0, ON0, cfg, horizon=C22.FUNDED_HORIZON,
                         wd_every=C22.FUNDED_WD_EVERY)
        vals.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
    SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
    return float(np.mean(vals)) + FEE


def main():
    t0 = time.time()
    SPREAD = 2.0
    M = SI.load_soy_stack(spread_bps=SPREAD)
    dates = M["dates_idx"]
    WT0, ON0 = SI.book_off_signals(M)
    starts = {w: V.starts(M, lo, hi, C22.COHORT_STEP) for w, lo, hi in C22.WINDOWS}
    all_starts = np.concatenate([starts["IS"], starts["OOS"]])
    # funded cohorts restricted to soy-active OOS window (soy starts 2018; IS 2013-17 has none)
    fstarts = V.starts(M, "2020-01-02", "2024-06-30", C22.FUNDED_STEP)

    res = {"spread_primary_bp": SPREAD, "n_cohorts": len(all_starts)}

    # ---------- daily-barrier pierce from soybean's own intraday low (skew -1.9 point) ----------
    a = STOP.base(SPREAD)[1]                       # low_frac (per K=1 unit)
    pierce = {}
    for K in KGRID:
        lowK = K * a
        pierce[K] = dict(p_low_lt_5pct=round(float((lowK < -0.05).mean()), 4),
                         p_low_lt_3pct=round(float((lowK < -0.03).mean()), 4),
                         worst_low_pct=round(float(lowK.min() * 100), 2),
                         p1_low_pct=round(float(np.percentile(lowK, 1) * 100), 2))
    res["intraday_low_vs_daily5"] = pierce
    print("=== intraday-low pierce of daily -5% (soybean leg alone, no stop) ===")
    for K in KGRID:
        print(f"  K={K}: P(low<-5%)={pierce[K]['p_low_lt_5pct']*100:.1f}%  "
              f"worst low {pierce[K]['worst_low_pct']:.1f}%  p1 {pierce[K]['p1_low_pct']:.1f}%")

    # ---------- (2) sweep K x variants ----------
    sweep = {}
    print(f"\n=== Q2 SWEEP soy_fp @ {SPREAD}bp (pooled / IS / OOS) ===")
    print(f"{'variant':<14}{'K':>4} {'pFund':>7}{'IS':>6}{'OOS':>6} {'att':>5} {'pBust':>7}"
          f"{'pBd':>6}{'pBf':>6} {'medT':>5} {'ddp5':>7}{'ddwst':>7}{'vol%':>6}")
    for vname, vk in VARIANTS.items():
        sweep[vname] = {}
        for K in KGRID:
            net, low, traded, diag = SI.build_soy_arrays(M, K=K, spread_bps=SPREAD, **vk)
            tr = traded.astype(bool)
            pooled = FP.cohort_run(net, low, tr, dates, all_starts)
            is_s = FP.cohort_run(net, low, tr, dates, starts["IS"])
            oos = FP.cohort_run(net, low, tr, dates, starts["OOS"])
            dd = pooled["min_eq_pct"]
            # account vol from the K-scaled traded-day net
            nz = net[net != 0]
            rec = dict(K=K, p_funded=round(pooled["p_funded"], 4),
                       p_is=round(is_s["p_funded"], 4), p_oos=round(oos["p_funded"], 4),
                       attempts=round(pooled["attempts_mean"], 2),
                       p_bust=round(pooled["p_bust_per_attempt"], 4),
                       p_bust_daily=round(pooled["p_bust_daily"], 4),
                       p_bust_floor=round(pooled["p_bust_floor"], 4),
                       med_t=None if np.isnan(pooled["med_t"]) else round(pooled["med_t"], 0),
                       dd_p5=round(float(np.percentile(dd, 5)), 2),
                       dd_worst=round(float(dd.min()), 2),
                       acct_vol_pct=round(float(nz.std() * np.sqrt(252) * 100), 1),
                       trig_frac=round(diag["trig_frac"], 4), n_skip=diag["n_skip"])
            sweep[vname][K] = rec
            print(f"{vname:<14}{K:>4} {rec['p_funded']*100:>6.1f}%{rec['p_is']*100:>5.1f}%"
                  f"{rec['p_oos']*100:>5.1f}% {rec['attempts']:>5.2f} {rec['p_bust']*100:>6.1f}%"
                  f"{rec['p_bust_daily']*100:>5.1f}%{rec['p_bust_floor']*100:>5.1f}% "
                  f"{str(rec['med_t']):>5} {rec['dd_p5']:>7.1f}{rec['dd_worst']:>7.1f}"
                  f"{rec['acct_vol_pct']:>6.1f}")
    res["sweep"] = sweep

    # ---------- (3) EV triplet for best-K per variant ----------
    print("\n=== EV triplet (best-K per variant; standalone funded over OOS soy-active) ===")
    ev = {}
    for vname, vk in VARIANTS.items():
        bestK = max(KGRID, key=lambda k: sweep[vname][k]["p_funded"])
        p = sweep[vname][bestK]["p_funded"]; at = sweep[vname][bestK]["attempts"]
        fv = funded_value_standalone(M, WT0, ON0, bestK, vk["X"], vk["skip_usda"], SPREAD, fstarts)
        EV = p * fv - at * FEE
        ev[vname] = dict(bestK=bestK, p_funded=round(p, 4), attempts=at,
                         funded_value=round(fv, 0), EV=round(EV, 0))
        print(f"  {vname:<14} K={bestK}: p {p*100:.1f}%  att {at:.2f}  fundedV ${fv:.0f}  EV ${EV:.0f}")
    res["ev_bestK"] = ev

    # ---------- (4) firstpassage close-to-close cross-check (V0, optimistic) ----------
    print("\n=== firstpassage cross-check (V0, close-to-close, optimistic bound) ===")
    base_net = STOP.base(SPREAD)[0].to_numpy(float)
    fpb = {}
    for K in [1.5, 3.0, 4.0]:
        r = FPB.cdf_sequential(base_net, lev=K, horizons=[63, None], n_paths=20000, cap=378)
        fpb[K] = dict(p_63td=round(r[63], 4), p_terminal=round(r["terminal"], 4),
                      med_days=None if r["_median_days_passers"] is None else round(r["_median_days_passers"], 0))
        print(f"  K={K}: p(funded<=63td) {r[63]*100:.1f}%  terminal {r['terminal']*100:.1f}%  med_days {fpb[K]['med_days']}")
    res["firstpassage_v0"] = fpb

    # ---------- (5) spread sensitivity (V3) + 26bp reality ----------
    print("\n=== spread sensitivity (V3 stop+skip, best-K) + 26bp FTMO CFD reality ===")
    spread_sens = {}
    bestK_v3 = ev["V3_stop_skip"]["bestK"]
    for sp in [1.5, 2.0, 3.0, 26.0]:
        net, low, traded, _ = SI.build_soy_arrays(M, K=bestK_v3, X=0.025, skip_usda=True, spread_bps=sp)
        r = FP.cohort_run(net, low, traded.astype(bool), dates, all_starts)
        spread_sens[sp] = dict(p_funded=round(r["p_funded"], 4), attempts=round(r["attempts_mean"], 2),
                               p_bust=round(r["p_bust_per_attempt"], 4))
        tag = "  <- FTMO CFD reality (per candidates.py)" if sp == 26 else ""
        print(f"  spread {sp:4.1f}bp (V3,K={bestK_v3}): p_funded {r['p_funded']*100:.1f}%  "
              f"att {r['attempts_mean']:.2f}  bust {r['p_bust_per_attempt']*100:.1f}%{tag}")
    res["spread_sensitivity_v3"] = spread_sens

    (OUT / "q2_standalone.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q2_standalone.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
