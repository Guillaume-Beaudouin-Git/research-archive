"""
Drawdown attribution for ASIA_23_8 — what drove the 2017-2021 underwater period?
Outputs episode table, monthly-return heatmap, annual diagnostics (structural drift
strength vs tail-loss days vs vol regime), worst days, rolling 12m Sharpe.
Run: python analyze_drawdown.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402

ANN = 252.0; WIN = [23, 0, 1, 2, 3, 4, 5, 6]; SPREAD = 1.5
RES = HERE / "results"

g = data.load_h1("XAUUSD")
g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
aday = (g.index - pd.Timedelta(hours=13)).normalize()
pv = g.assign(aday=aday, hour=g.index.hour).pivot_table(index="aday", columns="hour", values="lr")
sub = pv[WIN]
drift = sub[sub.notna().all(axis=1)].sum(axis=1)          # raw structural window return (no VT, no cost)
rv = drift.rolling(20, min_periods=20).std().shift(1)
scale = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)
net = (scale * drift - scale.abs() * SPREAD * 1e-4).dropna()
drift = drift.reindex(net.index); scale = scale.reindex(net.index)
eq = (1 + net).cumprod()
dd = eq / eq.cummax() - 1


def sharpe(x):
    x = np.asarray(x)
    return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


# 1) drawdown episodes
peak = eq.cummax()
episodes, in_dd = [], False
start = trough = None; tval = 0.0
for date, d in dd.items():
    if not in_dd and d < -1e-9:
        in_dd, start, trough, tval = True, date, date, d
    elif in_dd:
        if d < tval:
            trough, tval = date, d
        if d >= -1e-9:
            episodes.append((start, trough, date, tval)); in_dd = False
if in_dd:
    episodes.append((start, trough, dd.index[-1], tval))
ep = pd.DataFrame(episodes, columns=["peak", "trough", "recover", "depth"])
ep["dur_days"] = [(r - p).days for p, r in zip(ep["peak"], ep["recover"])]
print("=== worst drawdown episodes (by depth) ===")
for _, r in ep.sort_values("depth").head(4).iterrows():
    print(f"  {r['peak'].date()} -> trough {r['trough'].date()} ({r['depth']:.1%}) -> "
          f"recover {r['recover'].date()}  [{r['dur_days']} cal days ~{r['dur_days']/365:.1f}y]")

# 2) annual diagnostics: structural drift vs tail vs vol
print("\n=== annual diagnostics ===")
print(" year  drift_bps  net_bps  ann_vol  sharpe  avgVTscale  bigLossDays(<-1%)  worstDay%")
for y in range(2015, 2027):
    nd = net[net.index.year == y]; df_ = drift[drift.index.year == y]; sc = scale[scale.index.year == y]
    if len(nd) < 40:
        continue
    print(f" {y}   {df_.mean()*1e4:7.2f}  {nd.mean()*1e4:7.2f}  {nd.std()*np.sqrt(ANN):6.1%}  "
          f"{sharpe(nd):6.2f}  {sc.mean():8.2f}  {int((nd<-0.01).sum()):14d}  {nd.min()*100:8.2f}")

# 3) monthly returns pivot
mret = net.resample("ME").apply(lambda s: (1 + s).prod() - 1)
mp = pd.DataFrame({"y": mret.index.year, "m": mret.index.month, "r": mret.values}).pivot(index="y", columns="m", values="r")
print("\n=== worst 12 single days (date, net%, that day's raw drift%) ===")
for dt, v in net.nsmallest(12).items():
    print(f"  {dt.date()}  net {v*100:+.2f}%   raw_drift {drift.loc[dt]*100:+.2f}%   vt_scale {scale.loc[dt]:.2f}")

# figures
fig, ax = plt.subplots(figsize=(12, 6))
im = ax.imshow(mp.values * 100, cmap="RdYlGn", vmin=-6, vmax=6, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels(["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
ax.set_yticks(range(len(mp.index))); ax.set_yticklabels(mp.index, fontsize=8)
for i in range(mp.shape[0]):
    for j in range(mp.shape[1]):
        v = mp.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v*100:.0f}", ha="center", va="center", fontsize=6)
ax.set_title("ASIA_23_8 — monthly net return % (red = loss)")
fig.colorbar(im, ax=ax, label="%")
fig.tight_layout(); fig.savefig(RES / "fig_monthly_heatmap.png", dpi=120); plt.close(fig)

roll = net.rolling(252).mean() / net.rolling(252).std() * np.sqrt(ANN)
fig, (a1, a2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, height_ratios=[1, 1])
a1.fill_between(dd.index, dd.values * 100, 0, color="crimson", alpha=0.4)
a1.set_ylabel("drawdown %"); a1.set_title("ASIA_23_8 — underwater curve & rolling 12m Sharpe"); a1.grid(alpha=0.25)
a2.plot(roll.index, roll.values, color="navy", lw=1.0); a2.axhline(0, color="black", lw=0.8); a2.axhline(1, color="green", ls="--", lw=0.8)
a2.set_ylabel("rolling 12m Sharpe"); a2.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_underwater_rolling.png", dpi=120); plt.close(fig)
print("\nsaved fig_monthly_heatmap.png + fig_underwater_rolling.png")
