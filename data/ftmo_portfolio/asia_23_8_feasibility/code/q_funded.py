"""ASIA_23_8 FUNDED-only study (no profit target) with hard intraday stop.

Q1 funded survival (no-stop), Q2 stop levels (survival + edge-erosion), Q3 funded ablation.
Reuses the AUDITED v2.2 funded engine (run_funded) via the validated wrapper; the stop is a
series-level transform (asia_stop). Funded cohorts span the FULL sample incl. the 2018-19 dead
regime. ≤5 variants (4 used: no-stop + stops -1.5/-2.5/-3.5%), K=1 a priori. DSR n_trials=100.
"""
import importlib.util, json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asia_inject as AI
import asia_stop as STOP
import asia_series as ASER
V, C22, E = AI.V, AI.C22, AI.E
OUT = HERE.parent / "results"
INIT = 10000.0
N_TRIALS = 100          # DSR: 90 due-diligence + challenge overlays + 4 funded variants

_s = importlib.util.spec_from_file_location(
    "yt_stats", "<HOME>/Desktop/Algo_claude/yt_strategy_replications/engine/stats.py")
S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)


def funded_cohorts(M, end="2025-06-30", step=21, horizon=252):
    idx = M["dates_idx"]
    last_ok = np.where(idx <= pd.Timestamp(end))[0]
    starts = [i for i in range(0, last_ok[-1] + 1, step) if i + horizon < M["n"]]
    return np.array(starts)


def run_survival(M, WT, ON, cfg, horizon, starts):
    surv, ret, dd = [], [], []
    for i0 in starts:
        r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=horizon, wd_every=C22.FUNDED_WD_EVERY)
        surv.append(not r["busted"])
        ret.append(0.8 * (r["wd"] + r["residual"]) / INIT * (252.0 / horizon))   # ann. trader net
        dd.append(r.get("min_eq", INIT) / INIT - 1.0)
    return dict(p_survive=float(np.mean(surv)), n=len(surv),
                ann_ret_pct=round(float(np.mean(ret)) * 100, 2),
                ann_ret_med_pct=round(float(np.median(ret)) * 100, 2),
                maxdd_p5=round(float(np.percentile(dd, 5)) * 100, 2),
                maxdd_worst=round(float(np.min(dd)) * 100, 2))


def edge_metrics(net_aday):
    r = net_aday.to_numpy(float)
    cut = int(len(r) * 0.6)
    dsr = S.deflated_sharpe_ratio(r, N_TRIALS, periods_per_year=252)
    return dict(sharpe=round(S.sharpe_ratio(r, 252), 3),
                oos_sharpe=round(S.sharpe_ratio(r[cut:], 252), 3),
                dsr100=round(dsr["dsr"], 3), mean_bp=round(float(r.mean()) * 1e4, 2),
                maxdd=round(S.max_drawdown((1 + net_aday).cumprod().to_numpy())[0] * 100, 2))


def set_asia(M, net_aday, low_aday):
    M["asia_net"] = ASER.align_to_book(net_aday, M["dates_idx"])
    M["asia_low"] = ASER.align_to_book(low_aday, M["dates_idx"])


