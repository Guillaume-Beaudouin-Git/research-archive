"""Q2b — funded ablation on BOTH cohort windows (audit correction).

The headline Δ-6.8 used a non-canonical, soybean-favorable window (2018-06->2024-06). Re-run the
book-vs-book+basket funded ablation on the engine's CANONICAL FUNDED_WINDOWS (IS 2013-17 + OOS
2020-24) vs that window, to test whether the "aggregation reduces dilution" nuance is robust.
"""
import json, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import basket_inject as BI
V, C22, E = BI.V, BI.C22, BI.E
OUT = HERE.parent / "results"
FEE = 96.0


def main():
    M = BI.load_basket_stack()
    WT, ON = E.align_signals(M, *E.build_signals())
    windows = {
        "canonical_2013-17+2020-24": np.concatenate(
            [V.starts(M, lo, hi, C22.FUNDED_STEP) for _, lo, hi in C22.FUNDED_WINDOWS]),
        "soyfavorable_2018-2024": V.starts(M, "2018-06-01", "2024-06-30", C22.FUNDED_STEP),
    }

    def fund(basket_on, sleeves, K, fstarts):
        if basket_on:
            net, low, traded, _ = BI.build_basket_arrays(M, sleeves, K=K, X=None, spread_bps=2.0)
            BI.set_basket(M, net, low, traded)
        cfg = dict(C22.CFG_FUNDED, basket_on=basket_on, basket_lev=1.0)
        lives, wds = [], []
        for i0 in fstarts:
            r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
            lives.append(r["life"]); wds.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
        if basket_on: BI.set_basket(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        return float((np.array(lives) >= 252).mean()), float(np.mean(wds)) + FEE

    res = {}
    for wn, fs in windows.items():
        s0, fv0 = fund(False, None, 0, fs)
        print(f"\n=== {wn}  (n={len(fs)} cohorts) ===")
        print(f"  book_only: survive252 {s0*100:.1f}%  fundedV ${fv0:.0f}")
        res[wn] = {"book_only": dict(survive252=round(s0, 4), fundedV=round(fv0, 0)), "n": len(fs)}
        for cn, sl in [("B3", ("GOLD", "SILVER", "WTI")), ("B4", ("GOLD", "SILVER", "WTI", "SOYBEAN"))]:
            for K in (1.0, 2.0):
                s, fv = fund(True, sl, K, fs)
                res[wn][f"{cn}_K{K}"] = dict(survive252=round(s, 4), d_surv=round(s - s0, 4), fundedV=round(fv, 0))
                print(f"  book+{cn} K={K}: survive252 {s*100:.1f}% (Δ{(s-s0)*100:+.1f})  fundedV ${fv:.0f}")
    (OUT / "q2b_funded_windows.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwritten q2b_funded_windows.json")


if __name__ == "__main__":
    main()
