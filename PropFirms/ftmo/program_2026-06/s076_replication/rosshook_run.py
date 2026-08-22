"""
rosshook_run.py — run the independent S076 replication + full validation suite.
Writes results/*.csv + validation.json to research/s076_replication/. READ-ONLY on source data.
"""
from __future__ import annotations
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from rosshook_replication import (  # noqa: E402
    CLASS, DEPLOYABLE, FX, RES, load_daily, simulate, mtm_daily, sharpe,
    trade_stats, boot_ci, nw_alpha, ANN)

ALL = list(CLASS)


def span_years(d):
    return (d.index.max() - d.index.min()).days / 365.25


def portfolio_ret(daily_rets: dict, syms) -> pd.Series:
    s = [daily_rets[x] for x in syms if x in daily_rets]
    if not s:
        return pd.Series(dtype=float)
    return pd.concat(s, axis=1).fillna(0.0).sum(axis=1)


def maxdd(ret: pd.Series) -> float:
    eq = (1 + ret).cumprod()
    return float((eq / eq.cummax() - 1).min())


def tsmom_factor(daily: dict) -> pd.Series:
    """Cross-instrument 12-month TSMOM: factor_t = mean_i sign(252d ret)_{t-1} * ret_i,t ."""
    cols = {}
    for s, d in daily.items():
        r = d["close"].pct_change()
        sig = np.sign(d["close"] / d["close"].shift(252) - 1).shift(1)
        cols[s] = (sig * r)
    return pd.concat(cols, axis=1).mean(axis=1)