def main():
    t0 = time.time()
    M = AI.load_asia_stack(spread_bps=1.5)
    WT0, ON0 = AI.book_off_signals(M)
    cfg_off = dict(C22.CFG_FUNDED, on_w=0.0, orb_risk=0.0, micro_orb=False, asia_on=True)
    st126 = funded_cohorts(M, horizon=126)
    st252 = funded_cohorts(M, horizon=252)
    res = {"n_trials_dsr": N_TRIALS, "K": 1.0}

    variants = [("V_nostop", None), ("V_stop_1.5", 0.015),
                ("V_stop_2.5", 0.025), ("V_stop_3.5", 0.035)]
    print(f"{'variant':<12}{'trig%':>6}{'Sharpe':>8}{'OOS':>7}{'DSR100':>8}"
          f"{'pSurv6m':>9}{'pSurv12m':>10}{'annRet%':>9}{'DDworst%':>10}")
    res["variants"] = {}
    for vname, X in variants:
        s = STOP.apply_stop(K=1.0, X=X)
        set_asia(M, s["net"], s["low"])
        em = edge_metrics(s["net"])
        sv6 = run_survival(M, WT0, ON0, dict(cfg_off, asia_lev=1.0), 126, st126)
        sv12 = run_survival(M, WT0, ON0, dict(cfg_off, asia_lev=1.0), 252, st252)
        res["variants"][vname] = dict(stop_pct=None if X is None else X * 100,
                                      trig_frac=round(s["trig_frac"], 4),
                                      alpha_given_up_pct=round(s["alpha_given_up"] * 100, 1),
                                      protection_pct=round(s["protection"] * 100, 1),
                                      **em, survive_6m=sv6, survive_12m=sv12)
        print(f"{vname:<12}{s['trig_frac']*100:>5.1f}%{em['sharpe']:>8.2f}{em['oos_sharpe']:>7.2f}"
              f"{em['dsr100']:>8.2f}{sv6['p_survive']*100:>8.1f}%{sv12['p_survive']*100:>9.1f}%"
              f"{sv12['ann_ret_pct']:>8.1f}%{sv12['maxdd_worst']:>9.1f}%")

    # K sensitivity (risk-scaling only, NOT edge search) on no-stop and stop-2.5
    print("\n=== K sensitivity (survival only; Sharpe ~invariant) ===")
    res["k_sensitivity"] = {}
    for tag, X in [("nostop", None), ("stop_2.5", 0.025)]:
        for K in (0.5, 1.5):
            s = STOP.apply_stop(K=K, X=X)
            set_asia(M, s["net"], s["low"])
            sv = run_survival(M, WT0, ON0, dict(cfg_off, asia_lev=K), 252, st252)
            res["k_sensitivity"][f"{tag}_K{K}"] = dict(p_survive12m=round(sv["p_survive"], 3),
                                                       ann_ret_pct=sv["ann_ret_pct"],
                                                       dd_worst=sv["maxdd_worst"])
            print(f"  {tag} K={K}: pSurv12m {sv['p_survive']*100:.1f}%  "
                  f"annRet {sv['ann_ret_pct']:+.1f}%  DDworst {sv['maxdd_worst']:.1f}%")

    # ---------- Q3 funded ablation: book vs book + ASIA (best surviving stop) ----------
    print("\n=== Q3 funded ablation (book vs book+ASIA stopped) ===")
    WT_df, ON_df = E.build_signals()
    WT, ON = E.align_signals(M, WT_df, ON_df)
    best_X = 0.025          # best surviving level (highest pSurv12m 92.4% + top Sharpe), per pre-reg
    s = STOP.apply_stop(K=1.0, X=best_X)

    def book_survival(asia_on, K=1.0):
        if asia_on:
            sk = STOP.apply_stop(K=K, X=best_X)
            set_asia(M, sk["net"], sk["low"])
        cfg = dict(C22.CFG_FUNDED, asia_on=asia_on, asia_lev=K)
        return run_survival(M, WT, ON, cfg, 252, st252)

    def book_funded_sharpe(asia_on):
        AI.DAILY_EQ.clear()
        if asia_on:
            set_asia(M, s["net"], s["low"])
        cfg = dict(C22.CFG_FUNDED, asia_on=asia_on, asia_lev=1.0, log_eq=True)
        V.run_funded(M, int(funded_cohorts(M, horizon=1)[0]), WT, ON, cfg,
                     horizon=10 ** 9, wd_every=10 ** 9)        # full sample, no withdrawals
        eq = pd.Series([e for _, e in AI.DAILY_EQ])
        ret = eq.pct_change().dropna().to_numpy()
        return round(S.sharpe_ratio(ret, 252), 3), round(S.max_drawdown(eq.to_numpy())[0] * 100, 2)

    b0, a1, a_half = book_survival(False), book_survival(True, 1.0), book_survival(True, 0.5)
    sh0, dd0 = book_funded_sharpe(False)
    sh1, dd1 = book_funded_sharpe(True)
    # rho with gold_trend
    import q3_conflict as Q3
    gt, w_gold = Q3.gold_trend_returns()
    ax = s["net"].copy(); ax.index = ax.index + pd.Timedelta(days=1)
    ax = ax.groupby(ax.index.normalize()).sum()
    d = pd.DataFrame({"asia": ax, "gtrend": gt}).dropna(); d = d[d["asia"] != 0]
    rho = round(float(d["asia"].corr(d["gtrend"])), 4)
    # combined gold margin under swing (vm1 funded): |w_gold| + K*pos, x 0.1111
    pos = ASER.build(1.5)["pos"]
    comb = (w_gold.abs().reindex(pos.index).fillna(0) + 1.0 * pos) * C22.MARGIN_RATES_SWING["XAUUSD"]
    res["ablation"] = dict(
        best_stop_pct=best_X * 100,
        book_only=dict(p_survive12m=round(b0["p_survive"], 3), ann_ret=b0["ann_ret_pct"],
                       funded_sharpe=sh0, funded_maxdd=dd0),
        book_plus_asia=dict(p_survive12m=round(a1["p_survive"], 3), ann_ret=a1["ann_ret_pct"],
                            funded_sharpe=sh1, funded_maxdd=dd1),
        book_plus_asia_Khalf=dict(p_survive12m=round(a_half["p_survive"], 3),
                                   ann_ret=a_half["ann_ret_pct"], maxdd_worst=a_half["maxdd_worst"]),
        d_p_survive=round(a1["p_survive"] - b0["p_survive"], 4),
        d_p_survive_Khalf=round(a_half["p_survive"] - b0["p_survive"], 4),
        d_funded_sharpe=round(sh1 - sh0, 3),
        rho_asia_goldtrend=rho,
        combined_gold_margin_swing=dict(p50=round(float(comb.quantile(.5)), 3),
                                        p99=round(float(comb.quantile(.99)), 3),
                                        max=round(float(comb.max()), 3), cap=0.60))
    print(f"  book_only:      pSurv12m {b0['p_survive']*100:.1f}%  annRet {b0['ann_ret_pct']:+.1f}%  "
          f"fundedSharpe {sh0:.2f}  DD {dd0:.1f}%")
    print(f"  book+ASIA K=1.0:pSurv12m {a1['p_survive']*100:.1f}% (Δ{(a1['p_survive']-b0['p_survive'])*100:+.1f}) "
          f"annRet {a1['ann_ret_pct']:+.1f}%  fundedSharpe {sh1:.2f} (Δ{sh1-sh0:+.2f})  DD {dd1:.1f}%")
    print(f"  book+ASIA K=0.5:pSurv12m {a_half['p_survive']*100:.1f}% (Δ{(a_half['p_survive']-b0['p_survive'])*100:+.1f}) "
          f"annRet {a_half['ann_ret_pct']:+.1f}%  DD {a_half['maxdd_worst']:.1f}%")
    print(f"  rho(ASIA,gold_trend) {rho}  | combined gold margin swing p99 {res['ablation']['combined_gold_margin_swing']['p99']} (cap 0.60)")

    (OUT / "q_funded.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q_funded.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
