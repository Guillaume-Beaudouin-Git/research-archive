"""Q5 — SOYBEAN contribution to the REAL vm14 book (the report's central argument).

The report sells soybean as a regime-complement to GOLD-ASIA (strong 2018-21 = when gold-ASIA
was dead). But the live book has GOLD-TREND (TSMOM), J1 (USDJPY), nightly (GER40 overnight),
micro-ORB (US100) -- NO gold-ASIA sleeve. So:
(a) corr(soybean, real book trend = gold_trend + J1) vs corr(soybean, hypothetical gold-ASIA):
    does the announced complementarity transfer to the REAL book?  full/IS/OOS/2018-21/2022-25.
(b) ablation CHALLENGE: book vs book+soy (V1 stop), K sweep -> Δp_funded, Δattempts, ΔEV. Sanity 0.87.
(c) ablation FUNDED: book vs book+soy survival (the asia lesson: a benign-standalone sleeve can
    CRASH the book's funded survival). p_survive_252, E[wd].
(d) margin: soybean (separate commodity CFD) footprint + book metal under cap 60%.
Reuses soy_inject (engine + injection), cleanroom build_signals (book legs), asia_series (gold-ASIA).
"""
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import soy_inject as SI
import soy_series as SS
import soy_stop as STOP
V, C22, E = SI.V, SI.C22, SI.E
OUT = HERE.parent / "results"
SPREAD = 2.0
FEE = 96.0


