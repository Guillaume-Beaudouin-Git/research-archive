"""Piste A iteration — two literature-grounded angles:
 H1: gold/silver ratio z-score with a HARD z-stop + vol-target to control the -50% DD (repo 3A had SR 0.77 / DD -50%).
 H2: Avellaneda-Lee factor-residual s-score (index vs basket of the other indices), market-neutral, two-sided.
Net of active-fill 2-leg cost + asymmetric swap. Signal T-1, trade T. Target: net Sharpe>0.5, MaxDD<10%.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lib import data as D, stats as st, ftmo_costs as C
from statsmodels.tsa.stattools import adfuller

OUT = os.path.dirname(os.path.abspath(__file__)); ANN = 252.0


def roll_beta(a, b, w):
    mb = b.rolling(w).mean(); ma = a.rolling(w).mean()
    cov = (a*b).rolling(w).mean() - ma*mb; var = (b*b).rolling(w).mean() - mb*mb
    return (cov/var).shift(1)


def stats_block(r):
    r = r.dropna(); eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1)
    return dict(sharpe=st.sharpe(r.values), hac_t=st.hac_tstat(r.values),
                ann_ret=(1+r.mean())**ANN-1, ann_vol=r.std()*np.sqrt(ANN),
                maxdd=float(dd.min()), worst_day=float(r.min()), skew=float(r.skew()), n=int(len(r)))


def voltarget(book, tv=0.10, maxlev=1.5):
    rv = book.rolling(63).std()*np.sqrt(ANN)
    lev = (tv/rv).clip(upper=maxlev).shift(1).fillna(0.0)
    return book*lev


def gold_silver(z_in=2.0, z_out=0.5, z_stop=3.0, hard_stop=True, swap_mult=1.0):
    panel = D.close_panel(["XAUUSD", "XAGUSD"], "D"); la, lb = np.log(panel["XAUUSD"]), np.log(panel["XAGUSD"])
    beta = roll_beta(la, lb, 252); spread = la - beta*lb
    z = (spread - spread.rolling(60).mean())/spread.rolling(60).std()
    dla, dlb = la.diff(), lb.diff(); idx = la.index; n = len(idx)
    rt = (C.rt_cost_bps("XAUUSD")+C.rt_cost_bps("XAGUSD"))/1e4
    finL = C.pair_financing_bps_night("XAUUSD", "XAGUSD", +1, swap_mult)/1e4
    finS = C.pair_financing_bps_night("XAUUSD", "XAGUSD", -1, swap_mult)/1e4
    trip = np.where(idx.weekday == C.TRIPLE_DOW["XAUUSD"], 3.0, 1.0)
    za = z.values; pos = np.zeros(n); cur = 0
    for t in range(n):
        if np.isnan(za[t]): pos[t] = 0; cur = 0; continue
        if cur == 0:
            if za[t] <= -z_in: cur = 1
            elif za[t] >= z_in: cur = -1
        else:
            if abs(za[t]) < z_out: cur = 0
            elif hard_stop and abs(za[t]) > z_stop: cur = 0          # cut divergence (DD control)
        pos[t] = cur
    posx = np.concatenate([[0.0], pos[:-1]])
    sret = dla - beta.shift(1)*dlb
    gross = posx*np.nan_to_num(sret.values)
    tc = np.abs(np.diff(np.concatenate([[0.0], posx])))*(rt/2.0)
    fin = np.where(posx > 0, finL, np.where(posx < 0, finS, 0.0))*trip
    net = pd.Series(gross - tc + fin, index=idx)   # fin is SIGNED (negative=cost) -> ADD it
    longm = net.where(posx > 0); shortm = net.where(posx < 0)
    return net, dict(long_t=st.hac_tstat(longm[posx > 0].dropna().values) if (posx > 0).sum() > 10 else 0,
                     short_t=st.hac_tstat(shortm[posx < 0].dropna().values) if (posx < 0).sum() > 10 else 0,
                     long_mean_bps=float(longm[posx > 0].mean()*1e4) if (posx > 0).any() else 0,
                     short_mean_bps=float(shortm[posx < 0].mean()*1e4) if (posx < 0).any() else 0,
                     n_trades=int((np.abs(np.diff(np.concatenate([[0.0], posx]))) > 0).sum()//2))


def factor_residual(target, basket, s_in=1.25, s_out=0.5, swap_mult=1.0):
    syms = [target]+basket
    panel = D.close_panel(syms, "D"); rets = np.log(panel).diff()
    bret = rets[basket].mean(axis=1)                             # equal-weight basket return
    beta = roll_beta(rets[target], bret, 252)
    resid = rets[target] - beta*bret                            # idiosyncratic return
    X = resid.cumsum(); s = (X - X.rolling(60).mean())/X.rolling(60).std()   # s-score (OU proxy)
    idx = panel.index; n = len(idx)
    rt = (C.rt_cost_bps(target) + np.mean([C.rt_cost_bps(b) for b in basket]))/1e4
    swL = (C.swap_bps_night(target, "long") + np.mean([C.swap_bps_night(b, "short") for b in basket]))*swap_mult/1e4
    swS = (C.swap_bps_night(target, "short") + np.mean([C.swap_bps_night(b, "long") for b in basket]))*swap_mult/1e4
    trip = np.where(idx.weekday == C.TRIPLE_DOW[target], 3.0, 1.0)
    sa = s.values; pos = np.zeros(n); cur = 0
    for t in range(n):
        if np.isnan(sa[t]): pos[t] = 0; cur = 0; continue
        if cur == 0:
            if sa[t] <= -s_in: cur = 1
            elif sa[t] >= s_in: cur = -1
        elif abs(sa[t]) < s_out: cur = 0
        pos[t] = cur
    posx = np.concatenate([[0.0], pos[:-1]])
    rret = (rets[target] - beta.shift(1)*bret)                  # market-neutral residual P&L
    gross = posx*np.nan_to_num(rret.values)
    tc = np.abs(np.diff(np.concatenate([[0.0], posx])))*(rt/2.0)
    fin = np.where(posx > 0, swL, np.where(posx < 0, swS, 0.0))*trip
    net = pd.Series(gross - tc + fin, index=idx)   # fin is SIGNED (negative=cost) -> ADD it
    longm, shortm = net.where(posx > 0), net.where(posx < 0)
    # OOS coint of residual (ADF on second half)
    Xv = X.dropna().values; half = len(Xv)//2
    p_oos = adfuller(Xv[half:], maxlag=1, autolag=None)[1] if len(Xv) > 100 else 1.0
    return net, dict(short_t=st.hac_tstat(shortm[posx < 0].dropna().values) if (posx < 0).sum() > 10 else 0,
                     long_mean_bps=float(longm[posx > 0].mean()*1e4) if (posx > 0).any() else 0,
                     short_mean_bps=float(shortm[posx < 0].mean()*1e4) if (posx < 0).any() else 0,
                     resid_adf_oos=float(p_oos), n_trades=int((np.abs(np.diff(np.concatenate([[0.0], posx]))) > 0).sum()//2))


def main():
    res = {}
    # H1 gold/silver: with and without hard z-stop, vol-targeted
    for hs in [False, True]:
        net, legs = gold_silver(hard_stop=hs)
        bvt = voltarget(net, 0.10, 1.5)
        b = stats_block(bvt.dropna()); b.update(legs)
        res[f"H1_goldsilver_hardstop={hs}"] = b
        if hs:
            bvt.rename("ret").dropna().to_csv(f"{OUT}/H1_goldsilver_returns.csv")
    # H2 Avellaneda-Lee residual: each index vs basket of the other three
    idxs = ["US100", "US500", "US30", "GER40"]
    resid_books = []
    for tgt in idxs:
        net, legs = factor_residual(tgt, [x for x in idxs if x != tgt])
        b = stats_block(net.dropna()); b.update(legs)
        res[f"H2_resid_{tgt}"] = b
        resid_books.append(net)
    # H2 portfolio (equal-weight residual book), vol-targeted
    book = pd.concat(resid_books, axis=1).fillna(0.0).mean(axis=1)
    bvt = voltarget(book, 0.10, 1.5)
    res["H2_resid_PORTFOLIO"] = stats_block(bvt.dropna())
    bvt.rename("ret").dropna().to_csv(f"{OUT}/H2_resid_portfolio_returns.csv")
    out = {k: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()} for k, v in res.items()}
    json.dump(out, open(f"{OUT}/summary.json", "w"), indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
