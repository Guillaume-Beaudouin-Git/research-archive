"""
book.py — HONEST survivors-book baseline for FTMO 10k 2-step.
Sleeves: RH deployable (0.44) + TSMOM swap-NET (deployable; not the swap-free 0.85) + Sleeve C
(US30 MR, re-verified, included only if OOS daily-Sharpe CI clears ~0).
Reuses the AUDIT's monotone first-passage engine (read-only import). Leverage fixed ex-ante on IS.
CIs on every p(pass) via OUTER bootstrap. DSR at honest N.
"""
from __future__ import annotations
import sys, json, math
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, skew, kurtosis

ROOT = Path("<HOME>/Desktop/Algo_claude")
AUDIT = ROOT / "research/ftmo_portfolio_audit/code"
sys.path.insert(0, str(AUDIT))
import firstpassage as fp                                   # noqa  (audit engine, read-only)
from audit_common import vol_target, load_m1               # noqa
from sleeve_bc import build_bars, backtest                 # noqa  (audit clean-room Sleeve C)

OUT = ROOT / "research/ftmo_survivors_book/results"
RES = ROOT / "research/ftmo_survivors_book"
IS_END = "2024-12-31"
OOS0, OOS1 = "2025-01-01", "2026-06-05"
EULER = 0.5772156649


def ann_sharpe(s):
    s = s.dropna(); v = s[s != 0]
    return float(s.mean() / s.std(ddof=1) * np.sqrt(252)) if s.std(ddof=1) > 0 else 0.0


def daily_sharpe(s):
    s = s.dropna()
    return float(s.mean() / s.std(ddof=1)) if s.std(ddof=1) > 0 else 0.0


def sharpe_ci(s, nb=2000, seed=1):
    """Block-bootstrap 90% CI on ANNUAL Sharpe of a daily series."""
    s = s.dropna().values
    T = len(s)
    if T < 60:
        return (np.nan, np.nan, np.nan)
    block = max(2, int(round(np.sqrt(T))))
    rng = np.random.default_rng(seed)
    out = []
    nblk = int(np.ceil(T / block))
    for _ in range(nb):
        starts = rng.integers(0, T, nblk)
        idx = np.concatenate([np.arange(st, st + block) % T for st in starts])[:T]
        b = s[idx]
        sd = b.std(ddof=1)
        out.append(b.mean() / sd * np.sqrt(252) if sd > 0 else 0.0)
    return (float(np.percentile(out, 5)), float(np.median(out)), float(np.percentile(out, 95)))


def peryear_sign(s):
    return {int(y): round(g.mean() / g.std(ddof=1) * np.sqrt(252), 2)
            for y, g in s.groupby(s.index.year) if g.std(ddof=1) > 0}


def dsr(s, n_trials):
    r = s.dropna().values
    T = len(r); srd = r.mean() / r.std(ddof=1)
    g3 = skew(r, bias=False); g4 = kurtosis(r, fisher=False, bias=False)
    se = np.sqrt(max((1 - g3 * srd + ((g4 - 1) / 4) * srd ** 2) / (T - 1), 1e-12))
    emax = se * ((1 - EULER) * norm.ppf(1 - 1 / n_trials) + EULER * norm.ppf(1 - 1 / (n_trials * np.e)))
    return round(float(norm.cdf((srd - emax) / se)), 3)


