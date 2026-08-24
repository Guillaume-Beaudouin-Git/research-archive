"""Basket wrapper validation (MUST pass before any Q2 number is trusted).
(ii) book ON + basket OFF -> reproduces canonical pooled 0.87 -> non-invasive.
(iii) basket_fp (book off, basket on) == bar engine (book off, basket on), |Δ| <= 0.5pt at K=1.5,3.0.
(iv) same-day alignment: basket exit-morning index intersects book dates.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import basket_inject as BI
import basket_series as BS
import basket_fp as FP
V, C22, E = BI.V, BI.C22, BI.E
SLEEVES = ("GOLD", "SILVER", "WTI")


def main():
    M = BI.load_basket_stack()
    dates = M["dates_idx"]
    starts = {w: V.starts(M, lo, hi, C22.COHORT_STEP) for w, lo, hi in C22.WINDOWS}
    all_starts = np.concatenate([starts["IS"], starts["OOS"]])
    print(f"cohorts: IS {len(starts['IS'])} + OOS {len(starts['OOS'])} = {len(all_starts)}")

    # (iv) alignment
    d = BS.build(SLEEVES, 2.0)
    bd = pd.DatetimeIndex(M["dates"])
    inter = d.index.intersection(bd)
    print(f"(iv) basket exit-morning ∩ book dates: {len(inter)}/{len(d)} ({len(inter)/len(d)*100:.1f}%) same-day")

    # (ii) book ON, basket OFF -> 0.87
    WT, ON = E.align_signals(M, *E.build_signals())
    cfg_book = dict(C22.CFG_CHALLENGE)
    p_book = float(np.mean([V.run_funnel(M, int(i0), WT, ON, cfg_book, wall=C22.WALL)["funded"] for i0 in all_starts]))
    print(f"(ii) book ON + basket OFF pooled p_funded = {p_book*100:.2f}%  accept[86,91] -> {'PASS' if 0.86<=p_book<=0.91 else 'FAIL'}")

    # (iii) basket_fp vs bar engine (book off, basket on)
    WT0, ON0 = BI.book_off_signals(M)
    print("(iii) basket_fp vs bar engine (book off, B3 basket on):")
    ok = True
    for K in (1.5, 3.0):
        net, low, traded, _ = BI.build_basket_arrays(M, SLEEVES, K=K, X=None, spread_bps=2.0)
        st = FP.cohort_run(net, low, traded.astype(bool), dates, all_starts)
        BI.set_basket(M, net, low, traded)
        cfg = dict(C22.CFG_CHALLENGE, on_w=0.0, orb_risk=0.0, micro_orb=False, basket_on=True, basket_lev=1.0)
        p_bar = float(np.mean([V.run_funnel(M, int(i0), WT0, ON0, cfg, wall=C22.WALL)["funded"] for i0 in all_starts]))
        diff = abs(st["p_funded"] - p_bar) * 100
        ok = ok and diff <= 0.5
        print(f"  K={K}: basket_fp {st['p_funded']*100:5.1f}%  bar {p_bar*100:5.1f}%  |Δ| {diff:.2f}pt  {'PASS' if diff<=0.5 else 'FAIL'}")
        BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
    print(f"\nVALIDATION: (ii) {'PASS' if 0.86<=p_book<=0.91 else 'FAIL'} | (iii) {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
