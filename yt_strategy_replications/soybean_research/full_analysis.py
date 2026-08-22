"""
Full institutional analysis battery for the SOYBEAN reopen edge (01:00-07:00 UTC,
vol-targeted, complete-window) — mirrors the gold ASIA_23_8 work. The EDGE is
characterised GROSS (spread-independent in shape); net viability is reported as a
spread-scenario table (the spread is the decision variable and is broker-specific).
Run: python full_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as sst

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402

ANN = 252.0
WIN = [1, 2, 3, 4, 5, 6]
RES = HERE / "results"

g = data.load_h1("SOYBEAN")
g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
pv = g.assign(d=g.index.normalize(), hour=g.index.hour).pivot_table(index="d", columns="hour", values="lr")


def wret(hours):
    sub = pv[hours]
    return sub[sub.notna().all(axis=1)].sum(axis=1)


def vt(w):
    rv = w.rolling(20, min_periods=20).std().shift(1)
    return (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


drift = wret(WIN)
sc = vt(drift)


def net(spread):
    return (sc * drift - sc.abs() * spread * 1e-4).dropna()


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def maxdd(r):
    eq = np.cumprod(1 + np.asarray(r)); return float((eq / np.maximum.accumulate(eq) - 1).min())


gross = net(0.0)
r = gross.to_numpy()
mo = gross.resample("ME").apply(lambda s: (1 + s).prod() - 1)
split = gross.index[int(0.6 * len(gross))]
print("=== TEAR SHEET (gross edge) ===")
print(f"  n={len(r)} days  {gross.index.min().date()}->{gross.index.max().date()}")
print(f"  Sharpe {sharpe(r):.2f} | Sortino {S.sortino_ratio(r,ANN):.2f} | OOS Sharpe {sharpe(gross[gross.index>=split].to_numpy()):.2f}")
print(f"  annret {r.mean()*ANN:+.1%} | annvol {r.std()*np.sqrt(ANN):.1%} | maxDD {maxdd(r):.1%} | Calmar {r.mean()*ANN/abs(maxdd(r)):.2f}")
print(f"  daily hit {(r>0).mean():.1%} | monthly hit {(mo>0).mean():.1%} | skew {sst.skew(r):+.2f} | kurt {sst.kurtosis(r,fisher=False):.1f}")
print(f"  best/worst day {r.max():+.2%}/{r.min():+.2%} | best/worst month {mo.max():+.2%}/{mo.min():+.2%}")
print(f"  HAC t {S.hac_tstat(r)[1]:.2f} | DSR(20) {S.deflated_sharpe_ratio(r,20,periods_per_year=ANN)['dsr']:.2f}")

print("\n=== NET performance by round-trip spread (the decision variable) ===")
print("  spread_bp  Sharpe   annret   maxDD")
for sp in [0, 2, 3, 5, 9]:
    n = net(sp).to_numpy()
    print(f"   {sp:5.1f}    {sharpe(n):+.2f}   {n.mean()*ANN:+.1%}   {maxdd(n):.1%}")

print("\n=== code audit ===")
print(f"  no-VT constant-long gross Sharpe {sharpe(drift.dropna().to_numpy()):.2f} (edge not a VT artefact)")
print(f"  SHORT null gross Sharpe {sharpe((-gross).to_numpy()):+.2f} (should be clearly negative)")
sd = g['close'].groupby(g.index.normalize()).last().pct_change()
xy = pd.concat([gross.rename('s'), sd.reindex(gross.index).rename('m')], axis=1).dropna()
ols = sm.OLS(xy['s'].to_numpy(), sm.add_constant(xy['m'].to_numpy())).fit(cov_type='HAC', cov_kwds={'maxlags': 5})
print(f"  beta vs soybean {ols.params[1]:+.3f} | R^2 {ols.rsquared:.3f} | alpha t {ols.tvalues[0]:+.2f}")

print("\n=== per-year (gross Sharpe / raw drift bp) ===")
yr = gross.groupby(gross.index.year).apply(lambda s: sharpe(s) if len(s) > 40 else np.nan).dropna()
dr = drift.groupby(drift.index.year).mean() * 1e4
print("  " + " ".join(f"{y}:{v:+.1f}/{dr.get(y,0):+.0f}" for y, v in yr.items()))
print(f"  positive years {int((yr>0).sum())}/{len(yr)}")

print("\n=== parameter neighbourhood (gross Sharpe) ===")
for start in [1, 2]:
    row = []
    for length in [3, 4, 5, 6, 7, 8]:
        w = wret([(start + i) % 24 for i in range(length)])
        row.append(sharpe((vt(w) * w).dropna().to_numpy()))
    print(f"  start {start:02d}:00  " + " ".join(f"{v:5.2f}" for v in row))

print("\n=== execution-time robustness (gross Sharpe) ===")
for lbl, h in [("base 01-07", WIN), ("enter 1h late 02-07", [2,3,4,5,6]), ("exit 1h early 01-06", [1,2,3,4,5]), ("exit 1h late 01-08", WIN+[7])]:
    w = wret(h); s = vt(w)
    print(f"  {lbl:22s} Sharpe {sharpe((s*w).dropna().to_numpy()):+.2f}")

print("\n=== drawdown episodes (gross) + outliers ===")
eq = (1 + gross).cumprod(); dd = eq / eq.cummax() - 1
print(f"  max DD {dd.min():.1%}")
for k in [5, 10, 20]:
    cut = np.argsort(r)[::-1][:k]; print(f"  drop top {k:2d} days -> Sharpe {sharpe(np.delete(r, cut)):.2f}")

print("\n=== Monte-Carlo (stationary bootstrap, 2000x, gross) ===")
n = len(r); rng = np.random.default_rng(3); B = 2000; p = 0.1
sh = np.empty(B); md = np.empty(B)
for b in range(B):
    idx = np.empty(n, int); i = rng.integers(0, n)
    for k in range(n):
        idx[k] = i; i = rng.integers(0, n) if rng.random() < p else (i + 1) % n
    sh[b] = sharpe(r[idx]); md[b] = maxdd(r[idx])
print(f"  Sharpe median {np.median(sh):.2f} [5th {np.percentile(sh,5):.2f}] | P(SR>1) {np.mean(sh>1):.0%} | P(SR>0.5) {np.mean(sh>0.5):.0%}")
print(f"  maxDD median {np.median(md):.1%} [5th worst {np.percentile(md,5):.1%}]")

# figures
fig, ax = plt.subplots(2, 2, figsize=(13, 8))
ax[0,0].plot(eq.index, eq.values, color="seagreen", lw=1.2); ax[0,0].set_yscale("log")
ax[0,0].set_title("Soybean reopen edge — gross equity"); ax[0,0].grid(alpha=0.25); ax[0,0].set_ylabel("equity x (log)")
ax[0,1].fill_between(dd.index, dd.values*100, 0, color="crimson", alpha=0.4); ax[0,1].set_title(f"Drawdown (max {dd.min():.0%})"); ax[0,1].grid(alpha=0.25); ax[0,1].set_ylabel("DD %")
ax[1,0].bar(yr.index, yr.values, color=["seagreen" if v>0 else "indianred" for v in yr.values]); ax[1,0].axhline(0,color="black",lw=0.8)
ax[1,0].set_title(f"Per-year gross Sharpe ({int((yr>0).sum())}/{len(yr)} positive)"); ax[1,0].grid(alpha=0.25,axis="y")
ax[1,1].hist(sh,bins=40,color="steelblue",alpha=0.8); ax[1,1].axvline(1,color="crimson",ls="--",label="SR=1"); ax[1,1].axvline(np.median(sh),color="black",label=f"median {np.median(sh):.2f}")
ax[1,1].set_title(f"MC bootstrap Sharpe (gross) — P(SR>1)={np.mean(sh>1):.0%}"); ax[1,1].legend(); ax[1,1].grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES/"fig_soybean_stress.png", dpi=120); plt.close(fig)

mp = pd.DataFrame({"y":mo.index.year,"m":mo.index.month,"r":mo.values}).pivot(index="y",columns="m",values="r")
fig,axh=plt.subplots(figsize=(11,4)); im=axh.imshow(mp.values*100,cmap="RdYlGn",vmin=-6,vmax=6,aspect="auto")
axh.set_xticks(range(12)); axh.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"]); axh.set_yticks(range(len(mp.index))); axh.set_yticklabels(mp.index,fontsize=8)
for i in range(mp.shape[0]):
    for j in range(mp.shape[1]):
        v=mp.values[i,j]
        if not np.isnan(v): axh.text(j,i,f"{v*100:.0f}",ha="center",va="center",fontsize=6)
axh.set_title("Soybean reopen edge — monthly gross return %"); fig.colorbar(im,ax=axh,label="%")
fig.tight_layout(); fig.savefig(RES/"fig_soybean_monthly.png",dpi=120); plt.close(fig)
print("\nsaved fig_soybean_stress.png + fig_soybean_monthly.png")
