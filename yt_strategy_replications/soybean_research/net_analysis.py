"""
Net tear-sheet for the SOYBEAN reopen strategy under the assumed spread (<= 3 bp RT).
Base case = 2 bp; conservative = 3 bp; optimistic = 1 bp. Generates net figures.
Run: python net_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
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
sub = pv[WIN]
drift = sub[sub.notna().all(axis=1)].sum(axis=1)
rv = drift.rolling(20, min_periods=20).std().shift(1)
sc = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def net(spread):
    return (sc * drift - sc.abs() * spread * 1e-4).dropna()


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def mdd(r):
    eq = np.cumprod(1 + np.asarray(r)); return float((eq / np.maximum.accumulate(eq) - 1).min())


print("=== NET tear-sheet by spread (RT, = one quoted spread) ===")
print(" sp  Sharpe Sortino  annret annvol  maxDD Calmar  OOS   DSR  hit  skew")
for sp in [1.0, 2.0, 3.0]:
    n = net(sp); r = n.to_numpy()
    oos = sharpe(n[n.index >= n.index[int(0.6 * len(n))]].to_numpy())
    dsr = S.deflated_sharpe_ratio(r, 20, periods_per_year=ANN)["dsr"]
    print(f" {sp:.0f}bp {sharpe(r):5.2f}  {S.sortino_ratio(r,ANN):5.2f}  {r.mean()*ANN:+5.1%} {r.std()*np.sqrt(ANN):5.1%} "
          f"{mdd(r):6.1%} {r.mean()*ANN/abs(mdd(r)):5.2f} {oos:5.2f} {dsr:5.2f} {(r>0).mean():.0%} {sst.skew(r):+.2f}")

BASE = 2.0
b = net(BASE); rb = b.to_numpy()
print(f"\n=== base case = {BASE:.0f} bp ===  HAC t {S.hac_tstat(rb)[1]:.2f} | worst day {rb.min():+.2%} | worst month {b.resample('ME').apply(lambda s:(1+s).prod()-1).min():+.2%}")
yr = b.groupby(b.index.year).apply(lambda s: sharpe(s) if len(s) > 40 else np.nan).dropna()
print("per-year net Sharpe @2bp: " + " ".join(f"{y}:{v:+.1f}" for y, v in yr.items()) + f"  ({int((yr>0).sum())}/{len(yr)} +)")

# drawdown episodes @2bp
eq = (1 + b).cumprod(); dd = eq / eq.cummax() - 1
peak = eq.cummax(); ep = []; inx = False; st = tr = None; tv = 0
for dt, d in dd.items():
    if not inx and d < -1e-9:
        inx, st, tr, tv = True, dt, dt, d
    elif inx:
        if d < tv:
            tr, tv = dt, d
        if d >= -1e-9:
            ep.append((st, tr, dt, tv)); inx = False
if inx:
    ep.append((st, tr, dd.index[-1], tv))
ep = sorted(ep, key=lambda x: x[3])[:3]
print("worst DD episodes @2bp:")
for s, t, r_, v in ep:
    print(f"  {s.date()} -> {t.date()} ({v:.1%}) -> {r_.date()}  [{(r_-s).days} d ~{(r_-s).days/365:.1f}y]")

# MC @2bp
r = rb; n = len(r); rng = np.random.default_rng(4); B = 2000; p = 0.1
sh = np.empty(B); md = np.empty(B)
for j in range(B):
    idx = np.empty(n, int); i = rng.integers(0, n)
    for k in range(n):
        idx[k] = i; i = rng.integers(0, n) if rng.random() < p else (i + 1) % n
    sh[j] = sharpe(r[idx]); md[j] = mdd(r[idx])
print(f"MC @2bp: Sharpe median {np.median(sh):.2f} [5th {np.percentile(sh,5):.2f}] | P(SR>1) {np.mean(sh>1):.0%} | P(SR>0.5) {np.mean(sh>0.5):.0%} | maxDD med {np.median(md):.0%}")

# figures @2bp
mo = b.resample("ME").apply(lambda s: (1 + s).prod() - 1)
fig, ax = plt.subplots(2, 2, figsize=(13, 8))
ax[0,0].plot(eq.index, eq.values, color="seagreen", lw=1.2); ax[0,0].set_yscale("log")
ax[0,0].set_title(f"Soybean reopen — NET equity ({BASE:.0f} bp spread)"); ax[0,0].grid(alpha=0.25); ax[0,0].set_ylabel("equity x (log)")
ax[0,1].fill_between(dd.index, dd.values*100, 0, color="crimson", alpha=0.4); ax[0,1].set_title(f"Drawdown (max {dd.min():.0%})"); ax[0,1].grid(alpha=0.25); ax[0,1].set_ylabel("DD %")
ax[1,0].bar(yr.index, yr.values, color=["seagreen" if v>0 else "indianred" for v in yr.values]); ax[1,0].axhline(0,color="black",lw=0.8)
ax[1,0].set_title(f"Per-year net Sharpe @{BASE:.0f}bp ({int((yr>0).sum())}/{len(yr)} +)"); ax[1,0].grid(alpha=0.25,axis="y")
ax[1,1].hist(sh,bins=40,color="steelblue",alpha=0.8); ax[1,1].axvline(1,color="crimson",ls="--",label="SR=1"); ax[1,1].axvline(np.median(sh),color="black",label=f"median {np.median(sh):.2f}")
ax[1,1].set_title(f"MC Sharpe @{BASE:.0f}bp — P(SR>1)={np.mean(sh>1):.0%}"); ax[1,1].legend(); ax[1,1].grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES/"fig_soybean_net_stress.png", dpi=120); plt.close(fig)

mp = pd.DataFrame({"y":mo.index.year,"m":mo.index.month,"r":mo.values}).pivot(index="y",columns="m",values="r")
fig,axh=plt.subplots(figsize=(11,4)); im=axh.imshow(mp.values*100,cmap="RdYlGn",vmin=-6,vmax=6,aspect="auto")
axh.set_xticks(range(12)); axh.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"]); axh.set_yticks(range(len(mp.index))); axh.set_yticklabels(mp.index,fontsize=8)
for i in range(mp.shape[0]):
    for jj in range(mp.shape[1]):
        v=mp.values[i,jj]
        if not np.isnan(v): axh.text(jj,i,f"{v*100:.0f}",ha="center",va="center",fontsize=6)
axh.set_title(f"Soybean reopen — monthly NET return % (@{BASE:.0f}bp)"); fig.colorbar(im,ax=axh,label="%")
fig.tight_layout(); fig.savefig(RES/"fig_soybean_net_monthly.png",dpi=120); plt.close(fig)
print("saved fig_soybean_net_stress.png + fig_soybean_net_monthly.png")
