"""
Refinement (modification 1): trend-conditioned overnight session timing.

ON_long is long-biased -> it loses in gold bear regimes. Make the overnight
position two-sided by the prevailing daily trend (sign of close vs SMA, known at
21:00 before entry): long the overnight drift in up-trends, short it in down-
trends. This removes the directional-beta dependence and should lift the Sharpe.
Run: python refine.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402
import intraday as iz  # noqa: E402

RES = HERE / "results"
N_TRIALS = 50
OVERNIGHT = [21, 22, 23] + list(range(0, 13))

piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)

# daily close sampled at 20:00 UTC (before the 21:00 overnight entry) -> trend signal
g = data.load_h1("XAUUSD")
c20 = g["close"][g.index.hour == 20].copy()
c20.index = c20.index.normalize()
c20 = c20[~c20.index.duplicated(keep="last")]


def trend_sig(n):
    t = np.sign(c20 - c20.rolling(n, min_periods=n).mean())
    return t.reindex(piv13.index).fillna(0.0)


def report(net, label, cost):
    eq = (1 + net).cumprod()
    _, t = S.hac_tstat(net.to_numpy())
    dsr = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=N_TRIALS, periods_per_year=iz.ANN)
    folds = S.fold_metrics(net.to_numpy(), 5, iz.ANN)
    mdd, _ = S.max_drawdown(eq.to_numpy())
    return dict(label=label, cost_bps=cost, sharpe_net=round(float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), 3),
                hac_t=round(float(t), 2), dsr=round(float(dsr.get("dsr", float("nan"))), 3),
                mean_bps=round(float(net.mean() * 1e4), 2), ann_ret=round(float(net.mean() * iz.ANN), 3),
                ann_vol=round(float(net.std() * np.sqrt(iz.ANN)), 3), maxdd=round(float(mdd), 3),
                wf=round(float(folds["wf_score"]), 2), folds=[round(x, 2) for x in folds["fold_sharpes"]])


rows = []
nets = {}
for n in [50, 100, 150, 200]:
    for vt in [False, True]:
        net, _ = iz.backtest(piv13, trend_sig(n), OVERNIGHT, cost_bps=2.0, voltarget=vt,
                             label=f"ONtrend{n}{'_VT' if vt else ''}")
        name = f"ONtrend_{n}{'_VT' if vt else ''}"
        nets[name] = net
        rows.append(report(net, name, 2.0))

lb = pd.DataFrame(rows).sort_values("sharpe_net", ascending=False)
print("=== trend-conditioned overnight (net 2 bps/RT) ===")
print(lb[["label", "sharpe_net", "hac_t", "dsr", "mean_bps", "ann_ret", "ann_vol", "maxdd", "wf"]].to_string(index=False))
print("\nper-fold (5 sub-periods) for top 3:")
for _, r in lb.head(3).iterrows():
    print(f"  {r['label']:16s} {r['folds']}")

best = lb.iloc[0]["label"]
print(f"\n=== cost sensitivity — {best} ===")
n_best = int(best.split("_")[1])
vt_best = best.endswith("VT")
grid = {}
for c in [0, 1, 2, 3, 5]:
    net, _ = iz.backtest(piv13, trend_sig(n_best), OVERNIGHT, cost_bps=c, voltarget=vt_best)
    grid[c] = round(float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), 2)
print("  " + " ".join(f"{c}bp={grid[c]:+.2f}" for c in [0, 1, 2, 3, 5]))

json.dump({"leaderboard": rows, "best": best, "cost_grid": grid},
          open(RES / "refine_summary.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(11, 5))
for name, c in [(best, "seagreen"), ("ONtrend_200", "navy")]:
    if name in nets:
        s = nets[name]
        ax.plot(s.index, (1 + s).cumprod().values, label=name, lw=1.3, color=c)
ax.set_yscale("log"); ax.axhline(1, color="black", lw=0.6)
ax.set_title("Gold overnight trend-timing — equity (net 2 bps/RT, 2007–2026)")
ax.set_ylabel("equity (×, log)"); ax.legend(); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_overnight_trend.png", dpi=120); plt.close(fig)
print("\nsaved refine_summary + fig")
