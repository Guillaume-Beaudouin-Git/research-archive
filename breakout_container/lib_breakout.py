"""Donchian breakout on AUDITED data (deep_history_utc M1 -> 1h OHLC), force-flat true-EOD,
two-sided. Independent reimplementation of the Cowork q4_honest spec on the audited source
(NOT the Cowork _cache). Emits per-instrument + pooled daily (net, low) at two cost levels,
for the funded-container injection. Read-only on main-dir data."""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats as sstats

MAIN = "<HOME>/Desktop/Algo_claude"
DH = f"{MAIN}/data/deep_history_utc"
DIGITS = {"GER40": 2, "XAUUSD": 2, "EURUSD": 5, "GBPUSD": 5}
FXSET = {"EURUSD", "GBPUSD"}
SESS = {"fx": range(7, 16), "idx": range(13, 20)}      # UTC hours: FX 07-16, idx 13:30-20:00
STRESS = {"idx": 0.0002, "fx": 0.0001}                  # realistic 2bp idx / 1bp fx
PPY = 252.0

def _cls(sym): return "fx" if sym in FXSET else "idx"

def load_1h(sym):
    df = pd.read_csv(f"{DH}/{sym}_M1.csv")
    df["ts"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.set_index("ts").sort_index()
    o = df["open"].resample("1h").first(); h = df["high"].resample("1h").max()
    l = df["low"].resample("1h").min(); c = df["close"].resample("1h").last()
    sp = df["spread"].resample("1h").mean()
    d = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "spread": sp}).dropna()
    d = d[[hh in SESS[_cls(sym)] for hh in d.index.hour]]               # session filter
    return d

def atr(h, l, c, n=20):
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()

