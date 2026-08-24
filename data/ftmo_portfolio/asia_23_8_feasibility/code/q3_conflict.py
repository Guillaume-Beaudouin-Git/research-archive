"""Q3 — conflict with the existing gold_trend sleeve.

(a) corr(ASIA daily net, gold_trend daily net) — Pearson+Spearman, full + per regime.
(b) margin stacking under swing metal margin (XAU 1:9) when both gold legs coexist 01:00-09:00.
(c) window overlap (analytic).
(d) ablation: book vs book+ASIA (audited bar engine) -> p_funded, attempts, EV, sleeve Sharpe.
"""
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_series as ASER
V, C22, E = AI.V, AI.C22, AI.E
OUT = HERE.parent / "results"


def gold_trend_returns():
    """Reconstruct the gold_trend sleeve daily NET return from the cleanroom panels."""
    px = pd.read_parquet(E.CACHE / "panel_px.parquet")
    rets = pd.read_parquet(E.CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(E.CACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(E.CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(E.CACHE / "panel_mult.parquet")
    rt = pd.read_csv(E.AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    WT, _ = E.build_signals()
    w = WT["XAUUSD"].reindex(rets.index).fillna(0.0)          # deployed weight (gate+VT, shift baked)
    gross = w * rets["XAUUSD"]
    turn = w.diff().abs() * (rt["XAUUSD"] / 2.0 / 1e4)
    bps = np.where(w > 0, sL["XAUUSD"], np.where(w < 0, sS["XAUUSD"], 0.0))
    swap = w.abs() * pd.Series(bps, index=w.index) / 1e4 * mu["XAUUSD"]
    net = (gross - turn + swap).fillna(0.0)
    return net.rename("gold_trend"), w


def main():
    t0 = time.time()
    M = AI.load_asia_stack(spread_bps=1.5)
    dates = M["dates_idx"]
    WT_df, ON_df = E.build_signals()
    WT, ON = E.align_signals(M, WT_df, ON_df)
    WT0, ON0 = AI.book_off_signals(M)
    res = {}

    # ---------- (a) correlation ----------
    a = ASER.build(1.5)
    asia_exit = a["net_simple"].copy()
    asia_exit.index = asia_exit.index + pd.Timedelta(days=1)            # exit-date (CET book day)
    asia_exit = asia_exit.groupby(asia_exit.index.normalize()).sum()
    gt, w_gold = gold_trend_returns()
    df = pd.DataFrame({"asia": asia_exit, "gold_trend": gt}).dropna()
    df = df[(df.asia != 0) & df.gold_trend.notna()]
    def corr(d):
        return dict(n=len(d), pearson=round(float(d.asia.corr(d.gold_trend)), 4),
                    spearman=round(float(d.asia.corr(d.gold_trend, method="spearman")), 4))
    res["correlation"] = dict(
        full=corr(df),
        IS=corr(df[(df.index >= "2013-10-01") & (df.index <= "2019-12-31")]),
        OOS=corr(df[(df.index >= "2020-01-02")]),
        dead_regime_2018_19=corr(df[(df.index >= "2018-01-01") & (df.index <= "2019-12-31")]),
        gold_trend_long_frac=round(float((w_gold > 0).mean()), 3),
        asia_always_long=True)
    print("=== (a) correlation ASIA vs gold_trend (daily net) ===")
    for k, v in res["correlation"].items():
        print(f"  {k}: {v}")

    # ---------- (b) margin stacking under swing (XAU 1:9) ----------
    mr_swing = C22.MARGIN_RATES_SWING["XAUUSD"]          # 0.1111
    # ASIA notional/equity ~= K*pos (notional INIT*K*pos, eq~INIT). gold_trend notional/eq
    # ~= |w_gold| * book_scale; book overnight gold margin distribution from spec (swing).
    pos = ASER.build(1.5)["pos"]
    asia_margin_unit = {K: dict(
        p50=round(float(np.percentile(K * pos * mr_swing, 50)), 3),
        p99=round(float(np.percentile(K * pos * mr_swing, 99)), 3),
        max=round(float((K * pos.abs() * mr_swing).max()), 3))
        for K in (0.5, 1.0, 1.5, 2.0, 2.5)}
    res["margin_swing"] = dict(
        rate_xau_swing=mr_swing,
        asia_margin_frac_of_equity=asia_margin_unit,
        book_swing_margin_spec=dict(p50=0.687, p99=3.946, p999=5.112, bind_frac=0.56, cap=0.60),
        note=("book already binds the 60% cap 56% of the time under swing; ASIA adds the above "
              "metal margin during 01:00-09:00 CET (engine does NOT model intra-window margin -> "
              "real-account stop-out risk). gold_trend held continuously -> the two gold legs "
              "ALWAYS coexist during the ASIA window whenever gold_trend is long "
              f"({res['correlation']['gold_trend_long_frac']*100:.0f}% of days)."))
    print("\n=== (b) margin (swing XAU 1:9) ===")
    print(f"  ASIA margin frac of equity: {asia_margin_unit}")
    print(f"  book swing margin (spec): p50 0.687, p99 3.946, binds 60% cap 56% of days")

    # ---------- (d) ablation: book vs book+ASIA ----------
    print("\n=== (d) ablation book vs book+ASIA (audited bar engine) ===")
    starts_all = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])
    fstarts = np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP)
                              for _, lo, hi in C22.FUNDED_WINDOWS])

    def challenge_pooled(asia_on, K):
        cfg = dict(C22.CFG_CHALLENGE, asia_on=asia_on, asia_lev=K)
        out = [V.run_funnel(M, int(i0), WT, ON, cfg, wall=C22.WALL) for i0 in starts_all]
        f = np.array([o["funded"] for o in out]); at = np.array([o["attempts"] for o in out])
        return float(f.mean()), float(at.mean())

    def funded_value(asia_on, K):
        cfg = dict(C22.CFG_FUNDED, asia_on=asia_on, asia_lev=K)
        vals = []
        for i0 in fstarts:
            r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON,
                             wd_every=C22.FUNDED_WD_EVERY)
            vals.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
        return float(np.mean(vals)) + 96.0       # +1 fee refund

    abl = {}
    # baseline (ASIA off) — reproduce 0.87 + book funded_value (validate ~1422)
    p0, at0 = challenge_pooled(False, 0.0)
    fv0 = funded_value(False, 0.0)
    ev0 = p0 * fv0 - at0 * 96.0
    abl["book_only"] = dict(p_funded=round(p0, 4), attempts=round(at0, 2),
                            funded_value=round(fv0, 0), EV=round(ev0, 0))
    print(f"  book_only: p {p0*100:.2f}%  att {at0:.2f}  fundedV ${fv0:.0f}  EV ${ev0:.0f}")
    for K in (0.5, 1.0, 1.5, 2.0):
        p, at = challenge_pooled(True, K)
        fv = funded_value(True, K)
        ev = p * fv - at * 96.0
        abl[f"book+ASIA_K{K}"] = dict(p_funded=round(p, 4), attempts=round(at, 2),
                                      funded_value=round(fv, 0), EV=round(ev, 0),
                                      d_p=round(p - p0, 4), d_EV=round(ev - ev0, 0))
        print(f"  book+ASIA K={K}: p {p*100:.2f}% (Δ{(p-p0)*100:+.2f})  att {at:.2f}  "
              f"fundedV ${fv:.0f}  EV ${ev:.0f} (Δ${ev-ev0:+.0f})")
    res["ablation"] = abl

    (OUT / "q3_conflict.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q3_conflict.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
