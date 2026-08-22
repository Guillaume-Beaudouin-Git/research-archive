"""
Rigorous validation of the lead candidate ON_22_8 (vol-targeted long gold over the
22:00->06:00 UTC overnight window). Anti-overfit battery:
  1. TRUE OOS: select the window on the first 60% of history, test the SELECTED
     window on the untouched last 40%.
  2. Walk-forward: window re-selected each fold, evaluated on the next fold.
  3. Cost sensitivity, leverage realism, buy&hold benchmark, honest DSR.
Run: python validate.py
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
N_TRIALS = 60
piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)
ones = pd.Series(1.0, index=piv13.index)
STARTS, LENGTHS = [21, 22, 23, 0], [4, 6, 8, 10, 12, 16]


def win(start, length):
    return [(start + i) % 24 for i in range(length)]


def net_series(piv, start, length, cost=2.0):
    net, _ = iz.backtest(piv, ones.reindex(piv.index).fillna(0.0), win(start, length),
                         cost_bps=cost, voltarget=True)
    return net


def sh(net):
    return float(S.sharpe_ratio(net.to_numpy(), iz.ANN))


# 1) TRUE OOS train/test (select window on first 60%, test on last 40%)
split = piv13.index[int(0.60 * len(piv13))]
tr, te = piv13[piv13.index < split], piv13[piv13.index >= split]
grid = [(s, l, sh(net_series(tr, s, l))) for s in STARTS for l in LENGTHS]
best_s, best_l, best_tr = max(grid, key=lambda x: x[2])
test_net = net_series(te, best_s, best_l)
fixed_test = net_series(te, 22, 8)   # the pre-named candidate on the holdout
print(f"=== TRUE OOS ===  train best window = ({best_s}:00, {best_l}h)  train Sharpe {best_tr:.2f}")
print(f"  selected-window OOS (last 40%): Sharpe {sh(test_net):.2f}")
print(f"  ON_22_8 OOS (last 40%):         Sharpe {sh(fixed_test):.2f}  "
      f"({te.index.min().date()}..{te.index.max().date()})")

# 2) Walk-forward: re-select window on expanding train, test next fold
n = len(piv13)
bounds = np.linspace(0, n, 6).astype(int)
wf = []
for k in range(1, 5):
    trk = piv13.iloc[:bounds[k]]
    tek = piv13.iloc[bounds[k]:bounds[k + 1]]
    g = [(s, l, sh(net_series(trk, s, l))) for s in STARTS for l in LENGTHS]
    bs, bl, _ = max(g, key=lambda x: x[2])
    wf.append({"fold": k, "win": f"{bs}:{bl}", "test_sharpe": round(sh(net_series(tek, bs, bl)), 2)})
print("\n=== walk-forward (window re-selected each fold) ===")
for w in wf:
    print(f"  fold{w['fold']} selected={w['win']:5s} test Sharpe {w['test_sharpe']:+.2f}")

# 3) Full-sample stats + cost grid + leverage + benchmark
full = net_series(piv13, 22, 8)
eq = (1 + full).cumprod()
mdd, _ = S.max_drawdown(eq.to_numpy())
_, t = S.hac_tstat(full.to_numpy())
dsr = S.deflated_sharpe_ratio(full.to_numpy(), n_trials=N_TRIALS, periods_per_year=iz.ANN)
boot = S.stationary_bootstrap_pvalue(full.to_numpy())
folds = S.fold_metrics(full.to_numpy(), 5, iz.ANN)
cost_grid = {c: round(sh(net_series(piv13, 22, 8, cost=c)), 2) for c in [0, 1, 1.5, 2, 3, 5]}

# leverage realism (recompute the VT scale)
r = iz.win_ret(piv13, win(22, 8))
rv = r.rolling(20, min_periods=20).std().shift(1)
scale = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0)
lev = {"avg": round(float(scale.mean()), 2), "median": round(float(scale.median()), 2),
       "pct_at_cap": round(float((scale >= 2.999).mean()), 3)}

# buy & hold gold daily
g = data.load_h1("XAUUSD")
dret = g["close"].groupby(g.index.normalize()).last().pct_change().dropna()
bh_sharpe = round(float(S.sharpe_ratio(dret.to_numpy(), 252)), 2)
bh_mdd, _ = S.max_drawdown((1 + dret).cumprod().to_numpy())

summary = dict(
    candidate="ON_22_8 (VT long gold 22:00-06:00 UTC overnight)",
    full_sample=dict(sharpe_net_2bp=round(sh(full), 2), hac_t=round(float(t), 2),
                     dsr=round(float(dsr.get("dsr", float("nan"))), 3), bootstrap_p=round(boot, 4),
                     ann_ret=round(float(full.mean() * iz.ANN), 3), ann_vol=round(float(full.std() * np.sqrt(iz.ANN)), 3),
                     maxdd=round(float(mdd), 3), wf_folds=[round(x, 2) for x in folds["fold_sharpes"]],
                     mean_bps=round(float(full.mean() * 1e4), 2)),
    oos_train_test=dict(train_best_window=f"{best_s}:{best_l}", selected_oos_sharpe=round(sh(test_net), 2),
                        ON_22_8_oos_sharpe=round(sh(fixed_test), 2)),
    walk_forward=wf, cost_grid_sharpe=cost_grid, leverage=lev,
    benchmark_buyhold_gold=dict(sharpe=bh_sharpe, maxdd=round(float(bh_mdd), 3)),
    n_trials_dsr=N_TRIALS)
json.dump(summary, open(RES / "validation_summary.json", "w"), indent=2)
print("\n=== full-sample (net 2 bps) ===")
print(json.dumps(summary["full_sample"], indent=2))
print("cost grid (Sharpe):", cost_grid)
print("leverage:", lev, "| buy&hold gold Sharpe:", bh_sharpe, "maxDD", round(float(bh_mdd), 2))

# figure
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[3, 1], sharex=True)
a1.plot(eq.index, eq.values, color="seagreen", lw=1.3, label="ON_22_8 (net 2bp)")
bh = (1 + dret).cumprod().reindex(eq.index).ffill()
a1.plot(bh.index, (bh / bh.iloc[0]).values, color="gray", ls="--", lw=1.0, label="buy & hold gold")
a1.axvline(split, color="crimson", ls=":", lw=1.0, label="OOS split (60/40)")
a1.set_yscale("log"); a1.set_ylabel("equity (×, log)"); a1.legend(); a1.grid(alpha=0.25)
a1.set_title("Gold overnight strategy ON_22_8 — net 2 bps/RT, 2007–2026")
_, dd = S.max_drawdown(eq.to_numpy())
a2.fill_between(eq.index, dd * 100, 0, color="crimson", alpha=0.4); a2.set_ylabel("DD %"); a2.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_ON_22_8_validation.png", dpi=120); plt.close(fig)
print("\nsaved validation_summary + fig")