def backtest_eod(d, N=20, sl_mult=1.0, tp_mult=3.0):
    """Returns (trades df, per-bar same-day cumulative gross MTM series). One position at a time,
    pessimistic SL tie-break, force-flat at last session bar of the entry day."""
    o = d["open"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy(); c = d["close"].to_numpy()
    rh = d["high"].rolling(N).max().shift(1).to_numpy(); rl = d["low"].rolling(N).min().shift(1).to_numpy()
    a = atr(d["high"], d["low"], d["close"], N).to_numpy()
    sd = d.index.normalize().to_numpy(); last_of_day = np.append(sd[:-1] != sd[1:], True)
    n = len(c); i = 0
    et, xt, dr, ret, reason = [], [], [], [], []
    mtm = np.zeros(n)                      # per-bar same-day cumulative gross P&L (realized today + open MTM)
    day_real = 0.0; cur_day = sd[0]
    while i < n - 1:
        if sd[i] != cur_day: cur_day = sd[i]; day_real = 0.0
        sig = 1 if (np.isfinite(rh[i]) and c[i] > rh[i]) else (-1 if (np.isfinite(rl[i]) and c[i] < rl[i]) else 0)
        if sig != 0 and np.isfinite(a[i]) and a[i] > 0:
            e = i + 1; entry = o[e]; aa = a[i]
            sl = entry - sig * sl_mult * aa; tp = entry + sig * tp_mult * aa
            j = e; xpx = c[e]; rs = "eod"
            while j < n:
                if sd[j] != sd[e]:           # safety: never cross day (force-flat at prior close)
                    j -= 1; xpx, rs = c[j], "eod"; break
                hsl = (l[j] <= sl) if sig > 0 else (h[j] >= sl)
                htp = (h[j] >= tp) if sig > 0 else (l[j] <= tp)
                mtm[j] = day_real + sig * (c[j] / entry - 1.0)        # mark open position at bar close
                if hsl: xpx, rs = sl, "sl"; break
                if htp: xpx, rs = tp, "tp"; break
                if last_of_day[j]: xpx, rs = c[j], "eod"; break
                j += 1
            tr_ret = sig * (xpx / entry - 1.0)
            day_real += tr_ret; mtm[j] = day_real
            et.append(e); xt.append(j); dr.append(sig); ret.append(tr_ret); reason.append(rs)
            i = max(j, e)
        else:
            mtm[i] = day_real; i += 1
    trades = pd.DataFrame({"entry_t": d.index[et], "exit_t": d.index[xt], "dir": dr,
                           "ret_gross": ret, "reason": reason})
    return trades, pd.Series(mtm, index=d.index)

def daily_net(trades, cost, days):
    if trades.empty: return pd.Series(0.0, index=days)
    r = trades["ret_gross"].to_numpy() - cost
    day = pd.DatetimeIndex(trades["exit_t"]).normalize()
    return pd.Series(r, index=day).groupby(level=0).sum().reindex(days, fill_value=0.0)

def cost_lb(d, sym):                                   # lower-bound = median spread/close
    pt = 10.0 ** (-DIGITS[sym]); return float((d["spread"] * pt / d["close"]).replace(0, np.nan).median())

def sharpe(x): x = np.asarray(x); return x.mean() / x.std(ddof=1) * np.sqrt(PPY) if x.std() > 0 else 0.0

def hac_t(x, lag=6):
    import statsmodels.api as sm
    x = np.asarray(x, float)
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(m.tvalues[0])

def dsr(x, n_trials=145):
    """Deflated Sharpe (Bailey-Lopez de Prado)."""
    x = np.asarray(x, float); T = len(x); sr = x.mean() / x.std(ddof=1) if x.std() > 0 else 0.0
    g3 = sstats.skew(x); g4 = sstats.kurtosis(x, fisher=False)
    from scipy.stats import norm
    emax = (1 - np.euler_gamma) * norm.ppf(1 - 1.0/n_trials) + np.euler_gamma * norm.ppf(1 - 1.0/(n_trials*np.e))
    sr0 = (x.std(ddof=1) * 0 + emax) / np.sqrt(T)      # SR0 in per-period units ~ emax/sqrt(T)
    num = (sr - sr0) * np.sqrt(T - 1)
    den = np.sqrt(1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2)
    return float(norm.cdf(num / den)) if den > 0 else np.nan

def bh_sharpe(d):
    r = d["close"].pct_change().fillna(0.0)
    return sharpe(r.groupby(d.index.normalize()).sum().to_numpy())

def per_instrument(sym, N=20):
    d = load_1h(sym); tr, mtm = backtest_eod(d, N)
    days = pd.DatetimeIndex(d.index.normalize().unique())
    clb = cost_lb(d, sym); cst = STRESS[_cls(sym)]
    dn_lb = daily_net(tr, clb, days); dn_rl = daily_net(tr, cst, days)
    rg = tr["ret_gross"].to_numpy()
    return dict(sym=sym, n=len(tr), d=d, trades=tr, mtm=mtm, days=days, cost_lb=clb, cost_rl=cst,
                dn_lb=dn_lb, dn_rl=dn_rl,
                netSR=sharpe(dn_lb.to_numpy()), t=hac_t(dn_lb.to_numpy()), strSR=sharpe(dn_rl.to_numpy()),
                skew=float(sstats.skew(rg)), legL=np.nanmean(rg[tr["dir"]>0])*1e4, legS=np.nanmean(rg[tr["dir"]<0])*1e4,
                eod=float((tr["reason"]=="eod").mean()), tp=float((tr["reason"]=="tp").mean()),
                bh=bh_sharpe(d))

def pooled_series(insts, cost="lb"):
    """Equal-weight pooled daily (net, low) across instruments. low = min intraday pooled cumulative
    gross MTM (bar-by-bar, ffill within day), <=0. Returns DataFrame [net, low] on union of book days."""
    union_days = sorted(set().union(*[set(r["days"]) for r in insts]))
    union_days = pd.DatetimeIndex(union_days)
    nets = [(r["dn_lb"] if cost == "lb" else r["dn_rl"]).reindex(union_days, fill_value=0.0) for r in insts]
    net = pd.concat(nets, axis=1).mean(axis=1)
    # pooled intraday mtm: union 1h grid, per-instrument ffill within day from 0
    grid = sorted(set().union(*[set(r["mtm"].index) for r in insts]))
    grid = pd.DatetimeIndex(grid)
    cols = []
    for r in insts:
        s = r["mtm"].reindex(grid)
        day = pd.Series(grid.normalize(), index=grid)
        s = s.groupby(day).ffill().fillna(0.0)         # carry last same-day mark; 0 before first / out-of-session
        cols.append(s)
    pooled_mtm = pd.concat(cols, axis=1).mean(axis=1)
    low = pooled_mtm.groupby(pooled_mtm.index.normalize()).min().clip(upper=0.0).reindex(union_days, fill_value=0.0)
    return pd.DataFrame({"net": net, "low": low})