def book_leg_returns():
    """Reconstruct gold_trend (WT XAU) and J1 (WT USDJPY) daily NET from cleanroom panels."""
    rets = pd.read_parquet(E.CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(E.CACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(E.CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(E.CACHE / "panel_mult.parquet")
    rt = pd.read_csv(E.AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    WT, _ = E.build_signals()
    out = {}
    for leg in ("XAUUSD", "USDJPY"):
        w = WT[leg].reindex(rets.index).fillna(0.0)
        gross = w * rets[leg]
        turn = w.diff().abs() * (rt[leg] / 2.0 / 1e4)
        bps = np.where(w > 0, sL[leg], np.where(w < 0, sS[leg], 0.0))
        swap = w.abs() * pd.Series(bps, index=w.index) / 1e4 * mu[leg]
        out[leg] = (gross - turn + swap).fillna(0.0)
    return out["XAUUSD"].rename("gold_trend"), out["USDJPY"].rename("J1")


def gold_asia_returns():
    """Hypothetical gold-ASIA sleeve daily net (the report's claimed complement). +1 shift to book day."""
    try:
        import importlib.util
        # prefer the branch-local (worktree) copy inherited from the asia fork; fall back to MAIN
        local = HERE.parent.parent / "asia_23_8_feasibility" / "code" / "asia_series.py"
        main = Path("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/"
                    "asia_23_8_feasibility/code/asia_series.py")
        p = local if local.exists() else main
        spec = importlib.util.spec_from_file_location("asia_series_main", p)
        ASER = importlib.util.module_from_spec(spec); spec.loader.exec_module(ASER)
        a = ASER.build(1.5)["net_simple"].copy()
        a.index = a.index + pd.Timedelta(days=1)             # asia exit-date = book day D+1
        return a.groupby(a.index.normalize()).sum().rename("gold_asia")
    except Exception as ex:
        print(f"  [gold-ASIA reconstruction unavailable: {ex}]")
        return None


def corr_block(df, lo=None, hi=None):
    d = df.copy()
    if lo is not None:
        d = d[d.index >= lo]
    if hi is not None:
        d = d[d.index <= hi]
    d = d.dropna()
    d = d[d["soy"] != 0.0]
    out = {"n": len(d)}
    for c in d.columns:
        if c == "soy":
            continue
        out[c] = dict(pearson=round(float(d["soy"].corr(d[c])), 3),
                      spearman=round(float(d["soy"].corr(d[c], method="spearman")), 3))
    return out


def main():
    t0 = time.time()
    M = SI.load_soy_stack(spread_bps=SPREAD)
    dates = M["dates_idx"]
    WT_df, ON_df = E.build_signals()
    WT, ON = E.align_signals(M, WT_df, ON_df)
    WT0, ON0 = SI.book_off_signals(M)
    res = {"spread_bp": SPREAD}

    # ---------- (a) correlation ----------
    soy = SS.build(SPREAD)["net_simple"].copy()
    soy = soy.groupby(soy.index.normalize()).sum().rename("soy")     # same-day book alignment
    gt, j1 = book_leg_returns()
    book_trend = (gt + j1).rename("book_trend")
    ga = gold_asia_returns()
    cols = [soy, gt, j1, book_trend] + ([ga] if ga is not None else [])
    df = pd.concat(cols, axis=1)
    regimes = {"full": (None, None), "IS_2013_19": (None, "2019-12-31"),
               "OOS_2020_26": ("2020-01-02", None),
               "soy_strong_2018_21": ("2018-01-01", "2021-12-31"),
               "soy_weak_2022_25": ("2022-01-01", "2025-12-31")}
    res["correlation"] = {k: corr_block(df, lo, hi) for k, (lo, hi) in regimes.items()}
    print("=== (a) correlation soybean vs real-book legs + hypothetical gold-ASIA ===")
    for k, v in res["correlation"].items():
        line = f"  {k:<20} n={v['n']:4d}"
        for c in ("book_trend", "gold_trend", "J1", "gold_asia"):
            if c in v:
                line += f" | {c} ρ={v[c]['pearson']:+.2f}"
        print(line)

    # ---------- (b) ablation CHALLENGE: book vs book+soy (V1 stop) ----------
    starts_all = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])
    fstarts = V.starts(M, "2018-06-01", "2024-06-30", C22.FUNDED_STEP)

    def challenge(soy_on, K):
        if soy_on:
            net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=0.025, skip_usda=False, spread_bps=SPREAD)
            SI.set_soy(M, net, low, traded)
        cfg = dict(C22.CFG_CHALLENGE, soy_on=soy_on, soy_lev=1.0)
        out = [V.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL) for i0 in starts_all]
        if soy_on:
            SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        f = np.array([o["funded"] for o in out]); at = np.array([o["attempts"] for o in out])
        return float(f.mean()), float(at.mean())

    def funded_book(soy_on, K):
        if soy_on:
            net, low, traded, _ = SI.build_soy_arrays(M, K=K, X=0.025, skip_usda=False, spread_bps=SPREAD)
            SI.set_soy(M, net, low, traded)
        cfg = dict(C22.CFG_FUNDED, soy_on=soy_on, soy_lev=1.0)
        lives, wds = [], []
        for i0 in fstarts:
            r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
            lives.append(r["life"]); wds.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
        if soy_on:
            SI.set_soy(M, np.zeros(M["n"]), np.zeros(M["n"]), np.zeros(M["n"]))
        lives = np.array(lives)
        return float((lives >= 252).mean()), float(np.mean(wds)) + FEE

    print("\n=== (b) ablation CHALLENGE (book vs book+soy V1-stop) ===")
    p0, at0 = challenge(False, 0.0)
    fv0_surv, fv0 = funded_book(False, 0.0)
    ev0 = p0 * fv0 - at0 * FEE
    abl = {"book_only": dict(p_funded=round(p0, 4), attempts=round(at0, 2),
                             funded_survive252=round(fv0_surv, 4), funded_value=round(fv0, 0),
                             EV=round(ev0, 0))}
    print(f"  book_only: p {p0*100:.2f}%  att {at0:.2f}  fundedSurv252 {fv0_surv*100:.1f}%  fundedV ${fv0:.0f}  EV ${ev0:.0f}")
    for K in (1.0, 2.0, 3.0, 4.0):
        p, at = challenge(True, K)
        s252, fv = funded_book(True, K)
        ev = p * fv - at * FEE
        abl[f"book+soy_K{K}"] = dict(p_funded=round(p, 4), attempts=round(at, 2),
                                     d_p=round(p - p0, 4), funded_survive252=round(s252, 4),
                                     funded_value=round(fv, 0), EV=round(ev, 0), d_EV=round(ev - ev0, 0))
        print(f"  book+soy K={K}: p {p*100:.2f}% (Δ{(p-p0)*100:+.2f})  att {at:.2f}  "
              f"fundedSurv252 {s252*100:.1f}% (book {fv0_surv*100:.1f})  fundedV ${fv:.0f}  EV ${ev:.0f} (Δ${ev-ev0:+.0f})")
    res["ablation"] = abl

    # ---------- (d) margin (soybean separate CFD) ----------
    pos = SS.build(SPREAD)["pos"]
    mr = {"cfd_1to10": 0.10, "futures_~5pct": 0.05}
    margin = {}
    for tag, rate in mr.items():
        margin[tag] = {K: dict(p50=round(float(np.percentile(K * pos * rate, 50)), 3),
                               p99=round(float(np.percentile(K * pos * rate, 99)), 3),
                               max=round(float((K * pos * rate).max()), 3))
                       for K in (1.0, 2.0, 3.0, 4.0)}
    res["margin_soy"] = dict(rates=mr, footprint=margin,
                             book_note="book metal (XAU swing 1:9) already binds 60% cap ~56% of days "
                                       "(asia Q3 spec p50 0.687); soybean is a SEPARATE instrument -> "
                                       "its margin ADDS to the book's during the 01:00-07:00 overlap.")
    print("\n=== (d) soybean margin footprint (frac of equity) ===")
    for tag, rate in mr.items():
        print(f"  {tag} ({rate*100:.0f}%): " + "  ".join(
            f"K{K}: p50 {margin[tag][K]['p50']:.2f}/p99 {margin[tag][K]['p99']:.2f}" for K in (1.0, 2.0, 3.0, 4.0)))

    (OUT / "q5_book.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q5_book.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
