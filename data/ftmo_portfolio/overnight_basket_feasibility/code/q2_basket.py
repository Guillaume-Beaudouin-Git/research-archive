"""Q2 — the overnight BASKET vs FTMO 2-step gates (the real question).

CHALLENGE: B3/B4/B2/B3+stop x K via basket_fp -> p_pass/IS/OOS/attempts/bust + intraday-low dist.
  (does the reduced drawdown reach +10% fast enough? or does lower vol make it SLOWER?)
EV triplet per config. FUNDED ABLATION (DECISIVE): book vs book+basket -> challenge p_funded +
  funded survival-12m + extraction + min-balance. Does the -3.5%-DD basket beat the dilution that
  killed the solos (gold/soybean crashed book funded 100->43-72%), or is it still dilutive?
Spread 2 vs 3 bp. Reuses basket_inject (bar engine), basket_fp, basket_series.
"""
import json, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import basket_inject as BI
import basket_fp as FP
V, C22, E = BI.V, BI.C22, BI.E
OUT = HERE.parent / "results"
KGRID = [1.0, 2.0, 3.0, 4.0]
SPREAD = 2.0
FEE = 96.0
CONFIGS = {
    "B3_gsw":   dict(sleeves=("GOLD", "SILVER", "WTI"), X=None),
    "B4_gsws":  dict(sleeves=("GOLD", "SILVER", "WTI", "SOYBEAN"), X=None),
    "B2_sw":    dict(sleeves=("SILVER", "WTI"), X=None),
    "B3_stop":  dict(sleeves=("GOLD", "SILVER", "WTI"), X=0.025),
}


