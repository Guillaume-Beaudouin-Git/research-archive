"""Wrapper validation (MUST pass before any Q2 number is trusted). Mirrors asia validate.

(i)  soy_series.net_log == net_analysis.py net()  [done in soy_series; printed here]
(ii) book ON + soy OFF -> reproduces canonical pooled 0.87 (accept [0.86,0.91]) -> non-invasive
(iii) soy_fp (book off, soy on) == bar engine (book off, soy on), |Δ| <= 0.5pt on K in {1.5,3.0}
"""
import sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soy_inject as SI
import soy_series as SS
import soy_fp as FP
V, C22, E = SI.V, SI.C22, SI.E


def main():
    t0 = time.time()
    M = SI.load_soy_stack(spread_bps=2.0)
    dates = M["dates_idx"]
    starts = {w: V.starts(M, lo, hi, C22.COHORT_STEP) for w, lo, hi in C22.WINDOWS}
    all_starts = np.concatenate([starts["IS"], starts["OOS"]])
    print(f"cohorts: IS {len(starts['IS'])} + OOS {len(starts['OOS'])} = {len(all_starts)}")

    # (i) series check
    d = SS.build(2.0)
    print(f"\n(i)  soy_series verify_err = {d.attrs['verify_err']:.2e}  (==0 => net_log==net_analysis)")

    # (ii) book ON, soy OFF -> 0.87
    WT_df, ON_df = E.build_signals()
    WT, ON = E.align_signals(M, WT_df, ON_df)
    cfg_book = dict(C22.CFG_CHALLENGE)                 # soy_on absent => injection skipped
    fu = [V.run_funnel(M, int(i0), WT, ON, cfg_book, wall=C22.WALL)["funded"] for i0 in all_starts]
    p_book = float(np.mean(fu))
    ok2 = 0.86 <= p_book <= 0.91
    print(f"(ii) book ON + soy OFF pooled p_funded = {p_book*100:.2f}%  accept[86,91] -> {'PASS' if ok2 else 'FAIL'}")

    # (iii) soy_fp vs bar engine (book off, soy on)
    WT0, ON0 = SI.book_off_signals(M)
    print("\n(iii) soy_fp vs bar engine (book off, soy on), baseline V0:")
    val = {}
    for K in (1.5, 3.0):
        net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=None, skip_usda=False, spread_bps=2.0)
        st_fp = FP.cohort_run(net, low, traded.astype(bool), dates, all_starts)
        SI.set_soy(M, net, low, traded)
        cfg = dict(C22.CFG_CHALLENGE, on_w=0.0, orb_risk=0.0, micro_orb=False,
                   soy_on=True, soy_lev=1.0)
        fub = [V.run_funnel(M, int(i0), WT0, ON0, cfg, wall=C22.WALL)["funded"] for i0 in all_starts]
        p_bar = float(np.mean(fub))
        diff = abs(st_fp["p_funded"] - p_bar) * 100
        val[K] = (st_fp["p_funded"], p_bar, diff)
        print(f"  K={K}: soy_fp {st_fp['p_funded']*100:5.1f}%  bar {p_bar*100:5.1f}%  |Δ| {diff:.2f}pt"
              f"  {'PASS' if diff <= 0.5 else 'FAIL'}")
        SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))   # reset

    ok3 = all(v[2] <= 0.5 for v in val.values())
    print(f"\nVALIDATION: (ii) {'PASS' if ok2 else 'FAIL'} | (iii) {'PASS' if ok3 else 'FAIL'} "
          f"| [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
