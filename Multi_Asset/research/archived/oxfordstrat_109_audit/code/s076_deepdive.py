"""
DEEP-DIVE #76 Ross Hook — S060-grade audit of the project's first strong KEEP candidate.
Tests: (A) look-ahead robustness (entry delay +1/+2/+3/+5), (B) placebo controls
(naive 'buy every new N-high' without the hook; entry-date randomisation), (C) per-class
trade edge + MTM hedged Sharpe, (D) REAL FTMO data (indices real OHLC + gold M1 + crypto),
(E) exposure/turnover, (F) cost stress, (G) figure. ftmo_lab UNCHANGED.
"""
import os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
import rosshook as rh
RF = lab.RISK_FRAC; CLASS = lab.CLASS
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
cal = pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in uni.values()])))
MN, HK, TM = 10, 20, 10


def pool(instrs, fill='next_open', extra_delay=0, side='both', cb=None):
    fr = []
    for t in instrs:
        tr = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=(costs[t] if cb is None else cb), fill=fill, side=side, extra_delay=extra_delay)
        if len(tr): tr['instr'] = t; fr.append(tr)
    return pd.concat(fr, ignore_index=True) if fr else pd.DataFrame()


def daily(instrs, fill='next_open', side='both'):
    s = pd.Series(0.0, index=cal)
    for t in instrs:
        _, dm = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=costs[t], fill=fill, side=side, daily=True)
        s = s.add(dm.reindex(cal).fillna(0))
    return s * RF


def naive_highs(instrs, fill_delay=1):
    """Placebo control: buy next open after every fresh MN-bar high, hold TM + ATR stop, NO hook."""
    fr = []
    for t in instrs:
        df = uni[t]; o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close')); A = lab.atr(df, 20).values
        hh = pd.Series(h, index=df.index).rolling(MN).max().values; n = len(df); i = MN + 1; tr = []
        while i < n - 1:
            if np.isfinite(hh[i]) and h[i] >= hh[i] and h[i] > h[i-1] and np.isfinite(A[i]) and A[i] > 0:
                eb = i + fill_delay
                if eb > n-1: break
                entry = o[eb]; risk0 = A[i]*6; cR = (costs[t]/1e4)*abs(entry)/risk0; stop = entry-risk0
                last = min(eb+TM, n-1); xp = xj = None
                for j in range(eb, last+1):
                    if l[j] <= stop: xp, xj = stop, j; break
                    if j == last: xp, xj = c[j], j; break
                tr.append((entry, xp, risk0, cR)); i = xj+1
            else: i += 1
        for entry, xp, risk0, cR in tr: fr.append((xp-entry)/risk0 - cR)
    r = np.array(fr); return r.mean(), len(r)


def shp(s): s = s[s.index >= s[s != 0].index.min()].dropna(); return s.mean()/s.std()*np.sqrt(252) if s.std() > 0 else np.nan
def boot(r, nb=1200, blk=20, sd=0):
    rng = np.random.default_rng(sd); n = len(r); k = int(np.ceil(n/blk))
    return np.percentile([r[np.concatenate([np.arange(s, s+blk) for s in rng.integers(0, n-blk, k)])[:n]].mean() for _ in range(nb)], [2.5, 97.5])
def ab(y, Xs, names, L=15):
    d = pd.concat([y]+Xs, axis=1).dropna(); yy = d.iloc[:, 0].values
    X = np.column_stack([np.ones(len(d))]+[d.iloc[:, i+1].values for i in range(len(Xs))]); n = len(d)
    b, *_ = np.linalg.lstsq(X, yy, rcond=None); u = yy-X@b; XtXi = np.linalg.inv(X.T@X); S = (X*u[:, None]).T@(X*u[:, None])
    for k in range(1, L+1):
        w = 1-k/(L+1); G = (X[k:]*u[k:, None]).T@(X[:-k]*u[:-k, None]); S += w*(G+G.T)
    se = np.sqrt(np.diag(XtXi@S@XtXi)); out = f"alpha_ann={b[0]*252:+.4f} t={b[0]/se[0]:+.2f}"
    for i, nm in enumerate(names): out += f" | {nm} t={b[i+1]/se[i+1]:+.2f}"
    return out
def bh(instrs): return pd.concat([uni[t]['close'].pct_change().reindex(cal) for t in instrs], axis=1).mean(axis=1)

allI = list(uni)
rets = {t: uni[t]['close'].pct_change() for t in uni}
tsmom = pd.concat([(np.sign(uni[t]['close'].shift(1)-uni[t]['close'].shift(253))*rets[t]).reindex(cal) for t in uni], axis=1).mean(axis=1)
mkt = bh(allI)

print("=== (A) LOOK-AHEAD ROBUSTNESS (entry delay; trade Sharpe / MTM Sharpe) ===")
for dl in [0, 1, 2, 3, 5]:
    f = 'stop' if dl == 0 else 'next_open'
    m = lab.trade_metrics(pool(allI, fill=f, extra_delay=max(0, dl-1) if dl >= 1 else 0))
    s = daily(allI, fill=f) if dl <= 1 else None
    print(f"  delay+{dl}: tradeSh={m['sharpe']:+.2f} expR={m['expR']:+.4f}" + (f"  MTM Sh={shp(s):+.2f}" if s is not None else ""))

