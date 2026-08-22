"""Piste C — daily/multi-day MR on indices after excess. Executes frozen PREREGISTRATION.md.

Excess: RSI(2), RSI(14), Bollinger %b(20,2). Long oversold / short overbought; exit on reversion,
10d time-stop, or 2xATR hard stop. NET of active-fill cost + asymmetric overnight swap.
DECISIVE two-sided test: does the SHORT leg pay, and does the LONG leg beat unconditional drift?
Signal at T-1, execute at T. No look-ahead.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import data as D, stats as st, ftmo_costs as C

OUT = os.path.dirname(os.path.abspath(__file__))
SYMS = ["US100", "US500", "US30", "GER40", "XAUUSD", "EURUSD", "USDJPY"]
ANN = 252.0


def rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0); dn = (-d).clip(lower=0.0)
    au = up.ewm(alpha=1.0 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()


def signals(df: pd.DataFrame, defn: str, tight: bool):
    """Return (entry_long, entry_short, exit_flat) boolean series for an excess definition."""
    c = df["close"]
    if defn == "RSI2":
        r = rsi(c, 2); lo, hi = (5, 95) if tight else (10, 90)
        return r < lo, r > hi, (r.between(45, 55))
    if defn == "RSI14":
        r = rsi(c, 14); lo, hi = (25, 75) if tight else (30, 70)
        return r < lo, r > hi, (r.between(45, 55))
    if defn == "BOLL":
        sma = c.rolling(20).mean(); sd = c.rolling(20).std()
        up, dn = sma + 2 * sd, sma - 2 * sd
        pb = (c - dn) / (up - dn)
        lo, hi = (-0.1, 1.1) if tight else (0.0, 1.0)
        return pb < lo, pb > hi, pb.between(0.4, 0.6)
    raise ValueError(defn)


def backtest(sym, df, defn, tight, exit_mode, slip_mult=1.0, swap_mult=1.0):
    c = df["close"]; lc = np.log(c); ret = lc.diff()
    a = atr(df); idx = c.index
    eL, eS, exr = signals(df, defn, tight)
    eL, eS, exr = eL.values, eS.values, exr.values
    aatr = (a / c).values                       # atr as fraction of price
    rt = C.rt_cost_bps(sym, slip_mult) / 1e4
    swL = C.swap_bps_night(sym, "long") * swap_mult / 1e4
    swS = C.swap_bps_night(sym, "short") * swap_mult / 1e4
    trip = np.where(idx.weekday == C.TRIPLE_DOW[sym], 3.0, 1.0)
    pos = np.zeros(len(idx)); cur = 0; hold = 0; entry_px = np.nan; entry_atr = np.nan
    cl = c.values
    for t in range(len(idx)):
        if cur == 0:
            if eL[t]: cur = +1; hold = 0; entry_px = cl[t]; entry_atr = aatr[t]
            elif eS[t]: cur = -1; hold = 0; entry_px = cl[t]; entry_atr = aatr[t]
        else:
            hold += 1
            adverse = (cl[t] / entry_px - 1.0) * cur          # signed move in our favour
            hard_stop = adverse <= -2.0 * (entry_atr if entry_atr == entry_atr else 0.01)
            time_stop = hold >= 10
            revert = exr[t]
            if hard_stop or (time_stop if exit_mode == "time" else revert) or (time_stop and exit_mode == "revert"):
                cur = 0
        pos[t] = cur
    pos = pd.Series(pos, index=idx); posx = pos.shift(1).fillna(0)
    gross = posx * ret
    tc = posx.diff().abs().fillna(0) * (rt / 2.0)
    sw = np.where(posx > 0, swL, np.where(posx < 0, swS, 0.0)) * trip
    net = gross - tc + pd.Series(sw, index=idx)   # sw is SIGNED (negative=cost) -> ADD it
    longm = net.where(posx > 0); shortm = net.where(posx < 0)
    uncond = ret.mean()                                       # unconditional daily drift
    n_tr = int((posx.diff().abs() > 0).sum() // 2)
    book = net[posx != 0].reindex(idx).fillna(0.0)
    stt = st.annualized_stats(book)
    return dict(sym=sym, defn=defn, tight=tight, exit=exit_mode, n_trades=n_tr,
                net_sharpe=stt["sharpe"], hac_t=stt["hac_t"], maxdd=stt["maxdd"], skew=stt["skew"],
                long_n=int((posx > 0).sum()), short_n=int((posx < 0).sum()),
                long_mean_bps=float(longm[posx > 0].mean() * 1e4) if (posx > 0).any() else 0.0,
                short_mean_bps=float(shortm[posx < 0].mean() * 1e4) if (posx < 0).any() else 0.0,
                long_t=st.hac_tstat(longm[posx > 0].dropna().values) if (posx > 0).sum() > 10 else 0.0,
                short_t=st.hac_tstat(shortm[posx < 0].dropna().values) if (posx < 0).sum() > 10 else 0.0,
                uncond_bps=float(uncond * 1e4),
                long_beats_drift=bool((longm[posx > 0].mean() if (posx > 0).any() else -1) > uncond),
                _net=book, _sr=(book.mean() / book.std() if book.std() > 0 else 0.0))


def main():
    rows, sr_all, best = [], [], None
    dfs = {s: D.load(s, "D") for s in SYMS}
    for s in SYMS:
        for defn in ["RSI2", "RSI14", "BOLL"]:
            for tight in [False, True]:
                for exm in ["revert", "time"]:
                    r = backtest(s, dfs[s], defn, tight, exm)
                    sr_all.append(r["_sr"])
                    rows.append({k: v for k, v in r.items() if not k.startswith("_")})
                    two_sided = r["short_mean_bps"] >= 0 and r["short_t"] > -1 and r["long_beats_drift"]
                    if two_sided and (best is None or r["net_sharpe"] > best["net_sharpe"]):
                        best = dict(rows[-1], _net=r["_net"])
    df = pd.DataFrame(rows); df.to_csv(f"{OUT}/backtest_grid.csv", index=False)
    # aggregate short-leg verdict across the whole space
    shortpos = (df["short_mean_bps"] > 0).sum()
    shortpos_sig = ((df["short_mean_bps"] > 0) & (df["short_t"] > 2.0)).sum()
    longbeat = df["long_beats_drift"].sum()
    dsr = None
    if best is not None:
        from scipy import stats as sps
        nz = best["_net"]; nz = nz[nz != 0].dropna()
        d, star = st.deflated_sharpe(sr_all, nz.mean() / nz.std(), len(nz),
                                     float(sps.skew(nz.values)), float(sps.kurtosis(nz.values, fisher=False)))
        dsr = float(d)
    summary = dict(n_trials=len(df),
                   short_leg_netpos=f"{shortpos}/{len(df)}",
                   short_leg_netpos_significant=f"{shortpos_sig}/{len(df)}",
                   long_beats_uncond_drift=f"{longbeat}/{len(df)}",
                   best_two_sided=None if best is None else {k: best[k] for k in
                       ["sym", "defn", "tight", "exit", "net_sharpe", "hac_t", "short_mean_bps",
                        "short_t", "long_mean_bps", "uncond_bps", "n_trades", "maxdd"]},
                   best_dsr=dsr)
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    print("\n=== SHORT-LEG (overbought fade) BY INSTRUMENT — the decisive two-sided test ===")
    piv = df.groupby("sym").agg(short_mean_bps=("short_mean_bps", "mean"),
                                short_t=("short_t", "mean"),
                                long_mean_bps=("long_mean_bps", "mean"),
                                uncond_bps=("uncond_bps", "first")).round(2)
    print(piv.to_string())
    print("\n=== TOP NET-SHARPE CELLS ===")
    print(df.sort_values("net_sharpe", ascending=False).head(10)[
        ["sym", "defn", "tight", "exit", "n_trades", "net_sharpe", "hac_t",
         "long_mean_bps", "short_mean_bps", "short_t", "long_beats_drift"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
