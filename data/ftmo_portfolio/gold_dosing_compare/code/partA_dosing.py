"""PART A — gold ASIA dose curve: does a net-positive dose at held survival exist?

Sweep dose d in {0.1,0.25,0.5,0.75,1.0} (x contributive K=1), stop -2.5% applied ONCE
(apply_stop(K=d) bakes dose+stop at -2.5% of ACCOUNT; inject with asia_lev=1.0 -> no double-K).
Canonical FUNDED_WINDOWS ablation (book vs book+ASIA_dose). Book-only anchor 97.9% / $1442.
Triplet (fundedV extraction, survive-12m, min-balance/bust) + Δ vs book. Curve dose->(Δsurv, Δextract).
Reuses asia_inject (run_funded), asia_stop, asia_series.
"""
import json, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_stop as STOP
import asia_series as ASER
V, C22, E = AI.V, AI.C22, AI.E
OUT = HERE.parent / "results"
INIT, FEE = 10000.0, 96.0
DOSES = [0.1, 0.25, 0.5, 0.75, 1.0]
STOPX = 0.025


def set_asia(M, s):
    M["asia_net"] = ASER.align_to_book(s["net"], M["dates_idx"])
    M["asia_low"] = ASER.align_to_book(s["low"], M["dates_idx"])


def funded_run(M, WT, ON, asia_on, fstarts):
    cfg = dict(C22.CFG_FUNDED, asia_on=asia_on, asia_lev=1.0)
    lives, wds, mineqs = [], [], []
    for i0 in fstarts:
        r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
        lives.append(r["life"]); wds.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
        mineqs.append(r.get("min_eq", np.nan))
    lives = np.array(lives)
    fv = float(np.mean(wds)) + FEE
    return dict(survive252=float((lives >= 252).mean()), fundedV=round(fv, 0),
                p_bust=float((lives < 252).mean()))


def main():
    t0 = time.time()
    M = AI.load_asia_stack(spread_bps=1.5)
    WT, ON = E.align_signals(M, *E.build_signals())
    WT0, ON0 = AI.book_off_signals(M)
    fstarts = np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP) for _, lo, hi in C22.FUNDED_WINDOWS])
    res = {"window": "canonical FUNDED_WINDOWS", "n_funded": len(fstarts), "stop_pct": STOPX * 100}

    b = funded_run(M, WT, ON, False, fstarts)
    s0, fv0 = b["survive252"], b["fundedV"]
    print(f"book-only (canonical, n={len(fstarts)}): survive252 {s0*100:.1f}%  fundedV ${fv0:.0f}")
    res["book_only"] = dict(survive252=round(s0, 4), fundedV=fv0)

    print(f"\n{'dose':>6}{'standaloneSurv':>15}{'book+ASIA surv':>15}{'Δsurv':>8}"
          f"{'fundedV':>9}{'Δextract':>10}{'net-positive?':>15}")
    curve = {}
    for d in DOSES:
        s = STOP.apply_stop(K=d, X=STOPX)          # dose + stop applied ONCE
        set_asia(M, s)
        # standalone (book off) survival for context
        sa = funded_run(M, WT0, ON0, True, fstarts)
        set_asia(M, s)                              # re-set (funded_run doesn't mutate, but be safe)
        bk = funded_run(M, WT, ON, True, fstarts)
        d_surv = bk["survive252"] - s0
        d_extract = bk["fundedV"] - fv0
        netpos = (d_surv >= -0.025) and (d_extract > 0)
        curve[d] = dict(standalone_surv=round(sa["survive252"], 4),
                        book_asia_surv=round(bk["survive252"], 4), d_surv=round(d_surv, 4),
                        fundedV=bk["fundedV"], d_extract=round(d_extract, 0),
                        trig_frac=round(s["trig_frac"], 4), net_positive=bool(netpos))
        print(f"{d:>6.2f}{sa['survive252']*100:>14.1f}%{bk['survive252']*100:>14.1f}%{d_surv*100:>+7.1f}"
              f"{bk['fundedV']:>9.0f}{d_extract:>+10.0f}{('YES' if netpos else 'no'):>15}")
        SI_reset = None
    res["dose_curve"] = curve

    # ---- verdict logic ----
    netpos_doses = [d for d in DOSES if curve[d]["net_positive"]]
    # dose where extraction first > 0, and dose where survival first < -2.5pt
    first_contrib = next((d for d in DOSES if curve[d]["d_extract"] > 0), None)
    first_dilute = next((d for d in DOSES if curve[d]["d_surv"] < -0.025), None)
    res["verdict"] = dict(
        net_positive_doses=netpos_doses,
        first_dose_contributing=first_contrib,
        first_dose_diluting=first_dilute,
        dosing_dilemma=(len(netpos_doses) == 0))
    print(f"\nnet-positive doses (Δsurv≥−2.5pt AND Δextract>0): {netpos_doses if netpos_doses else 'NONE'}")
    print(f"first dose that contributes (Δextract>0): {first_contrib} | first dose that dilutes (Δsurv<−2.5pt): {first_dilute}")
    print(f"VERDICT Part A: {'DOSING DILEMMA (no net-positive dose)' if not netpos_doses else 'NET-POSITIVE DOSE EXISTS: '+str(netpos_doses)}")

    (OUT / "partA_dosing.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten partA_dosing.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