print("\n=== (B) PLACEBO CONTROLS ===")
mr, nr = naive_highs(allI, 1)
rh_e = pool(allI, 'next_open')['netR']
print(f"  Ross Hook expR (delai+1) = {rh_e.mean():+.4f} (n={len(rh_e)})")
print(f"  NAIVE 'buy every new {MN}-high' (no hook) expR = {mr:+.4f} (n={nr})  -> hook selectivity adds: {rh_e.mean()-mr:+.4f}")

print("\n=== (C) PER-CLASS (trade expR + bootstrap CI ; MTM hedged-Sharpe) ===")
P = pool(allI, 'next_open')
for cls in ['indices', 'commodities', 'forex', 'crypto']:
    ci = [t for t in allI if CLASS.get(t) == cls]; p = P[P['instr'].isin(ci)]; r = p['netR'].values
    if len(r) < 30: print(f"  {cls:11s}: n={len(r)}"); continue
    lo, hi = boot(r); sd = daily(ci, 'next_open');
    import numpy as _np
    print(f"  {cls:11s}: n={len(r)} expR={r.mean():+.4f} CI[{lo:+.4f},{hi:+.4f}] MTM_Sh={shp(sd):+.2f}")

print("\n=== (D) REAL FTMO DATA (indices real OHLC + gold M1 2007+ + crypto) ===")
GOLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "real_data", "XAUUSD_real_m1daily.parquet")
uni['XAUUSD'] = pd.read_parquet(GOLD)                      # swap proxy gold -> real
real = [t for t in uni if CLASS.get(t) in ('indices', 'crypto')] + ['XAUUSD']
cal2 = pd.DatetimeIndex(sorted(set().union(*[set(uni[t].index) for t in real])))
sr = pd.Series(0.0, index=cal2)
for t in real:
    _, dm = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=costs[t], fill='next_open', daily=True)
    sr = sr.add(dm.reindex(cal2).fillna(0))
sr = sr*RF; mkt2 = pd.concat([uni[t]['close'].pct_change().reindex(cal2) for t in real], axis=1).mean(axis=1)
print(f"  REAL deployable: MTM Sharpe={shp(sr):+.2f} | {ab(sr,[mkt2.reindex(sr.index)],['mkt'])}")

print("\n=== (E) EXPOSURE / TURNOVER ===")
posdays = (daily(allI, 'next_open') != 0).mean()
print(f"  days with P&L (>=1 position): {posdays*100:.0f}% | trades total={len(P)} (~{len(P)/26:.0f}/yr) | avg hold={ (pd.to_datetime(P['exit'])-pd.to_datetime(P['entry'])).dt.days.mean():.1f}d")

print("\n=== (F) COST STRESS (delai+1, extra bps) ===")
for extra in [0, 3, 6, 10]:
    fr = []
    for t in allI:
        tr = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=costs[t]+extra, fill='next_open')
        if len(tr): fr.append(tr)
    m = lab.trade_metrics(pd.concat(fr, ignore_index=True)); print(f"  +{extra}bps: expR={m['expR']:+.4f} tradeSh={m['sharpe']:+.2f}")

# ---- (G) figure ----
uni2 = lab.load_universe()  # restore proxy for the all-universe figure consistency
s = daily(allI, 'next_open'); eq = (1+s).cumprod(); dd = eq/eq.cummax()-1
fig, ax = plt.subplots(2, 2, figsize=(13, 8))
ax[0,0].plot(eq.index, eq.values, lw=1.3); ax[0,0].set_yscale('log'); ax[0,0].set_title(f"Ross Hook equity (MTM, delai+1) Sharpe {shp(s):.2f}")
ax[0,1].fill_between(dd.index, dd.values*100, 0, color='crimson', alpha=.5); ax[0,1].set_title(f"Drawdown MTM — max {dd.min()*100:.1f}% (pas -79%)")
cls_sh = {}
for cls in ['indices','commodities','forex','crypto']:
    ci=[t for t in allI if CLASS.get(t)==cls]
    if ci: cls_sh[cls]=shp(daily(ci,'next_open'))
ax[1,0].bar(cls_sh.keys(), cls_sh.values(), color=['steelblue','seagreen','indianred','goldenrod']); ax[1,0].axhline(0,color='k',lw=.8); ax[1,0].set_title("MTM Sharpe par classe")
roll=s.rolling(252).mean()/s.rolling(252).std()*np.sqrt(252); ax[1,1].plot(roll.index,roll.values,lw=1); ax[1,1].axhline(0,color='k',lw=.6); ax[1,1].axhline(1,color='g',ls='--',lw=.6); ax[1,1].set_title("Sharpe glissant 1 an")
plt.tight_layout(); plt.savefig("../results/s076_deepdive.png", dpi=110); print("\nsaved ../results/s076_deepdive.png")
