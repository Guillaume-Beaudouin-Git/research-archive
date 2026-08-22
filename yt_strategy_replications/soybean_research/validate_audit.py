"""
SOYBEAN.c — validate that the gross electronic-reopen edge is REAL (so the verdict
is 'real edge, wrong instrument', not 'noise'), then nail the cost verdict.
Edge: long soybean over the post-halt electronic reopen 01:00-07:00 UTC (hours 1-6),
vol-targeted, complete-window. Run: python validate_audit.py
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
drift = sub[sub.notna().all(axis=1)].sum(axis=1)          # raw window return (gross, complete-window)
rv = drift.rolling(20, min_periods=20).std().shift(1)
scale = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def net(spread):
    return (scale * drift - scale.abs() * spread * 1e-4).dropna()


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


gross = net(0.0)
print("=== is the gross edge real? ===")
print(f"  n={len(gross)} | gross Sharpe {sharpe(gross):.2f} | HAC t {S.hac_tstat(gross.to_numpy())[1]:.2f} | "
      f"DSR {S.deflated_sharpe_ratio(gross.to_numpy(),20,periods_per_year=ANN)['dsr']:.2f}")
split = gross.index[int(0.6 * len(gross))]
print(f"  OOS(40%) gross Sharpe {sharpe(gross[gross.index >= split].to_numpy()):.2f}")
no_vt = (drift - 0).dropna()
print(f"  no-VT constant-long gross Sharpe {sharpe(no_vt.to_numpy()):.2f} (edge not a VT artefact)")
print(f"  SHORT-the-window gross Sharpe {sharpe((-gross).to_numpy()):.2f} (should be clearly negative)")
yr = gross.groupby(gross.index.year).apply(lambda s: sharpe(s) if len(s) > 40 else np.nan).dropna()
print(f"  per-year gross Sharpe positive: {int((yr>0).sum())}/{len(yr)}  ->  " +
      " ".join(f"{y}:{v:+.1f}" for y, v in yr.items()))

# beta vs soybean buy&hold
sd = g["close"].groupby(g.index.normalize()).last().pct_change()
xy = pd.concat([gross.rename("s"), sd.reindex(gross.index).rename("m")], axis=1).dropna()
ols = sm.OLS(xy["s"].to_numpy(), sm.add_constant(xy["m"].to_numpy())).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
print(f"  beta vs soybean {ols.params[1]:+.3f}, R^2 {ols.rsquared:.3f}, alpha t {ols.tvalues[0]:+.2f}")

print("\n=== THE COST VERDICT: net Sharpe by round-trip spread ===")
for sp in [0, 1.5, 3, 5, 8, 13, 26]:
    nn = net(sp)
    print(f"  {sp:5.1f} bp RT -> Sharpe {sharpe(nn.to_numpy()):+.2f} | mean {nn.mean()*1e4:+.2f} bp/day"
          + ("   <- futures (ZS) tier" if sp == 1.5 else "   <- FTMO CFD reality" if sp == 26 else ""))
print("  break-even spread ~ gross edge = "
      f"{gross.mean()*1e4 + (net(26).mean()*1e4*0):.1f} bp/trade gross  (need RT spread below this)")

# figure
fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
for sp, c, lab in [(0, "seagreen", "gross"), (5, "steelblue", "net 5bp (futures-ish)"), (26, "crimson", "net 26bp (FTMO CFD)")]:
    eq = (1 + net(sp)).cumprod()
    ax[0].plot(eq.index, eq.values, color=c, lw=1.2, label=lab)
ax[0].set_yscale("log"); ax[0].axhline(1, color="black", lw=0.6)
ax[0].set_title("Soybean electronic-reopen edge: gross vs net"); ax[0].legend(); ax[0].grid(alpha=0.25); ax[0].set_ylabel("equity x (log)")
sps = [0, 1.5, 3, 5, 8, 13, 26]; shs = [sharpe(net(s).to_numpy()) for s in sps]
ax[1].plot(sps, shs, "o-", color="navy"); ax[1].axhline(1, color="green", ls="--", label="Sharpe=1"); ax[1].axhline(0, color="black", lw=0.8)
ax[1].axvline(26, color="crimson", ls=":", label="FTMO CFD ~26bp"); ax[1].axvline(1.5, color="seagreen", ls=":", label="futures ~1.5bp")
ax[1].set_xlabel("round-trip spread (bp)"); ax[1].set_ylabel("net Sharpe"); ax[1].set_title("Cost sensitivity — dead above ~8 bp RT"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_soybean_cost.png", dpi=120); plt.close(fig)
print("\nsaved fig_soybean_cost.png")
