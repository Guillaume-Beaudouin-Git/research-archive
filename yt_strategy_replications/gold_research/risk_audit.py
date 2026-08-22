"""
RISK AUDIT / STRESS TEST for ASIA_23_8 (gold 23:00->07:00 UTC, vol-targeted, long).

After confirming the code has no look-ahead (audit_code.py: causal VT; edge present
without VT), this quantifies how FRAGILE the headline Sharpe is:
  1. gap-handling sensitivity (complete-window-only vs production gap-fill);
  2. neighbourhood-robust Sharpe (is 23:00/8h a plateau or a cherry-picked spike?);
  3. is it gold beta? (regress on buy&hold);  4. per-year stability;
  5. stationary block bootstrap -> Sharpe distribution & P(SR>1);  6. outlier dependence.
Run: python risk_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402

ANN = 252.0
WIN = [23, 0, 1, 2, 3, 4, 5, 6]
SPREAD = 1.5

g = data.load_h1("XAUUSD")
g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
aday = (g.index - pd.Timedelta(hours=13)).normalize()
pv = g.assign(aday=aday, hour=g.index.hour).pivot_table(index="aday", columns="hour", values="lr")


def vt_net(wret, spread=SPREAD, lookback=20):
    rv = wret.rolling(lookback, min_periods=lookback).std().shift(1)
    scale = (rv.expanding(min_periods=lookback).median() / rv).clip(upper=3.0).fillna(0.0)
    return (scale * wret - scale.abs() * spread * 1e-4).dropna()


def sharpe(x):
    return float(S.sharpe_ratio(np.asarray(x), ANN))


def win_ret(hours, complete_only):
    sub = pv[hours]
    if complete_only:
        sub = sub[sub.notna().all(axis=1)]
        return sub.sum(axis=1)
    return sub.fillna(0.0).sum(axis=1)


# 1) gap sensitivity
net_prod = vt_net(win_ret(WIN, complete_only=False))
net_clean = vt_net(win_ret(WIN, complete_only=True))
print("=== 1. gap-handling sensitivity (net 1.5 bp) ===")
print(f"  production (gap-filled, all days)     : Sharpe {sharpe(net_prod):.3f}  n={len(net_prod)}")
print(f"  complete-window-only (no gap fill)    : Sharpe {sharpe(net_clean):.3f}  n={len(net_clean)}")

# 2) neighbourhood-robust Sharpe (swap-free windows only)
print("\n=== 2. neighbourhood (complete-window, net 1.5 bp) — swap-free starts 23/0 ===")
vals = []
for start in [23, 0]:
    row = []
    for length in [6, 7, 8, 9, 10]:
        w = [(start + i) % 24 for i in range(length)]
        if 21 in w or 22 in w:
            row.append(np.nan); continue
        s = sharpe(vt_net(win_ret(w, complete_only=True)))
        row.append(s); vals.append(s)
    print(f"  {start:02d}:00  " + " ".join(f"{v:5.2f}" for v in row))
print(f"  -> neighbourhood mean {np.nanmean(vals):.2f}, max {np.nanmax(vals):.2f}, "
      f"frac>1 {np.mean([v>1 for v in vals]):.0%}")

# 3) is it gold beta?  regress strategy net on buy&hold gold daily
clean = win_ret(WIN, complete_only=True)
nc = vt_net(clean)
gold_daily = g["close"].groupby(g.index.normalize()).last().pct_change()
gold_daily.index = pd.DatetimeIndex(gold_daily.index)
xy = pd.concat([nc.rename("strat"), gold_daily.reindex(nc.index).rename("gold")], axis=1).dropna()
X = sm.add_constant(xy["gold"].to_numpy())
ols = sm.OLS(xy["strat"].to_numpy(), X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
print("\n=== 3. beta decomposition (strategy ~ gold buy&hold) ===")
print(f"  alpha {ols.params[0]*1e4:+.2f} bp/day (t {ols.tvalues[0]:+.2f}) | "
      f"beta {ols.params[1]:+.3f} | R^2 {ols.rsquared:.3f}")
print(f"  annualised alpha {ols.params[0]*ANN*100:+.1f}%  ->  alpha Sharpe ~ "
      f"{ols.params[0]/xy['strat'].std()*np.sqrt(ANN):.2f} if beta-hedged")

# 4) per-year Sharpe
print("\n=== 4. per-year net Sharpe (complete-window, 1.5 bp) ===")
yr = nc.groupby(nc.index.year).apply(lambda s: sharpe(s) if len(s) > 40 else np.nan)
print("  " + " ".join(f"{y}:{v:+.1f}" for y, v in yr.items()))
print(f"  positive years: {int((yr>0).sum())}/{int(yr.notna().sum())} | worst {yr.min():+.2f}")

# 5) stationary block bootstrap of net daily returns
r = nc.to_numpy()
n = len(r)
rng = np.random.default_rng(1)
B, p = 2000, 1.0 / 10
boot = np.empty(B)
for b in range(B):
    idx = np.empty(n, dtype=int); i = rng.integers(0, n)
    for k in range(n):
        idx[k] = i
        i = rng.integers(0, n) if rng.random() < p else (i + 1) % n
    boot[b] = sharpe(r[idx])
print("\n=== 5. stationary block bootstrap (2000x) — Sharpe distribution ===")
print(f"  median {np.median(boot):.2f} | 5th pct {np.percentile(boot,5):.2f} | "
      f"P(SR>0) {np.mean(boot>0):.2f} | P(SR>0.5) {np.mean(boot>0.5):.2f} | P(SR>1) {np.mean(boot>1):.2f}")

# 6) outlier dependence
srt = np.sort(r)[::-1]
for k in [5, 10, 20]:
    cut = np.sort(np.argsort(r)[::-1][:k])
    keep = np.delete(r, cut)
    print(f"  drop top {k:2d} days -> Sharpe {sharpe(keep):.2f}")
