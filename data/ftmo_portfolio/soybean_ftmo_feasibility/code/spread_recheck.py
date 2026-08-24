"""Spread re-check (user's real FTMO SOYBEAN.c measurement = <=3 bp, NOT 26 bp).

Re-run the decisive triplets at spread = {2.0, 3.0} bp side-by-side: standalone challenge
(soy_fp), standalone funded (run_funded, V1 stop), and the book ablation (challenge + funded).
Answers: does the verdict change on the spread axis, and is it spread-INDEPENDENT?
Read-only; reuses soy_inject / soy_fp.
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soy_inject as SI
import soy_fp as FP
V, C22, E = SI.V, SI.C22, SI.E

KGRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
FEE = 96.0


def run_for_spread(SPREAD):
    M = SI.load_soy_stack(spread_bps=SPREAD)
    dates = M["dates_idx"]
    WT, ON = E.align_signals(M, *E.build_signals())
    WT0, ON0 = SI.book_off_signals(M)
    starts_all = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])
    fstarts = V.starts(M, "2018-06-01", "2024-06-30", C22.FUNDED_STEP)

    print(f"\n================= SPREAD = {SPREAD} bp =================")

    # --- standalone challenge: V0 + V1(stop), max p_funded ---
    print("standalone challenge p_funded (soy_fp):")
    best = {}
    for vname, X in [("V0", None), ("V1_stop", 0.025)]:
        row = {}
        for K in KGRID:
            net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=X, skip_usda=False, spread_bps=SPREAD)
            r = FP.cohort_run(net, low, traded.astype(bool), dates, starts_all)
            row[K] = (r["p_funded"], r["p_bust_per_attempt"])
        best[vname] = max(row.items(), key=lambda kv: kv[1][0])
        print("  " + vname + ": " + "  ".join(f"K{K}:{row[K][0]*100:.1f}%" for K in KGRID)
              + f"   -> MAX {best[vname][1][0]*100:.1f}% (K={best[vname][0]}, bust {best[vname][1][1]*100:.0f}%)")
    chal_max = max(best['V0'][1][0], best['V1_stop'][1][0])

    # --- standalone funded V1(stop) ---
    print("standalone funded V1(stop) p_survive_252 / E[wd]:")
    cfg_f = dict(C22.CFG_FUNDED, on_w=0.0, orb_risk=0.0, soy_on=True, soy_lev=1.0)
    for K in (1.0, 2.0, 3.0):
        net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=0.025, skip_usda=False, spread_bps=SPREAD)
        SI.set_soy(M, net, low, traded)
        lives, wds = [], []
        for i0 in fstarts:
            r = V.run_funded(M, int(i0), WT0, ON0, cfg_f, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
            lives.append(r["life"]); wds.append(r["wd"] + r["residual"])
        SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        print(f"  K={K}: survive252 {np.mean(np.array(lives) >= 252)*100:.1f}%  E[net] ${np.mean(wds):.0f}")

    # --- book ablation: challenge p_funded + funded survival (V1 stop) ---
    def book_chal(soy_on, K):
        if soy_on:
            net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=0.025, skip_usda=False, spread_bps=SPREAD)
            SI.set_soy(M, net, low, traded)
        cfg = dict(C22.CFG_CHALLENGE, soy_on=soy_on, soy_lev=1.0)
        f = np.mean([V.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL)["funded"] for i0 in starts_all])
        if soy_on: SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        return float(f)

    def book_fund(soy_on, K):
        if soy_on:
            net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=0.025, skip_usda=False, spread_bps=SPREAD)
            SI.set_soy(M, net, low, traded)
        cfg = dict(C22.CFG_FUNDED, soy_on=soy_on, soy_lev=1.0)
        lives = [V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)["life"]
                 for i0 in fstarts]
        if soy_on: SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        return float(np.mean(np.array(lives) >= 252))

    print("book ablation (challenge p_funded | funded survive252):")
    p0 = book_chal(False, 0); s0 = book_fund(False, 0)
    print(f"  book_only: challenge {p0*100:.2f}%  funded252 {s0*100:.1f}%")
    for K in (1.0, 2.0, 3.0):
        p = book_chal(True, K); s = book_fund(True, K)
        print(f"  book+soy K={K}: challenge {p*100:.2f}% (Δ{(p-p0)*100:+.2f})  funded252 {s*100:.1f}% (book {s0*100:.0f})")
    return chal_max


if __name__ == "__main__":
    res = {}
    for sp in (2.0, 3.0):
        res[sp] = run_for_spread(sp)
    print("\n================= SUMMARY =================")
    for sp in (2.0, 3.0):
        print(f"  spread {sp}bp: standalone challenge MAX p_funded = {res[sp]*100:.1f}%  "
              f"(gate 0.30) -> {'PASS' if res[sp] >= 0.30 else 'FAIL'}")
