"""Q2 — ASIA_23_8 standalone survival under FTMO 2-step gates.

(1) VALIDATE the lean first-passage (asia_fp) against the AUDITED bar engine (book off).
(2) Sweep K x {V0,V2(MA100),V3(regime),V4(both)} -> triplet (p_funded, attempts, EV-proxy),
    p_bust, IS/OOS split, drawdown-under-constraint distribution.
(3) firstpassage.py cross-check (close-to-close block-bootstrap = optimistic bound).

Reuses: asia_inject (patched audited bar engine), asia_series, firstpassage.
"""
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_series as ASER
import asia_fp as FP
V, C22, E = AI.V, AI.C22, AI.E
sys.path.insert(0, str(Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/"
                            "program_2026-06/ftmo_portfolio_audit/code")))
import firstpassage as FPB                       # noqa: E402

OUT = HERE.parent / "results"
KGRID = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]


def build_variant_arrays(M, regime=False, ma100=False, spread=1.5):
    a = ASER.build(spread_bps=spread)
    net, low = a["net_simple"].copy(), a["low_frac"].copy()
    scale = pd.Series(1.0, index=a.index)
    if ma100:
        eq = (1 + a["net_simple"]).cumprod()
        scale *= (eq > eq.rolling(100).mean()).astype(float).replace(0.0, 0.4).shift(1).fillna(1.0)
    if regime:
        drift = a["raw_log"].rolling(252).sum().shift(1)
        scale *= (drift > 0).astype(float).fillna(0.0)
    net, low = net * scale, low * scale
    bd = M["dates_idx"]
    return (ASER.align_to_book(net, bd), ASER.align_to_book(low, bd),
            a, scale)


def bar_standalone(M, WT0, ON0, K, net_arr, low_arr):
    """Audited bar engine, book OFF, ASIA on -> pooled p_funded (validation)."""
    M["asia_net"], M["asia_low"] = net_arr, low_arr
    cfg = dict(C22.CFG_CHALLENGE, on_w=0.0, orb_risk=0.0, micro_orb=False,
               asia_on=True, asia_lev=K)
    fu = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
            r = V.run_funnel(M, int(i0), WT0, ON0, cfg, wall=C22.WALL)
            fu.append(r["funded"])
    return float(np.mean(fu))


def main():
    t0 = time.time()
    M = AI.load_asia_stack(spread_bps=1.5)
    dates = M["dates_idx"]
    WT0, ON0 = AI.book_off_signals(M)
    starts = {win: V.starts(M, lo, hi, C22.COHORT_STEP) for win, lo, hi in C22.WINDOWS}
    all_starts = np.concatenate([starts["IS"], starts["OOS"]])

    # base (V0) arrays
    netV0, lowV0, a0, _ = build_variant_arrays(M)
    traded = (netV0 != 0).astype(bool)

    # ---------- (1) validation: asia_fp vs bar engine (book off) ----------
    print("=== VALIDATION asia_fp vs audited bar engine (book off) ===")
    val = {}
    for K in (1.5, 3.0):
        st_fp = FP.cohort_run(netV0 * K, lowV0 * K, traded, dates, all_starts)
        # bar engine: asia_net is the per-day return; K applied via asia_lev
        M["asia_net"], M["asia_low"] = netV0, lowV0
        cfg = dict(C22.CFG_CHALLENGE, on_w=0.0, orb_risk=0.0, micro_orb=False,
                   asia_on=True, asia_lev=K)
        fu = [V.run_funnel(M, int(i0), WT0, ON0, cfg, wall=C22.WALL)["funded"]
              for i0 in all_starts]
        p_bar = float(np.mean(fu))
        val[K] = dict(fp=round(st_fp["p_funded"], 4), bar=round(p_bar, 4),
                      diff=round(abs(st_fp["p_funded"] - p_bar), 4))
        print(f"  K={K}: asia_fp {st_fp['p_funded']*100:.1f}%  bar {p_bar*100:.1f}%  "
              f"|Δ| {abs(st_fp['p_funded']-p_bar)*100:.1f}pt")

    # ---------- (2) sweep K x variants ----------
    variants = {"V0_baseline": dict(regime=False, ma100=False),
                "V2_ma100": dict(regime=False, ma100=True),
                "V3_regime": dict(regime=True, ma100=False),
                "V4_both": dict(regime=True, ma100=True)}
    sweep = {}
    print("\n=== Q2 SWEEP (asia_fp, pooled / IS / OOS) ===")
    print(f"{'variant':<14}{'K':>4} {'pFund':>7}{'IS':>7}{'OOS':>7} {'att':>5} "
          f"{'pBust':>7} {'medT':>5} {'p5DD%':>7}{'worstDD%':>9}")
    for vname, vk in variants.items():
        netb, lowb, _, scale = build_variant_arrays(M, **vk)
        tr = (netb != 0).astype(bool)
        sweep[vname] = {}
        for K in KGRID:
            pooled = FP.cohort_run(netb * K, lowb * K, tr, dates, all_starts)
            is_s = FP.cohort_run(netb * K, lowb * K, tr, dates, starts["IS"])
            oos_s = FP.cohort_run(netb * K, lowb * K, tr, dates, starts["OOS"])
            dd = pooled["min_eq_pct"]
            rec = dict(K=K, p_funded=round(pooled["p_funded"], 4),
                       p_is=round(is_s["p_funded"], 4), p_oos=round(oos_s["p_funded"], 4),
                       attempts=round(pooled["attempts_mean"], 2),
                       p_bust=round(pooled["p_bust_per_attempt"], 4),
                       p_bust_daily=round(pooled["p_bust_daily"], 4),
                       p_bust_floor=round(pooled["p_bust_floor"], 4),
                       med_t=None if np.isnan(pooled["med_t"]) else round(pooled["med_t"], 0),
                       dd_p5=round(float(np.percentile(dd, 5)), 2),
                       dd_worst=round(float(dd.min()), 2),
                       acct_vol_pct=round(float((netb[netb != 0]).std() * np.sqrt(258) * K * 100), 1))
            sweep[vname][K] = rec
            print(f"{vname:<14}{K:>4} {rec['p_funded']*100:>6.1f}%{rec['p_is']*100:>6.1f}%"
                  f"{rec['p_oos']*100:>6.1f}% {rec['attempts']:>5.2f} {rec['p_bust']*100:>6.1f}%"
                  f" {str(rec['med_t']):>5} {rec['dd_p5']:>7.1f}{rec['dd_worst']:>9.1f}")

    # ---------- (3) firstpassage cross-check (close-to-close, optimistic) ----------
    print("\n=== firstpassage.py cross-check (close-to-close, no intraday low) ===")
    fpb = {}
    series = a0["net_simple"].to_numpy(float)        # strategy daily net (aday-indexed)
    for K in KGRID:
        r = FPB.cdf_sequential(series, lev=K, horizons=[63, None], n_paths=20000, cap=378)
        fpb[K] = dict(p_63td=round(r[63], 4), p_terminal=round(r["terminal"], 4),
                      med_days=None if r["_median_days_passers"] is None
                      else round(r["_median_days_passers"], 0))
        print(f"  K={K}: p(funded<=63td) {r[63]*100:.1f}%  terminal {r['terminal']*100:.1f}%  "
              f"med_days {fpb[K]['med_days']}")

    res = dict(validation=val, sweep=sweep, firstpassage=fpb,
               note="asia_fp = lean standalone (intraday-low, $-additive, validated vs bar engine); "
                    "firstpassage = close-to-close block-bootstrap (optimistic bound)")
    (OUT / "q2_standalone.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q2_standalone.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
