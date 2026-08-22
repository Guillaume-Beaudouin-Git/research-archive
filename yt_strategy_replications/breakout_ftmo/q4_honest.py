"""
HONEST rerun after the audit caught a bug: the engine max_hold (session-bar count) let
positions cross the overnight boundary (captured overnight drift -> inflated SR + beta leak).
This backtester FORCE-FLATTENS at the last session bar of the ENTRY day (true intraday-flat).
Recompute the two-sided book net/skew/WF/drift-control. One position at a time.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as sstats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
from engine import stats as S, indicators as ind

CACHE = HERE / "_cache"
DIGITS = {"US100": 2, "US500": 2, "GER40": 2, "XAUUSD": 2, "EURUSD": 5, "GBPUSD": 5}
BOOK = ["GER40", "XAUUSD", "EURUSD", "GBPUSD"]; CONTROL = ["US100", "US500"]
FXSET = {"EURUSD", "GBPUSD"}
PPY = 252.0; N_TRIALS = 145
STRESS = {"idx": 0.0002, "fx": 0.0001}


def backtest_eod(d, N, sl_mult=1.0, tp_mult=3.0):
    o = d["open"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy(); c = d["close"].to_numpy()
    rh = d["high"].rolling(N).max().shift(1).to_numpy()
    rl = d["low"].rolling(N).min().shift(1).to_numpy()
    atr = ind.atr(d["high"], d["low"], d["close"], n=N).to_numpy()
    sd = d.index.normalize().to_numpy()
    last_of_day = np.append(sd[:-1] != sd[1:], True)
    n = len(c); i = 0
    et, xt, dr, ret, reason = [], [], [], [], []
    while i < n - 1:
        sig = 1 if (np.isfinite(rh[i]) and c[i] > rh[i]) else (-1 if (np.isfinite(rl[i]) and c[i] < rl[i]) else 0)
        if sig != 0 and np.isfinite(atr[i]) and atr[i] > 0:
            e = i + 1; entry = o[e]; a = atr[i]
            sl = entry - sig * sl_mult * a; tp = entry + sig * tp_mult * a
            j = e; xpx = c[e]; rs = "eod"
            while j < n:
                if sig > 0:
                    hsl, htp = l[j] <= sl, h[j] >= tp
                else:
                    hsl, htp = h[j] >= sl, l[j] <= tp
                if hsl: xpx, rs = sl, "sl"; break
                if htp: xpx, rs = tp, "tp"; break
                if last_of_day[j] or sd[j] != sd[e]:
                    xpx, rs = c[j], "eod"; break
                j += 1
            et.append(e); xt.append(j); dr.append(sig); ret.append(sig * (xpx / entry - 1.0)); reason.append(rs)
            i = max(j, e)
        else:
            i += 1
    return pd.DataFrame({"entry_t": d.index[et], "exit_t": d.index[xt], "dir": dr,
                         "ret_gross": ret, "reason": reason})


def daily(tr, c, days):
    if tr.empty: return pd.Series(0.0, index=days)
    r = tr["ret_gross"].to_numpy() - c
    day = pd.DatetimeIndex(tr["exit_t"]).normalize()
    return pd.Series(r, index=day).groupby(level=0).sum().reindex(days, fill_value=0.0)


def bh(d):
    r = d["close"].pct_change().fillna(0.0)
    return S.sharpe_ratio(r.groupby(d.index.normalize()).sum().to_numpy(), PPY)


def one(sym, freq, N):
    d = pd.read_parquet(CACHE / f"{sym}_{freq}.parquet")
    cls = "fx" if sym in FXSET else "idx"
    tr = backtest_eod(d, N)
    if len(tr) < 30: return None
    pt = 10.0 ** (-DIGITS[sym]); cost = float((d["spread"]*pt/d["close"]).replace(0, np.nan).median())
    days = pd.DatetimeIndex(d.index.normalize().unique())
    dn = daily(tr, cost, days); dS = daily(tr, STRESS[cls], days)
    rg = tr["ret_gross"].to_numpy()
    _, t = S.hac_tstat(dn.to_numpy(), 6)
    return dict(n=len(tr), netSR=S.sharpe_ratio(dn.to_numpy(), PPY), t=t,
                strSR=S.sharpe_ratio(dS.to_numpy(), PPY),
                wf=S.fold_metrics(dn.to_numpy(), 5, PPY)["wf_score"],
                legL=np.nanmean(rg[tr["dir"].to_numpy() > 0])*1e4,
                legS=np.nanmean(rg[tr["dir"].to_numpy() < 0])*1e4,
                skew=float(sstats.skew(rg)), tp=float((tr["reason"]=="tp").mean()),
                sl=float((tr["reason"]=="sl").mean()), eod=float((tr["reason"]=="eod").mean()),
                bh=bh(d), _dn=dn, _dS=dS)


if __name__ == "__main__":
    for freq, N in [("1h", 20), ("30min", 20), ("30min", 10)]:
        print(f"\n#### HONEST (force-flat EOD) — {freq} Donchian{N} ####")
        print(f"{'sym':6} | {'n':>5} {'netSR':>6} {'t':>5} {'strSR':>6} {'WF':>4} {'skew':>5} "
              f"{'legL':>6} {'legS':>6} {'tp%':>4} {'eod%':>4} | {'B&H':>5}")
        ser = []; serS = []
        for sym in BOOK + CONTROL:
            r = one(sym, freq, N)
            if r is None: print(f"{sym:6} | insufficient"); continue
            if sym in BOOK: ser.append(r["_dn"]); serS.append(r["_dS"])
            mark = "" if sym in BOOK else "  <-control(beta)"
            print(f"{sym:6} | {r['n']:>5} {r['netSR']:>+6.2f} {r['t']:>+5.1f} {r['strSR']:>+6.2f} "
                  f"{r['wf']:>4.0%} {r['skew']:>+5.1f} {r['legL']:>+6.1f} {r['legS']:>+6.1f} "
                  f"{r['tp']:>4.0%} {r['eod']:>4.0%} | {r['bh']:>+5.2f}{mark}")
        mat = pd.concat(ser, axis=1).fillna(0.0).mean(axis=1)
        matS = pd.concat(serS, axis=1).fillna(0.0).mean(axis=1)
        _, t = S.hac_tstat(mat.to_numpy(), 6)
        dsr = S.deflated_sharpe_ratio(mat.to_numpy(), n_trials=N_TRIALS, periods_per_year=PPY)
        wf = S.fold_metrics(mat.to_numpy(), 5, PPY)
        print(f"{'BOOK':6} | net SR {S.sharpe_ratio(mat.to_numpy(),PPY):+.2f} (HACt {t:+.1f}) "
              f"stressSR {S.sharpe_ratio(matS.to_numpy(),PPY):+.2f} WF {wf['wf_score']:.0%} "
              f"DSR(N=145) {dsr.get('dsr',float('nan')):.3f}")
    print("\ndone")