def main():
    t0 = time.time()
    M = BI.load_basket_stack()
    dates = M["dates_idx"]
    WT0, ON0 = BI.book_off_signals(M)
    WT, ON = E.align_signals(M, *E.build_signals())
    starts = {w: V.starts(M, lo, hi, C22.COHORT_STEP) for w, lo, hi in C22.WINDOWS}
    all_starts = np.concatenate([starts["IS"], starts["OOS"]])
    fstarts = V.starts(M, "2018-06-01", "2024-06-30", C22.FUNDED_STEP)
    res = {"spread_bp": SPREAD, "n_cohorts": len(all_starts), "n_funded_cohorts": len(fstarts)}

    # ---------- (1) challenge sweep ----------
    sweep = {}
    print(f"=== Q2 CHALLENGE sweep @ {SPREAD}bp (basket_fp) ===")
    print(f"{'config':<10}{'K':>4} {'pPass':>7}{'IS':>6}{'OOS':>6} {'att':>5} {'bust':>6}{'bD':>5}{'bF':>5}"
          f"{'medT':>5} {'ddp5':>7}{'lowWorst%':>9}{'vol%':>6}")
    for cname, c in CONFIGS.items():
        sweep[cname] = {}
        for K in KGRID:
            net, low, traded, d = BI.build_basket_arrays(M, c["sleeves"], K=K, X=c["X"], spread_bps=SPREAD)
            tr = traded.astype(bool)
            pooled = FP.cohort_run(net, low, tr, dates, all_starts)
            iss = FP.cohort_run(net, low, tr, dates, starts["IS"])
            oos = FP.cohort_run(net, low, tr, dates, starts["OOS"])
            dd = pooled["min_eq_pct"]; nz = net[net != 0]
            rec = dict(K=K, p_pass=round(pooled["p_funded"], 4), p_is=round(iss["p_funded"], 4),
                       p_oos=round(oos["p_funded"], 4), attempts=round(pooled["attempts_mean"], 2),
                       bust=round(pooled["p_bust_per_attempt"], 4),
                       bust_daily=round(pooled["p_bust_daily"], 4), bust_floor=round(pooled["p_bust_floor"], 4),
                       med_t=None if np.isnan(pooled["med_t"]) else round(pooled["med_t"], 0),
                       dd_p5=round(float(np.percentile(dd, 5)), 2),
                       low_worst=round(float(d["basket_low"].min() * K * 100), 2),
                       vol=round(float(nz.std() * np.sqrt(252) * 100), 1))
            sweep[cname][K] = rec
            print(f"{cname:<10}{K:>4} {rec['p_pass']*100:>6.1f}%{rec['p_is']*100:>5.1f}%{rec['p_oos']*100:>5.1f}%"
                  f" {rec['attempts']:>5.2f} {rec['bust']*100:>5.1f}%{rec['bust_daily']*100:>4.1f}%{rec['bust_floor']*100:>4.1f}%"
                  f" {str(rec['med_t']):>5} {rec['dd_p5']:>7.1f}{rec['low_worst']:>9.1f}{rec['vol']:>6.1f}")
    res["challenge_sweep"] = sweep
    chal_max = max(sweep[c][K]["p_pass"] for c in CONFIGS for K in KGRID)
    print(f"  -> CHALLENGE max p_pass across all configs/K = {chal_max*100:.1f}% (gate 0.50 / floor 0.30)")

    # ---------- (2) funded value (standalone, for EV) ----------
    def funded_value_standalone(sleeves, K, X):
        net, low, traded, _ = BI.build_basket_arrays(M, sleeves, K=K, X=X, spread_bps=SPREAD)
        BI.set_basket(M, net, low, traded)
        cfg = dict(C22.CFG_FUNDED, on_w=0.0, orb_risk=0.0, basket_on=True, basket_lev=1.0)
        vals = [(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
                for r in (V.run_funded(M, int(i0), WT0, ON0, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY) for i0 in fstarts)]
        BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        return float(np.mean(vals)) + FEE

    print("\n=== EV triplet (best-K per config; standalone) ===")
    ev = {}
    for cname, c in CONFIGS.items():
        bestK = max(KGRID, key=lambda k: sweep[cname][k]["p_pass"])
        p = sweep[cname][bestK]["p_pass"]; at = sweep[cname][bestK]["attempts"]
        fv = funded_value_standalone(c["sleeves"], bestK, c["X"])
        EV = p * fv - at * FEE
        ev[cname] = dict(bestK=bestK, p_pass=round(p, 4), attempts=at, funded_value=round(fv, 0), EV=round(EV, 0))
        print(f"  {cname:<10} K={bestK}: p {p*100:.1f}%  att {at:.2f}  fundedV ${fv:.0f}  EV ${EV:.0f}")
    res["ev_bestK"] = ev

    # ---------- (3) FUNDED ABLATION (decisive): book vs book+basket ----------
    def book_chal(basket_on, sleeves, K):
        if basket_on:
            net, low, traded, _ = BI.build_basket_arrays(M, sleeves, K=K, X=None, spread_bps=SPREAD)
            BI.set_basket(M, net, low, traded)
        cfg = dict(C22.CFG_CHALLENGE, basket_on=basket_on, basket_lev=1.0)
        f = np.mean([V.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)["funded"] for i0 in all_starts])
        if basket_on: BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        return float(f)

    def book_fund(basket_on, sleeves, K):
        if basket_on:
            net, low, traded, _ = BI.build_basket_arrays(M, sleeves, K=K, X=None, spread_bps=SPREAD)
            BI.set_basket(M, net, low, traded)
        cfg = dict(C22.CFG_FUNDED, basket_on=basket_on, basket_lev=1.0)
        lives, wds, mineq = [], [], []
        for i0 in fstarts:
            r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
            lives.append(r["life"]); wds.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
        if basket_on: BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        lives = np.array(lives)
        return float((lives >= 252).mean()), float(np.mean(wds)) + FEE

    print("\n=== (3) FUNDED ABLATION — book vs book+basket (DECISIVE) ===")
    p0 = book_chal(False, None, 0); s0, fv0 = book_fund(False, None, 0)
    print(f"  book_only: challenge {p0*100:.2f}%  funded_survive252 {s0*100:.1f}%  fundedV ${fv0:.0f}")
    abl = {"book_only": dict(challenge=round(p0, 4), survive252=round(s0, 4), funded_value=round(fv0, 0))}
    for cname in ("B3_gsw", "B4_gsws"):
        sleeves = CONFIGS[cname]["sleeves"]
        for K in (1.0, 2.0, 3.0):
            p = book_chal(True, sleeves, K); s, fv = book_fund(True, sleeves, K)
            abl[f"{cname}_K{K}"] = dict(challenge=round(p, 4), d_chal=round(p - p0, 4),
                                        survive252=round(s, 4), d_surv=round(s - s0, 4), funded_value=round(fv, 0))
            print(f"  book+{cname} K={K}: challenge {p*100:.2f}% (Δ{(p-p0)*100:+.2f})  "
                  f"survive252 {s*100:.1f}% (book {s0*100:.0f}, Δ{(s-s0)*100:+.1f})  fundedV ${fv:.0f}")
    res["funded_ablation"] = abl

    (OUT / "q2_basket.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q2_basket.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
