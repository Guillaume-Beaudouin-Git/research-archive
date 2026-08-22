"""
Monte-Carlo / scenario stress for ASIA_23_8 (complete-window, vol-targeted).
  * MC stationary bootstrap -> distribution of annual return, max drawdown, Calmar;
  * worst observed & bootstrap drawdown and its duration;
  * conservative deployment scenarios: spread 2 bp, and a weekly swap "leak"
    (rollover hits the position one day/week -> -3.3 bp that day);
  * entry/exit time perturbation (+/-1h) execution robustness.
Run: python stress_mc.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402

ANN = 252.0
WIN = [23, 0, 1, 2, 3, 4, 5, 6]

g = data.load_h1("XAUUSD")
g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
aday = (g.index - pd.Timedelta(hours=13)).normalize()
pv = g.assign(aday=aday, hour=g.index.hour).pivot_table(index="aday", columns="hour", values="lr")


def wret_complete(hours):
    sub = pv[hours]
    return sub[sub.notna().all(axis=1)].sum(axis=1)


def vt_scale(wret, lookback=20):
    rv = wret.rolling(lookback, min_periods=lookback).std().shift(1)
    return (rv.expanding(min_periods=lookback).median() / rv).clip(upper=3.0).fillna(0.0)


def net_series(hours=WIN, spread=1.5, swap_weekly_leak=False):
    wret = wret_complete(hours)
    sc = vt_scale(wret)
    cost = sc.abs() * spread * 1e-4
    if swap_weekly_leak:                       # rollover leaks one day/week -> -3.3 bp
        leak = (pd.Series(wret.index, index=wret.index).dt.dayofweek == 2).astype(float)
        cost = cost + sc.abs() * leak * 3.3 * 1e-4
    return (sc * wret - cost).dropna()


def sharpe(x):
    return float(S.sharpe_ratio(np.asarray(x), ANN))


def max_dd(r):
    eq = np.cumprod(1 + np.asarray(r))
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def dd_duration(r):
    eq = np.cumprod(1 + np.asarray(r))
    peak = np.maximum.accumulate(eq)
    underwater = eq < peak * (1 - 1e-9)
    best = cur = 0
    for u in underwater:
        cur = cur + 1 if u else 0
        best = max(best, cur)
    return best


base = net_series(spread=1.5)
r = base.to_numpy()
n = len(r)
print(f"=== base (complete-window, 1.5 bp): Sharpe {sharpe(r):.2f} | ann.ret {r.mean()*ANN:+.1%} | "
      f"maxDD {max_dd(r):.1%} | Calmar {r.mean()*ANN/abs(max_dd(r)):.2f} | "
      f"longest DD {dd_duration(r)} trading days (~{dd_duration(r)/ANN:.1f}y) ===")

# MC stationary bootstrap
rng = np.random.default_rng(2)
B, p = 2000, 1.0 / 10
sh = np.empty(B); mdd = np.empty(B); ar = np.empty(B)
for b in range(B):
    idx = np.empty(n, dtype=int); i = rng.integers(0, n)
    for k in range(n):
        idx[k] = i
        i = rng.integers(0, n) if rng.random() < p else (i + 1) % n
    rb = r[idx]
    sh[b] = sharpe(rb); mdd[b] = max_dd(rb); ar[b] = rb.mean() * ANN
print("\n=== Monte-Carlo (2000 stationary-bootstrap paths) ===")
print(f"  Sharpe : median {np.median(sh):.2f}  [5th {np.percentile(sh,5):.2f}, 95th {np.percentile(sh,95):.2f}]")
print(f"  maxDD  : median {np.median(mdd):.1%}  [5th {np.percentile(mdd,5):.1%} worst, 95th {np.percentile(mdd,95):.1%}]")
print(f"  ann.ret: median {np.median(ar):+.1%}  [5th {np.percentile(ar,5):+.1%}, 95th {np.percentile(ar,95):+.1%}]")

# deployment scenarios
print("\n=== deployment scenarios (Sharpe) ===")
for lbl, s in [("1.0 bp spread", net_series(spread=1.0)),
               ("1.5 bp spread (base)", base),
               ("2.0 bp spread", net_series(spread=2.0)),
               ("2.0 bp + weekly swap leak", net_series(spread=2.0, swap_weekly_leak=True))]:
    rr = s.to_numpy()
    print(f"  {lbl:28s}: Sharpe {sharpe(rr):.2f} | ann.ret {rr.mean()*ANN:+.1%} | maxDD {max_dd(rr):.1%}")

# entry/exit time perturbation
print("\n=== execution-time robustness (complete-window, 1.5 bp) ===")
for lbl, hrs in [("base 23:00->07:00", WIN), ("enter 1h late (00->07)", [0, 1, 2, 3, 4, 5, 6]),
                 ("exit 1h early (23->06)", [23, 0, 1, 2, 3, 4, 5]), ("exit 1h late (23->08)", WIN + [7])]:
    print(f"  {lbl:24s}: Sharpe {sharpe(net_series(hrs).to_numpy()):.2f}")