def main():
    rep = {}
    # ---------- load sleeves (raw daily) ----------
    RH = pd.read_csv(ROOT / "research/s076_replication/results/mtm_deployable.csv",
                     parse_dates=["date"]).set_index("date")["ret"]
    def load_ts(name):
        s = pd.read_csv(OUT / name, index_col=0, parse_dates=True).iloc[:, 0]
        s.index = pd.to_datetime(s.index)
        return s
    TS_net = load_ts("tsmom_swapnet_nocrypto.csv")
    TS_free = load_ts("tsmom_swapfree_full.csv")
    TS_c0 = load_ts("tsmom_swapnet_crypto0_full.csv")

    # ---------- Sleeve C: re-verify clean-room (REPORT.md sec4 spec) ----------
    us30 = load_m1("US30", "deep")
    barsC = build_bars(us30, "60min", 13, 20, drop_weekend=True)
    C = backtest(barsC, "US30", "mr", window=16, z_entry=2.0, daily_stop=0.02, markup=2.0)["net"]
    C.index = pd.to_datetime(C.index)
    c_is = sharpe_ci(C.loc[:IS_END]); c_oos = sharpe_ci(C.loc[OOS0:OOS1])
    include_C = c_oos[0] > 0.0
    rep["sleeve_C_reverify"] = {
        "IS_annSharpe_median_ci90": [round(c_is[1], 2), [round(c_is[0], 2), round(c_is[2], 2)]],
        "OOS_annSharpe_median_ci90": [round(c_oos[1], 2), [round(c_oos[0], 2), round(c_oos[2], 2)]],
        "inclusion_bar": "OOS ann-Sharpe 90%CI lower > 0",
        "INCLUDED": bool(include_C)}
    print(f"[Sleeve C] IS Sh={c_is[1]:+.2f} CI[{c_is[0]:+.2f},{c_is[2]:+.2f}] | "
          f"OOS Sh={c_oos[1]:+.2f} CI[{c_oos[0]:+.2f},{c_oos[2]:+.2f}] -> INCLUDE={include_C}")

    # ---------- per-sleeve honest stats ----------
    print("\n[per-sleeve] annSharpe (IS / OOS) + CI:")
    sleeves_raw = {"RH": RH, "TSMOM_swapnet_nocrypto": TS_net, "Sleeve_C_US30MR": C,
                   "TSMOM_swapfree(NOT deployable)": TS_free, "TSMOM_swapnet_crypto0": TS_c0}
    persleeve = {}
    for nm, s in sleeves_raw.items():
        is_ci, oos_ci = sharpe_ci(s.loc[:IS_END]), sharpe_ci(s.loc[OOS0:OOS1])
        persleeve[nm] = {"IS": [round(is_ci[1], 2), [round(is_ci[0], 2), round(is_ci[2], 2)]],
                         "OOS": [round(oos_ci[1], 2), [round(oos_ci[0], 2), round(oos_ci[2], 2)]],
                         "excess_kurt": round(float(kurtosis(s.dropna(), fisher=True, bias=False)), 1),
                         "peryear": peryear_sign(s)}
        print(f"  {nm:32s} IS {is_ci[1]:+.2f}[{is_ci[0]:+.2f},{is_ci[2]:+.2f}]  "
              f"OOS {oos_ci[1]:+.2f}[{oos_ci[0]:+.2f},{oos_ci[2]:+.2f}]  kurt={persleeve[nm]['excess_kurt']}")
    rep["per_sleeve"] = persleeve

    # ---------- build books (vol-target each to 1%/day, then combine) ----------
    def vt(s):
        return vol_target(s.dropna(), sigma_target=0.01, lookback=63, cap=4.0)

    def combine(sleeves, weight="equal"):
        df = pd.concat({k: vt(v) for k, v in sleeves.items()}, axis=1)
        start = max(df[c].first_valid_index() for c in df.columns)   # all sleeves live
        df = df.loc[start:]
        z = df.fillna(0.0)                                            # non-trading sleeve = flat/allocated
        if weight == "equal":
            return z.mean(axis=1), df
        inv = 1.0 / df.rolling(63).std().shift(1).replace(0, np.nan)
        w = inv.div(inv.sum(axis=1), axis=0).fillna(0.0)
        return (w * z).sum(axis=1), df

    HB = "HONEST_2sleeve(RH+TSMOMswapnet)"
    base = {"RH": RH, "TSMOM": TS_net}
    if include_C:
        base["C"] = C
        HB = "HONEST_3sleeve(RH+TSMOMswapnet+C)"
    books = {
        HB: base,
        "incl_C_show(RH+TSMOMnet+C)": {"RH": RH, "TSMOM": TS_net, "C": C},
        "optimistic_swapFREE_TSMOM": {"RH": RH, "TSMOM": TS_free},
        "swapnet_crypto0_TSMOM": {"RH": RH, "TSMOM": TS_c0},
    }

    # ---------- leverage fixed ex-ante on IS, then OOS; + sweep ----------
    def ppass(series, L, H):
        return fp.cdf_sequential(series, L, [H], n_paths=15000)[H]

    def ppass_ci(series, L, H, n_outer=80):
        o = fp.outer_resample_ci(series, L, H, n_outer=n_outer, n_paths=9000)
        return o

    Lgrid = [1.5, 2.0, 2.5, 3.0, 3.5]
    bookres = {}
    for bname, sleeves in books.items():
        comb_ew, df = combine(sleeves, "equal")
        comb_rp, _ = combine(sleeves, "risk-parity")
        is_s = comb_ew.loc[:IS_END]; oos_s = comb_ew.loc[OOS0:OOS1]
        # fix L on IS: argmax IS p(pass<=12mo) (NEVER OOS)
        is_pp = {L: ppass(is_s, L, 252) for L in Lgrid}
        Lstar = max(is_pp, key=is_pp.get)
        # sweep (report both IS and OOS, headline uses Lstar)
        sweep = {L: {"IS_12mo": round(ppass(is_s, L, 252), 3),
                     "OOS_12mo": round(ppass(oos_s, L, 252), 3),
                     "OOS_6mo": round(ppass(oos_s, L, 126), 3)} for L in Lgrid}
        # headline p(pass) table at Lstar with 90% CI (outer bootstrap)
        tbl = {}
        for win, s in [("IS", is_s), ("OOS", oos_s)]:
            for H, mo in [(126, "6mo"), (252, "12mo")]:
                ci = ppass_ci(s, Lstar, H)
                tbl[f"{win}_{mo}"] = {"p": round(ci["mean"], 3),
                                      "ci90": [round(ci["ci90"][0], 3), round(ci["ci90"][1], 3)]}
        # monotonicity sanity (OOS)
        mono = {h: round(ppass(oos_s, Lstar, h), 3) for h in [63, 126, 189, 252]}
        bookres[bname] = {
            "n_sleeves": len(sleeves), "Lstar_fixed_on_IS": Lstar,
            "combined_annSharpe_IS": round(ann_sharpe(is_s), 2),
            "combined_annSharpe_OOS": round(ann_sharpe(oos_s), 2),
            "combined_dailySharpe_OOS": round(daily_sharpe(oos_s), 4),
            "combined_excess_kurt": round(float(kurtosis(comb_ew.dropna(), fisher=True, bias=False)), 1),
            "ppass_table": tbl, "leverage_sweep": sweep,
            "monotonic_OOS_3_6_9_12mo": mono,
            "rp_vs_ew_OOS_annSharpe": [round(ann_sharpe(comb_rp.loc[OOS0:OOS1]), 2)],
        }
        print(f"\n[{bname}] L*={Lstar} (IS-fixed)  combSh IS={bookres[bname]['combined_annSharpe_IS']:+.2f} "
              f"OOS={bookres[bname]['combined_annSharpe_OOS']:+.2f}")
        for k, v in tbl.items():
            print(f"    p(pass) {k:9s} = {v['p']:.3f}  90%CI[{v['ci90'][0]:.3f},{v['ci90'][1]:.3f}]")
        print(f"    monotone OOS 3/6/9/12mo: {mono}")
    rep["books"] = bookres

    # ---------- final-book tail correlation + co-breach ----------
    fin = books[HB]
    dfc = pd.concat({k: vt(v) for k, v in fin.items()}, axis=1).dropna()
    port = dfc.mean(axis=1)
    tail = {"unconditional_corr": dfc.corr().round(3).to_dict()}
    us500 = pd.read_csv(ROOT / "data/panels/ftmo_close.csv", index_col=0, parse_dates=True)["US500"].pct_change().reindex(dfc.index)
    trend = us500.rolling(20).sum().abs()
    for nm, m in [("trend_top25", trend >= trend.quantile(.75)),
                  ("volshock_top10", us500.abs() >= us500.abs().quantile(.90)),
                  ("worst_decile_port", port <= port.quantile(.10))]:
        sub = dfc[m.reindex(dfc.index).fillna(False)]
        if len(sub) > 20:
            cc = sub.corr().round(3)
            pairs = {f"{a}|{b}": float(cc.loc[a, b]) for i, a in enumerate(cc.columns)
                     for b in cc.columns[i + 1:]}
            tail[nm] = {"n": len(sub), "corr": pairs}
    thr = dfc.quantile(0.05)            # -5%-ish daily-floor proxy: each sleeve's own 5th pct
    below = (dfc < thr).sum(axis=1)
    k = dfc.shape[1]
    indep2 = sum([math.comb(k, j) * 0.05 ** j * 0.95 ** (k - j) for j in range(2, k + 1)])
    tail["co_breach_ge2"] = {"empirical": round(float((below >= 2).mean()), 4),
                             "independent": round(float(indep2), 4)}
    rep["final_book_tail"] = tail
    print(f"\n[tail] uncond corr={tail['unconditional_corr']}")
    print(f"[tail] co-breach >=2 empirical={tail['co_breach_ge2']['empirical']} vs indep={tail['co_breach_ge2']['independent']}")

    # ---------- DSR at honest N ----------
    comb_ew, _ = combine(fin, "equal")
    rep["DSR"] = {f"N={N}": dsr(comb_ew, N) for N in [1, 20, 100, 500]}
    rep["DSR_note"] = ("honest N >> 100: survivors drawn from 109-strategy library (RH) + multi-asset "
                       "TSMOM program + this exercise (leverage sweep 5 x weightings 2 x Sleeve-C variants x "
                       "swap scenarios). Report N>=100.")
    print(f"\n[DSR] {rep['DSR']}")

    (OUT / "book_results.json").write_text(json.dumps(rep, indent=2, default=str))
    comb_ew.rename("ret").to_csv(OUT / "final_book_daily.csv")
    print("\nwrote book_results.json + final_book_daily.csv")


if __name__ == "__main__":
    main()
