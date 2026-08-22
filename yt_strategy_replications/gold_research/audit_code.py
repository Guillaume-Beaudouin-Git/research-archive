"""
CODE / LOGIC AUDIT for ASIA_23_8 (long XAUUSD 23:00->07:00 UTC, vol-targeted).

Checks: (1) independent reimplementation from raw H1 closes must match the pivot
backtest; (2) the edge is not manufactured by vol-targeting (no-VT still positive)
nor by look-ahead (a deliberately-cheating future-vol sizing is much higher);
(3) permutation/sign nulls behave correctly; (4) parameter neighbourhood is a
plateau, not a spike.
Run: python audit_code.py
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
import intraday as iz  # noqa: E402

ANN = 252.0
piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)
ones = pd.Series(1.0, index=piv13.index)
ASIA = [23, 0, 1, 2, 3, 4, 5, 6]
SPREAD = 1.5


def sharpe(x):
    return float(S.sharpe_ratio(np.asarray(x), ANN))


def get_net(hours=ASIA, vt=True, spread=SPREAD, swap=0.0, position=None):
    pos = ones if position is None else position
    net, _ = iz.backtest(piv13, pos, hours, cost_bps=spread, swap_bps=swap, voltarget=vt)
    return net


# 1) INDEPENDENT REIMPLEMENTATION from raw prices (entry 23:00 close, exit 07:00 close)
g = data.load_h1("XAUUSD")
ch = {h: g["close"][g.index.hour == h].copy() for h in (22, 6)}
for h in ch:
    ch[h].index = ch[h].index.normalize()
    ch[h] = ch[h][~ch[h].index.duplicated(keep="last")]
entry = ch[22]                          # close at 22:00 (~23:00 entry) on date D
exit_ = ch[6].shift(-1).reindex(entry.index)   # close at 06:00 of D+1 (the exit)
wret = np.log(exit_ / entry).dropna()           # window return per entry date
rv = wret.rolling(20, min_periods=20).std().shift(1)
scale = (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)
net_indep = (scale * wret - scale.abs() * SPREAD * 1e-4).dropna()

net_piv = get_net()
common = net_indep.index.intersection(net_piv.index)
corr = float(np.corrcoef(net_indep.reindex(common).fillna(0), net_piv.reindex(common).fillna(0))[0, 1])
print("=== 1. independent reimplementation cross-check ===")
print(f"  pivot Sharpe {sharpe(net_piv):.3f} | raw-price Sharpe {sharpe(net_indep):.3f} | "
      f"return corr {corr:.3f}  ({len(common)} common days)")

# 2) is the edge manufactured by VT or by look-ahead?
no_vt = get_net(vt=False)
# cheating: size inversely to the SAME day's realised vol (uses future info at entry)
cheat_scale = (wret.abs().expanding().median() / wret.abs().rolling(1).mean()).clip(upper=3.0)
cheat = (cheat_scale * wret - cheat_scale.abs() * SPREAD * 1e-4).dropna()
print("\n=== 2. VT / look-ahead attribution ===")
print(f"  no vol-target (constant long): Sharpe {sharpe(no_vt):.3f}")
print(f"  causal VT (deployed)         : Sharpe {sharpe(net_piv):.3f}")
print(f"  CHEAT same-day-vol sizing     : Sharpe {sharpe(cheat):.3f}   (look-ahead upper bound)")

# 3) permutation / sign nulls
rng = np.random.default_rng(0)
perm = [sharpe(rng.permutation(wret.to_numpy()) * scale.to_numpy()[:len(wret)]) for _ in range(200)]
flip = get_net(position=-ones)
print("\n=== 3. nulls ===")
print(f"  shuffled-returns Sharpe: mean {np.mean(perm):+.2f}, 95th pct {np.percentile(perm,95):+.2f} (should be ~0)")
print(f"  SHORT instead of long  : Sharpe {sharpe(flip):+.2f} (should be clearly negative)")

# 4) parameter neighbourhood (plateau vs spike)
print("\n=== 4. parameter neighbourhood — Sharpe (net 1.5 bp), * = >1 ===")
print("  start\\len   4      6      8     10     12")
grid_vals = []
for start in [21, 22, 23, 0]:
    row = []
    for length in [4, 6, 8, 10, 12]:
        w = [(start + i) % 24 for i in range(length)]
        sw = 3.3 if (21 in w or 22 in w) else 0.0   # honest: rollover windows pay swap
        s = sharpe(get_net(hours=w, swap=sw))
        row.append(s)
        grid_vals.append(s)
    print(f"  {start:02d}:00     " + " ".join(f"{v:5.2f}{'*' if v > 1 else ' '}" for v in row))
def vt_net(lb):
    rv2 = wret.rolling(lb, min_periods=lb).std().shift(1)
    sc = (rv2.expanding(min_periods=lb).median() / rv2).clip(upper=3.0).fillna(0.0)
    return (sc * wret - sc.abs() * SPREAD * 1e-4).dropna()

print("\n  vt-lookback sweep (raw-price ASIA_23_8): " +
      " ".join(f"vt{lb}={sharpe(vt_net(lb)):.2f}" for lb in [10, 20, 40, 60]))
print("\nNote: cells with start 21/22 include the rollover hour -> swap charged (-3.3 bp);")
print("the swap-free plateau (start 23/0) is the deployable region.")