def main():
    print("loading daily (EET)…", flush=True)
    daily = {s: load_daily(s, "EET") for s in ALL}
    daily_utc = {s: load_daily(s, "UTC") for s in ALL}

    # ---------- PRIMARY: realistic delay+1, real cost ----------
    trades = {s: simulate(daily[s], s, delay=1, fill="realistic", cost_mode="real") for s in ALL}
    rets = {s: mtm_daily(trades[s], daily[s]) for s in ALL}
    mkt = daily["US500"]["close"].pct_change().rename("mkt")
    tsmom = tsmom_factor(daily).rename("tsmom")

    # per-instrument
    pi = []
    for s in ALL:
        st = trade_stats(trades[s], span_years(daily[s]))
        pi.append(dict(sym=s, cls=CLASS[s], start=str(daily[s].index.min().date()),
                       end=str(daily[s].index.max().date()), **st,
                       mtm_sharpe=round(sharpe(rets[s]), 3),
                       pct_long=round(float((trades[s]["dir"] > 0).mean()), 3) if len(trades[s]) else np.nan))
    pi = pd.DataFrame(pi)
    pi.to_csv(RES / "per_instrument.csv", index=False)

    # per-class
    pc = []
    for cls in ["index", "commodity", "crypto", "fx"]:
        syms = [s for s in ALL if CLASS[s] == cls]
        allR = pd.concat([trades[s]["netR"] for s in syms if len(trades[s])]) if syms else pd.Series(dtype=float)
        lo, hi = boot_ci(allR.values)
        pr = portfolio_ret(rets, syms)
        pc.append(dict(cls=cls, n_inst=len(syms), n_trades=len(allR),
                       expR=round(float(allR.mean()), 4) if len(allR) else np.nan,
                       ci95_lo=round(lo, 4), ci95_hi=round(hi, 4),
                       win=round(float((allR > 0).mean()), 3) if len(allR) else np.nan,
                       mtm_sharpe=round(sharpe(pr), 3), maxdd=round(maxdd(pr), 4),
                       skew=round(float(pr[pr != 0].skew()), 3)))
    pc = pd.DataFrame(pc)
    pc.to_csv(RES / "per_class.csv", index=False)

    # deployable portfolio (indices+commodity+crypto)
    dep = portfolio_ret(rets, DEPLOYABLE)
    depR = pd.concat([trades[s]["netR"] for s in DEPLOYABLE if len(trades[s])])
    V = {}
    V["deployable_portfolio"] = dict(
        n_trades=int(len(depR)), expR=round(float(depR.mean()), 4),
        mtm_sharpe=round(sharpe(dep), 3), maxdd=round(maxdd(dep), 4),
        skew=round(float(dep[dep != 0].skew()), 3), pct_days_invested=round(float((dep != 0).mean()), 3))

    # ---------- covered alpha (deployable MTM ~ market + TSMOM) ----------
    V["covered_alpha"] = {
        "vs_market": nw_alpha(dep, pd.DataFrame({"mkt": mkt})),
        "vs_market_tsmom": nw_alpha(dep, pd.DataFrame({"mkt": mkt, "tsmom": tsmom})),
        "note": "deployable (indices+commodity+crypto) MTM daily returns; benchmark report real-data t=4.0"}

    # ---------- delay robustness (aggregate deployable) ----------
    dly = {}
    for delt in (0, 1, 2, 3, 5):
        tr = {s: simulate(daily[s], s, delay=delt, fill="realistic", cost_mode="real") for s in DEPLOYABLE}
        allT = pd.concat([tr[s] for s in DEPLOYABLE if len(tr[s])])
        allR = allT["netR"]
        span = max((allT["exit_date"].max() - allT["entry_date"].min()).days / 365.25, 1e-9)
        st = float(allR.mean() / allR.std() * np.sqrt(len(allR) / span)) if allR.std() > 0 else None
        dly[f"delay+{delt}"] = dict(n=int(len(allR)), expR=round(float(allR.mean()), 4),
                                    sharpe_trade=round(st, 3) if st else None)
    V["delay_robustness"] = dly

    # ---------- placebo (no hook) ----------
    plc = {s: simulate(daily[s], s, delay=1, fill="realistic", placebo=True, cost_mode="real") for s in DEPLOYABLE}
    plcR = pd.concat([plc[s]["netR"] for s in DEPLOYABLE if len(plc[s])])
    V["placebo"] = dict(placebo_expR=round(float(plcR.mean()), 4), placebo_n=int(len(plcR)),
                        strat_expR=round(float(depR.mean()), 4),
                        hook_adds=round(float(depR.mean() - plcR.mean()), 4),
                        hook_pct=round(float((depR.mean() - plcR.mean()) / depR.mean() * 100), 1) if depR.mean() else np.nan)

    # ---------- truncation causality (T=2020-01-01) ----------
    T = pd.Timestamp("2020-01-01"); genuine = 0; straddle = 0; common = 0
    for s in ALL:
        full = trades[s][trades[s]["exit_date"] < T].set_index("entry_date")
        trc = simulate(daily[s], s, delay=1, fill="realistic", cost_mode="real", truncate="2020-01-01")
        trc = trc[trc["exit_date"] < T].set_index("entry_date")
        comm = full.index.intersection(trc.index)
        common += len(comm)
        for ed in comm:
            a, b = full.loc[[ed]], trc.loc[[ed]]
            if len(a) != len(b) or bool((np.abs(a["netR"].values - b["netR"].values) > 1e-9).any()) \
                    or bool((a["dir"].values != b["dir"].values).any()):
                genuine += 1
        straddle += len(full.index.symmetric_difference(trc.index))
    V["truncation_causality"] = dict(T="2020-01-01", common_trades=int(common),
                                     genuine_disagreements=int(genuine), straddling_edge=int(straddle),
                                     note="genuine_disagreements=0 => strictly causal; straddling = positions open at T "
                                          "force-closed at the truncation edge (expected, not a leak)")

    # ---------- OOS splits (per class expR) ----------
    def oos(split_year):
        out = {}
        for cls in ["index", "commodity", "crypto", "fx"]:
            syms = [s for s in ALL if CLASS[s] == cls]
            tr = pd.concat([trades[s] for s in syms if len(trades[s])]) if syms else pd.DataFrame()
            if len(tr) == 0:
                out[cls] = dict(train=np.nan, test=np.nan); continue
            trn = tr[tr["entry_date"] < pd.Timestamp(split_year)]["netR"]
            tst = tr[tr["entry_date"] >= pd.Timestamp(split_year)]["netR"]
            out[cls] = dict(train_expR=round(float(trn.mean()), 4) if len(trn) else None, train_n=int(len(trn)),
                            test_expR=round(float(tst.mean()), 4) if len(tst) else None, test_n=int(len(tst)))
        return out
    V["oos_primary_2016"] = oos("2016-01-01")
    V["oos_secondary_2021"] = oos("2021-01-01")

    # ---------- sub-period stability (per class expR + MTM sharpe) ----------
    def subperiod(a, b):
        out = {}
        for cls in ["index", "commodity", "crypto", "fx"]:
            syms = [s for s in ALL if CLASS[s] == cls]
            tr = pd.concat([trades[s] for s in syms if len(trades[s])]) if syms else pd.DataFrame()
            r = tr[(tr["entry_date"] >= pd.Timestamp(a)) & (tr["entry_date"] < pd.Timestamp(b))]["netR"] if len(tr) else pd.Series(dtype=float)
            pr = portfolio_ret({s: rets[s][(rets[s].index >= a) & (rets[s].index < b)] for s in syms}, syms)
            out[cls] = dict(n=int(len(r)), expR=round(float(r.mean()), 4) if len(r) else None,
                            mtm_sharpe=round(sharpe(pr), 3) if len(pr) else None)
        return out
    V["subperiod_2007_2011"] = subperiod("2007-01-01", "2012-01-01")
    V["subperiod_2012_2018"] = subperiod("2012-01-01", "2019-01-01")
    V["subperiod_2019_2026"] = subperiod("2019-01-01", "2027-01-01")

    # ---------- cost sensitivity (deployable aggregate expR) ----------
    cst = {}
    for mode in ("real", "flat"):
        for xb in (0, 3, 6, 10):
            tr = {s: simulate(daily[s], s, delay=1, fill="realistic", cost_mode=mode, extra_bps=xb) for s in DEPLOYABLE}
            allR = pd.concat([tr[s]["netR"] for s in DEPLOYABLE if len(tr[s])])
            cst[f"{mode}+{xb}bps"] = round(float(allR.mean()), 4)
    V["cost_sensitivity"] = cst

    # ---------- optimistic vs realistic fill (aggregate) ----------
    opt = {s: simulate(daily[s], s, fill="optimistic", cost_mode="real") for s in DEPLOYABLE}
    optR = pd.concat([opt[s]["netR"] for s in DEPLOYABLE if len(opt[s])])
    V["fill_compare"] = dict(optimistic_expR=round(float(optR.mean()), 4), optimistic_n=int(len(optR)),
                             realistic_expR=round(float(depR.mean()), 4), realistic_n=int(len(depR)))

    # ---------- UTC-midnight sensitivity (per class expR + deployable sharpe) ----------
    tr_utc = {s: simulate(daily_utc[s], s, delay=1, fill="realistic", cost_mode="real") for s in ALL}
    rets_utc = {s: mtm_daily(tr_utc[s], daily_utc[s]) for s in ALL}
    utc = {}
    for cls in ["index", "commodity", "crypto", "fx"]:
        syms = [s for s in ALL if CLASS[s] == cls]
        r = pd.concat([tr_utc[s]["netR"] for s in syms if len(tr_utc[s])]) if syms else pd.Series(dtype=float)
        utc[cls] = dict(expR_utc=round(float(r.mean()), 4) if len(r) else None,
                        mtm_sharpe_utc=round(sharpe(portfolio_ret(rets_utc, syms)), 3))
    V["utc_sensitivity"] = dict(per_class=utc,
                                deployable_sharpe_utc=round(sharpe(portfolio_ret(rets_utc, DEPLOYABLE)), 3),
                                deployable_sharpe_eet=round(sharpe(dep), 3))

    # ---------- save ----------
    pd.concat([trades[s] for s in ALL if len(trades[s])]).to_csv(RES / "trades_all.csv", index=False)
    dep.rename("ret").to_frame().assign(equity=(1 + dep).cumprod()).to_csv(RES / "mtm_deployable.csv")
    for cls in ["index", "commodity", "crypto", "fx"]:
        syms = [s for s in ALL if CLASS[s] == cls]
        portfolio_ret(rets, syms).rename("ret").to_csv(RES / f"mtm_{cls}.csv")
    json.dump(V, open(RES / "validation.json", "w"), indent=2, default=str)

    # console summary
    print("\n=== PER CLASS (realistic delay+1, real cost, EET) ===")
    print(pc.to_string(index=False))
    print("\n=== DEPLOYABLE PORTFOLIO ===", json.dumps(V["deployable_portfolio"]))
    print("covered alpha vs mkt+TSMOM:", json.dumps(V["covered_alpha"]["vs_market_tsmom"]))
    print("placebo:", json.dumps(V["placebo"]))
    print("truncation:", json.dumps(V["truncation_causality"]))
    print("delay:", json.dumps(V["delay_robustness"]))
    print("cost:", json.dumps(V["cost_sensitivity"]))
    print("UTC sensitivity deployable sharpe EET vs UTC:",
          V["utc_sensitivity"]["deployable_sharpe_eet"], "vs", V["utc_sensitivity"]["deployable_sharpe_utc"])
    print(f"\nresults -> {RES}")


if __name__ == "__main__":
    main()
