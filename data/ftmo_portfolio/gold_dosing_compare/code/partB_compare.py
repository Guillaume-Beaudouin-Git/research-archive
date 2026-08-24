"""PART B — or-trend (book) vs ASIA (overnight): complementary or redundant?

(a) standalone Sharpe/ret/DD/skew (same period). (b) correlation. (c) temporal complementarity
(2018-19 ASIA-dead regime; or-trend OFF days). (d) active days/yr. (e) hypothetical book swap
(or-trend vs ASIA-replacing-or-trend vs BOTH) -> challenge p_funded + funded survival.
Reuses asia_inject, asia_series, asia_stop, cleanroom build_signals. NOT a deployment.
"""
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as sst

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_series as ASER
import asia_stop as STOP
V, C22, E = AI.V, AI.C22, AI.E
OUT = HERE.parent / "results"
ANN = 252.0


def sharpe(x):
    x = np.asarray(x); x = x[~np.isnan(x)]
    return float(x.mean() / x.std() * np.sqrt(ANN)) if len(x) > 1 and x.std() > 0 else np.nan


def mdd(r):
    r = np.asarray(r); eq = np.cumprod(1 + r); return float((eq / np.maximum.accumulate(eq) - 1).min())


def ortrend_net():
    rets = pd.read_parquet(E.CACHE / "panel_rets.parquet")
    sL = pd.read_parquet(E.CACHE / "panel_swapL.parquet"); sS = pd.read_parquet(E.CACHE / "panel_swapS.parquet")
    mu = pd.read_parquet(E.CACHE / "panel_mult.parquet")
    rt = pd.read_csv(E.AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    WT, _ = E.build_signals()
    w = WT["XAUUSD"].reindex(rets.index).fillna(0.0)
    gross = w * rets["XAUUSD"]; turn = w.diff().abs() * (rt["XAUUSD"] / 2.0 / 1e4)
    bps = np.where(w > 0, sL["XAUUSD"], np.where(w < 0, sS["XAUUSD"], 0.0))
    swap = w.abs() * pd.Series(bps, index=w.index) / 1e4 * mu["XAUUSD"]
    return (gross - turn + swap).fillna(0.0).rename("ortrend"), w


def main():
    t0 = time.time()
    res = {}
    ot, w = ortrend_net()                                   # book-date indexed
    asia = ASER.build(1.5)["net_simple"].copy()             # aday-indexed
    asia.index = asia.index + pd.Timedelta(days=1)          # -> exit-morning = book date
    asia = asia.groupby(asia.index.normalize()).sum().rename("asia")
    df = pd.concat([ot, asia], axis=1)
    common = df.dropna().index
    df = df.loc[common]
    print(f"common dates {len(df)}  {df.index.min().date()}->{df.index.max().date()}")

    # (a) standalone metrics (deployed series incl flat days for or-trend)
    def metr(s):
        r = s.to_numpy()
        return dict(sharpe_full=round(sharpe(r), 2), sharpe_active=round(sharpe(r[r != 0]), 2),
                    ann_ret_pct=round(float(r.mean() * ANN) * 100, 2), maxdd_pct=round(mdd(r) * 100, 1),
                    skew=round(float(sst.skew(r[r != 0])), 2), active_pct=round(float((r != 0).mean()) * 100, 1))
    res["standalone"] = {"ortrend": metr(df["ortrend"]), "asia": metr(df["asia"])}
    print("\n(a) standalone (common period):")
    for k, v in res["standalone"].items():
        print(f"  {k:8s} Sharpe(full/active) {v['sharpe_full']}/{v['sharpe_active']}  annret {v['ann_ret_pct']}%  "
              f"maxDD {v['maxdd_pct']}%  skew {v['skew']}  active {v['active_pct']}%")

    # (b) correlation
    def corr(d):
        d = d[(d["ortrend"] != 0) & (d["asia"] != 0)]  # both active
        return dict(n=len(d), pearson=round(float(d["ortrend"].corr(d["asia"])), 3),
                    spearman=round(float(d["ortrend"].corr(d["asia"], method="spearman")), 3))
    res["correlation"] = dict(
        full_bothactive=corr(df),
        all_days=dict(pearson=round(float(df["ortrend"].corr(df["asia"])), 3)),
        IS_2013_19=corr(df[df.index <= "2019-12-31"]), OOS_2020_26=corr(df[df.index >= "2020-01-02"]),
        regime_2018_19=corr(df[(df.index >= "2018-01-01") & (df.index <= "2019-12-31")]))
    print(f"\n(b) corr or-trend vs ASIA: all-days ρ={res['correlation']['all_days']['pearson']}  "
          f"both-active ρ={res['correlation']['full_bothactive']['pearson']}  "
          f"2018-19 ρ={res['correlation']['regime_2018_19']['pearson']}")

    # (c) temporal complementarity
    seg = {}
    for tag, mask in [("2018_19_ASIAdead", (df.index >= "2018-01-01") & (df.index <= "2019-12-31")),
                      ("ortrend_OFF", df["ortrend"] == 0), ("ortrend_ON", df["ortrend"] != 0)]:
        d = df[mask]
        seg[tag] = dict(n=len(d), ortrend_ann=round(float(d["ortrend"].mean() * ANN) * 100, 1),
                        asia_ann=round(float(d["asia"].mean() * ANN) * 100, 1),
                        ortrend_sharpe=round(sharpe(d["ortrend"]), 2), asia_sharpe=round(sharpe(d["asia"]), 2),
                        asia_pos_frac=round(float((d["asia"] > 0).mean()), 3))
    res["temporal"] = seg
    print("\n(c) temporal complementarity (annualized return contribution in each window):")
    for tag, v in seg.items():
        print(f"  {tag:18s} n={v['n']:4d}  or-trend {v['ortrend_ann']:+.1f}%/Sh{v['ortrend_sharpe']}  "
              f"ASIA {v['asia_ann']:+.1f}%/Sh{v['asia_sharpe']}  (ASIA pos {v['asia_pos_frac']*100:.0f}%)")

    # (e) hypothetical book swap: challenge + funded
    print("\n(e) hypothetical book swap (challenge p_funded / funded survive252):")
    M = AI.load_asia_stack(spread_bps=1.5)
    WT_full, ON = E.align_signals(M, *E.build_signals())
    WT_noOR = WT_full.copy(); WT_noOR[:, 0] = 0.0          # zero the XAUUSD (or-trend) leg, keep J1
    s = STOP.apply_stop(K=1.0, X=0.025)
    asia_net = ASER.align_to_book(s["net"], M["dates_idx"]); asia_low = ASER.align_to_book(s["low"], M["dates_idx"])
    all_starts = np.concatenate([V.starts(M, lo, hi, C22.COHORT_STEP) for _, lo, hi in C22.WINDOWS])
    fstarts = np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP) for _, lo, hi in C22.FUNDED_WINDOWS])

    def run(WT, asia_on):
        if asia_on:
            M["asia_net"], M["asia_low"] = asia_net, asia_low
        ch = float(np.mean([V.run_funnel(M, int(i0), WT, ON, dict(C22.CFG_CHALLENGE, asia_on=asia_on, asia_lev=1.0), wall=C22.WALL)["funded"] for i0 in all_starts]))
        lives = [V.run_funded(M, int(i0), WT, ON, dict(C22.CFG_FUNDED, asia_on=asia_on, asia_lev=1.0), horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)["life"] for i0 in fstarts]
        if asia_on:
            M["asia_net"], M["asia_low"] = np.zeros(M["n"]), np.zeros(M["n"])
        return ch, float((np.array(lives) >= 252).mean())

    swaps = {}
    for tag, WT, aon in [("book[or-trend] std", WT_full, False),
                         ("book[ASIA replaces or-trend]", WT_noOR, True),
                         ("book[BOTH or-trend+ASIA]", WT_full, True)]:
        ch, sv = run(WT, aon)
        swaps[tag] = dict(challenge=round(ch, 4), funded_survive252=round(sv, 4))
        print(f"  {tag:32s} challenge {ch*100:.2f}%  funded252 {sv*100:.1f}%")
    res["hypothetical_swap"] = swaps

    (OUT / "partB_compare.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten partB_compare.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
