"""Piste C iteration — Connors RSI2 mean-reversion, long-only above SMA200, on a 4-index portfolio,
vol-targeted + hard-stopped for FTMO-challenge DD control. Net of active-fill cost + overnight swap.
Signal at T-1, trade at T. Reference: Connors & Alvarez, 'Short-Term Trading Strategies That Work'.
"""
from __future__ import annotations
import os, sys, json, itertools
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lib import data as D, stats as st, ftmo_costs as C

OUT = os.path.dirname(os.path.abspath(__file__))
IDX = ["US100", "US500", "US30", "GER40"]
ANN = 252.0
TARGET_VOL, MAX_LEV = 0.08, 1.5


def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0); dn = (-d).clip(lower=0)
    au = up.ewm(alpha=1/n, adjust=False).mean(); ad = dn.ewm(alpha=1/n, adjust=False).mean()
    return (100 - 100/(1 + au/ad.replace(0, np.nan))).fillna(50)


def atr(df, n=14):
    h, l, c = df["high"], df["low"], df["close"]; pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()


def strat_returns(sym, df, entry, exit_mode, stop_atr, vol_filter=True, swap_mult=1.0):
    """Long-only Connors RSI2 with INTRADAY hard stop (modelled via the daily low) and a causal
    realized-vol regime filter. Returns daily net strategy return (unlevered, per-instrument)."""
    c = df["close"]; lc = np.log(c); ret = lc.diff().values
    sma200 = c.rolling(200).mean(); sma5 = c.rolling(5).mean()
    r2 = rsi(c, 2); cum = r2.rolling(2).sum(); af = (atr(df) / c).values
    lo = df["low"].values; op = df["open"].values; clv = c.values; idx = c.index; n = len(idx)
    up = (c > sma200).values
    sig = {"rsi5": r2 < 5, "rsi10": r2 < 10, "cum35": cum < 35, "cum50": cum < 50}[entry].values
    above5 = (c > sma5).values; r2v = r2.values
    # causal vol-regime filter: 20d realized vol below its trailing 252d 60th pctile
    rvol = pd.Series(ret, index=idx).rolling(20).std()
    volok = (rvol < rvol.rolling(252).quantile(0.60)).values if vol_filter else np.ones(n, bool)
    rt = C.rt_cost_bps(sym) / 1e4
    swL = C.swap_bps_night(sym, "long") * swap_mult / 1e4
    trip = np.where(idx.weekday == C.TRIPLE_DOW[sym], 3.0, 1.0)
    day_ret = np.zeros(n); pos = np.zeros(n); cur = 0; hold = 0; ep = np.nan; ea = np.nan
    for t in range(1, n):
        r_today = 0.0
        if cur == 1:                                    # holding into day t
            stop_level = ep * (1 - stop_atr * ea)
            if lo[t] <= stop_level:                      # intraday stop hit
                fill = min(op[t], stop_level)            # gap-through-stop: fill at open if it gaps below
                r_today = np.log(fill) - np.log(clv[t - 1]); cur = 0
            else:
                r_today = ret[t]; hold += 1
                ex = above5[t] if exit_mode == "sma5" else (r2v[t] > 70 if exit_mode == "rsi70" else hold >= 5)
                if ex or hold >= 15: cur = 0
            r_today += swL * trip[t]                      # overnight financing (swL is SIGNED, negative=cost)
            if cur == 0: r_today -= rt / 2.0             # exit cost
        if cur == 0 and up[t] and sig[t] and volok[t] and not np.isnan(af[t]):
            cur = 1; hold = 0; ep = clv[t]; ea = af[t]; r_today -= rt / 2.0   # enter at close t
        day_ret[t] = r_today; pos[t] = cur
    return pd.Series(day_ret, index=idx), pos


