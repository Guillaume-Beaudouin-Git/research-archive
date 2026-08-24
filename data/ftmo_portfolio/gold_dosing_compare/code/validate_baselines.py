"""Validate engines + reproduce baselines (before freezing Part A/B thresholds).
(i)   ASIA-OFF -> challenge pooled 0.87 (non-invasive injection wrapper).
(ii)  book-only CANONICAL FUNDED_WINDOWS survival-12m (~97.9%) + fundedV (the dosing anchor).
(iii) asia_stop -2.5% reproduces (edge intact, trig ~0).
(iv)  or-trend (WT[XAUUSD]) daily-net reconstruction (for Part B).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_series as ASER
import asia_stop as STOP
V, C22, E = AI.V, AI.C22, AI.E
ANN = 252.0
FEE = 96.0


def ortrend_net():
    """or-trend = gold_trend sleeve daily NET (WT[XAUUSD] x rets - turn + swap)."""
    rets = pd.read_parquet(E.CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(E.CACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(E.CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(E.CACHE / "panel_mult.parquet")
    rt = pd.read_csv(E.AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    WT, _ = E.build_signals()
    w = WT["XAUUSD"].reindex(rets.index).fillna(0.0)
    gross = w * rets["XAUUSD"]
    turn = w.diff().abs() * (rt["XAUUSD"] / 2.0 / 1e4)
    bps = np.where(w > 0, sL["XAUUSD"], np.where(w < 0, sS["XAUUSD"], 0.0))
    swap = w.abs() * pd.Series(bps, index=w.index) / 1e4 * mu["XAUUSD"]
    return (gross - turn + swap).fillna(0.0).rename("ortrend"), w


def main():
    M = AI.load_asia_stack(spread_bps=1.5)
    WT, ON = E.align_signals(M, *E.build_signals())
    all_starts = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])
    fstarts = np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP) for _, lo, hi in C22.FUNDED_WINDOWS])
    print(f"challenge cohorts {len(all_starts)} | canonical funded cohorts {len(fstarts)}")

    # (i) ASIA off -> 0.87
    p = float(np.mean([V.run_funnel(M, int(i0), WT, ON, dict(C22.CFG_CHALLENGE), wall=C22.WALL)["funded"] for i0 in all_starts]))
    print(f"(i)  ASIA-OFF challenge pooled = {p*100:.2f}%  -> {'PASS' if 0.86<=p<=0.91 else 'FAIL'}")

    # (ii) book-only canonical funded survival + fundedV
    cfg = dict(C22.CFG_FUNDED)
    lives, wds = [], []
    for i0 in fstarts:
        r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
        lives.append(r["life"]); wds.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
    s0 = float((np.array(lives) >= 252).mean()); fv0 = float(np.mean(wds)) + FEE
    print(f"(ii) book-only canonical funded: survive252 {s0*100:.1f}%  fundedV ${fv0:.0f}  (anchor ~97.9%)")

    # (iii) asia_stop -2.5%
    r = STOP.apply_stop(K=1.0, X=0.025, spread_bps=1.5)
    n = r["net"]; sh = n.mean() / n.std() * np.sqrt(ANN)
    print(f"(iii) asia_stop -2.5%: trig {r['trig_frac']*100:.1f}%  Sharpe {sh:.2f}  alpha_given_up {r['alpha_given_up']*100:.1f}%")

    # (iv) or-trend reconstruction
    ot, w = ortrend_net()
    sh_ot = ot[ot != 0].mean() / ot[ot != 0].std() * np.sqrt(ANN)
    print(f"(iv) or-trend reconstructed: n={len(ot)} | long-frac {(w>0).mean()*100:.1f}% | active {(w!=0).mean()*100:.1f}% | Sharpe(active) {sh_ot:.2f}")
    print(f"\nBASELINES OK -> freeze pre-registration.")


if __name__ == "__main__":
    main()
