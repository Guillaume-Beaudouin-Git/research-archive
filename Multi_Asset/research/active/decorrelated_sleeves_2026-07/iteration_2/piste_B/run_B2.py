"""Piste B iteration — amplitude-filtered range fade. Attacks iteration-1's cost-death:
fade Bollinger extremes only when (a) low-ADX range regime is on (causal), (b) a causal vol-persistence
flag is on, and (c) the band width >= amp_k x round-trip cost (so reversion amplitude clears cost).
Higher-amplitude instruments only (gold + indices). Intraday-flat (no swap). Event-driven. T-1/T.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lib import data as D, stats as st, ftmo_costs as C

OUT = os.path.dirname(os.path.abspath(__file__)); ANN_H = 24*252.0; TIME_STOP = 8
SYMS = ["XAUUSD", "US100", "US500", "GER40"]


def wil(x, n): return x.ewm(alpha=1/n, adjust=False).mean()


def precompute(sym, df):
    c = df["close"]; ret = np.log(c).diff().values
    h, l, cc = df["high"], df["low"], df["close"]; pc = cc.shift(1)
    up = h.diff().clip(lower=0); dn = (-l.diff()).clip(lower=0)
    up = up.where(up > dn, 0.0); dn = dn.where(dn > up, 0.0)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1); atr = wil(tr, 14)
    pdi = 100*wil(up, 14)/atr; mdi = 100*wil(dn, 14)/atr
    dx = 100*(pdi-mdi).abs()/(pdi+mdi).replace(0, np.nan); adx = wil(dx.fillna(0), 14).values
    rvol = pd.Series(ret, index=c.index).rolling(24).std()
    volpersist = (rvol < rvol.rolling(500).median()).values           # causal vol-persistence
    sma = c.rolling(20).mean(); sd = c.rolling(20).std()
    return dict(ret=ret, adx=adx, volp=volpersist, sma=sma.values, sd=sd.values,
                cl=c.values, op=df["open"].values, lo=l.values, hi=h.values,
                day=c.index.normalize().values, idx=c.index)


def backtest(sym, pc, band_sig, adx_thr, amp_k, zero_cost=False):
    ret, adx, volp = pc["ret"], pc["adx"], pc["volp"]; sma, sd = pc["sma"], pc["sd"]
    cl, op, lo, hi, day, idx = pc["cl"], pc["op"], pc["lo"], pc["hi"], pc["day"], pc["idx"]
    n = len(idx); rtf = C.rt_cost_bps(sym)/1e4
    upper = sma + band_sig*sd; lower = sma - band_sig*sd
    bw = (upper-lower)/sma                                              # band width (fraction)
    amp_ok = bw >= amp_k*rtf                                            # amplitude filter
    regime = np.concatenate([[False], ((adx[:-1] < adx_thr) & volp[:-1] & amp_ok[:-1])])  # known at T-1
    entS = regime & (cl >= upper); entL = regime & (cl <= lower)
    cand = np.where(entL | entS)[0]
    pos = np.zeros(n); exit_ptr = 0; rt = 0.0 if zero_cost else rtf
    for e in cand:
        if e < exit_ptr or e == 0: continue
        d = 1 if entL[e] else -1; x = e+1
        while x < n:
            if day[x] != day[x-1]: break
            broke = (cl[x] > upper[x]) if d < 0 else (cl[x] < lower[x])
            revert = (cl[x] <= sma[x]) if d < 0 else (cl[x] >= sma[x])
            if broke or revert or (x-e) >= TIME_STOP: break
            x += 1
        pos[e:x] = d; exit_ptr = x
    posx = np.concatenate([[0.0], pos[:-1]])
    gross = posx*np.nan_to_num(ret)
    tc = np.abs(np.diff(np.concatenate([[0.0], posx])))*(rt/2.0)
    net = pd.Series(gross - tc, index=idx)
    n_tr = int((np.abs(np.diff(np.concatenate([[0.0], posx]))) > 0).sum()//2)
    longm, shortm = net.where(posx > 0), net.where(posx < 0)
    daily = net.groupby(net.index.normalize()).sum()          # HONEST: daily P&L over all calendar days
    gpt = float(np.nan_to_num(gross)[posx != 0].sum()/max(n_tr, 1)*1e4)
    eq = (1+daily).cumprod(); mdd = float((eq/eq.cummax()-1).min())
    return dict(sym=sym, band=band_sig, adx=adx_thr, amp_k=amp_k, n_trades=n_tr,
                net_sharpe=st.sharpe(daily.values, 252.0) if len(daily) > 5 else 0,
                maxdd=mdd, worst_day=float(daily.min()),
                gross_per_trade_bps=gpt, cost_bps=C.rt_cost_bps(sym), gross_cost_ratio=gpt/C.rt_cost_bps(sym),
                long_bps=float(longm[posx > 0].mean()*1e4) if (posx > 0).any() else 0,
                short_bps=float(shortm[posx < 0].mean()*1e4) if (posx < 0).any() else 0,
                two_sided=bool((longm[posx > 0].mean() if (posx > 0).any() else -1) >= 0
                               and (shortm[posx < 0].mean() if (posx < 0).any() else -1) >= 0))


def main():
    rows = []
    for s in SYMS:
        pc = precompute(s, D.load(s, "H"))
        for band in [2.0, 2.5]:
            for adx_thr in [20, 25]:
                for amp_k in [3.0, 5.0, 8.0]:
                    rows.append(backtest(s, pc, band, adx_thr, amp_k))
    df = pd.DataFrame(rows); df.to_csv(f"{OUT}/grid.csv", index=False)
    summ = dict(n_trials=len(df),
                cells_net_sharpe_gt_0p5=int((df.net_sharpe > 0.5).sum()),
                cells_gross_cost_ge3=int((df.gross_cost_ratio >= 3).sum()),
                cells_twosided_and_sharpe=int(((df.two_sided) & (df.net_sharpe > 0.5)).sum()),
                best_net_sharpe=float(df.net_sharpe.max()),
                best=df.loc[df.net_sharpe.idxmax()][["sym", "band", "adx", "amp_k", "net_sharpe",
                     "gross_cost_ratio", "n_trades", "short_bps", "two_sided"]].to_dict())
    json.dump(summ, open(f"{OUT}/summary.json", "w"), indent=2, default=str)
    print(json.dumps(summ, indent=2, default=str))
    print("\n=== top cells by net Sharpe ===")
    print(df.sort_values("net_sharpe", ascending=False).head(12)[
        ["sym", "band", "adx", "amp_k", "n_trades", "net_sharpe", "gross_cost_ratio",
         "long_bps", "short_bps", "two_sided"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