def portfolio(entry="rsi10", exit_mode="sma5", stop_atr=2.5):
    dfs = {s: D.load(s, "D") for s in IDX}
    rets, poss = {}, {}
    for s in IDX:
        r, p = strat_returns(s, dfs[s], entry, exit_mode, stop_atr)
        rets[s] = r; poss[s] = p
    R = pd.concat(rets, axis=1).fillna(0.0)
    book = R.mean(axis=1)                                  # equal-weight 4-index book
    # causal vol-target to TARGET_VOL
    rv = book.rolling(63).std() * np.sqrt(ANN)
    lev = (TARGET_VOL / rv).clip(upper=MAX_LEV).shift(1).fillna(0.0)
    bvt = book * lev
    presence = float(np.mean([np.mean(np.abs(p) > 0) for p in poss.values()]))
    return bvt.dropna(), presence


def stats_block(r):
    r = r[r != 0].reindex(r.index).fillna(0.0) if (r == 0).all() else r
    eq = (1 + r).cumprod(); dd = (eq/eq.cummax() - 1)
    return dict(sharpe=st.sharpe(r.values), hac_t=st.hac_tstat(r.values),
                ann_ret=(1+r.mean())**ANN - 1, ann_vol=r.std()*np.sqrt(ANN),
                maxdd=float(dd.min()), worst_day=float(r.min()), best_day=float(r.max()),
                daily_dd_p999=float(r.quantile(0.001)), skew=float(r.skew()),
                pct_days_in=float((r != 0).mean()), n=int(len(r)))


def main():
    grid = list(itertools.product(["rsi5", "rsi10", "cum35", "cum50"], ["sma5", "rsi70", "time5"], [1.5, 2.5]))
    rows, sr_all, cells = [], [], []
    for e, x, s in grid:
        bvt, pres = portfolio(e, x, s)
        b = stats_block(bvt); b.update(entry=e, exit=x, stop=s, presence=round(pres, 3))
        rows.append(b); sr_all.append(bvt.mean()/bvt.std() if bvt.std() > 0 else 0)
        cells.append(dict(b, _r=bvt))
    df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    df.to_csv(f"{OUT}/grid.csv", index=False)
    ok = df[(df.sharpe > 0.5) & (df.maxdd > -0.10) & (df.worst_day > -0.05)]
    # pick most ROBUST challenge cell: highest Sharpe among those with maxdd>-9% & worst_day>-4.5%
    robust = df[(df.sharpe > 0.5) & (df.maxdd > -0.09) & (df.worst_day > -0.045)].sort_values("sharpe", ascending=False)
    pick = robust.iloc[0] if len(robust) else (ok.sort_values("sharpe", ascending=False).iloc[0] if len(ok) else df.sort_values("sharpe", ascending=False).iloc[0])
    best_cell = next(cc for cc in cells if cc["entry"] == pick["entry"] and cc["exit"] == pick["exit"] and cc["stop"] == pick["stop"])
    best_cell["_r"].rename("ret").to_csv(f"{OUT}/best_daily_returns.csv")            # for challenge sim
    from scipy import stats as sps
    rr = best_cell["_r"]; rr = rr[rr != 0].dropna()
    dsr, _ = st.deflated_sharpe(sr_all, rr.mean()/rr.std(), len(rr),
                                float(sps.skew(rr.values)), float(sps.kurtosis(rr.values, fisher=False)))
    summary = dict(n_trials=len(grid), target_vol=TARGET_VOL,
                   cells_sharpe_gt_0p5=int((df.sharpe > 0.5).sum()),
                   cells_challenge_ok=int(len(ok)),
                   chosen={k: (round(float(pick[k]), 4) if isinstance(pick[k], (int, float, np.floating)) else pick[k])
                           for k in ["entry", "exit", "stop", "sharpe", "hac_t", "ann_ret", "ann_vol",
                                     "maxdd", "worst_day", "presence"]},
                   chosen_dsr=round(float(dsr), 3),
                   challenge_ok=bool(pick["sharpe"] > 0.5 and pick["maxdd"] > -0.10 and pick["worst_day"] > -0.05))
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    print("\n=== GRID (sorted by Sharpe) ===")
    print(df.sort_values("sharpe", ascending=False)[
        ["entry", "exit", "stop", "sharpe", "hac_t", "ann_ret", "ann_vol", "maxdd", "worst_day",
         "presence"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
