"""
Swap-aware gold research. XAUUSD overnight swap is large and asymmetric
(long ~-66/lot/night ~= -3.3 bp at $2000; short ~-14.5 ~= -0.7 bp), so any held-
overnight edge is taxed away (the repo's lessons L30/L36). This script:
  1. shows ON_22_8 collapses once the long swap is charged;
  2. searches for genuinely INTRADAY edges that are FLAT across the 21:00-22:00 UTC
     rollover (swap_bps = 0, spread cost only): swap-free Asian windows + US-session
     momentum.
Run: python intraday_noswap.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from engine import stats as S  # noqa: E402
import intraday as iz  # noqa: E402

RES = HERE / "results"
N_TRIALS = 80
SWAP_LONG = 3.3   # bps/night at ~$2000 (historically larger when gold was cheaper)
piv0 = iz.hourly_pivot("XAUUSD", anchor_hour=0)
piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)
ones13 = pd.Series(1.0, index=piv13.index)


def W(start, length):
    return [(start + i) % 24 for i in range(length)]


def crosses_rollover(hours):
    return (21 in hours) or (22 in hours)


def report(net, label):
    eq = (1 + net).cumprod()
    _, t = S.hac_tstat(net.to_numpy())
    dsr = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=N_TRIALS, periods_per_year=iz.ANN)
    folds = S.fold_metrics(net.to_numpy(), 5, iz.ANN)
    mdd, _ = S.max_drawdown(eq.to_numpy())
    return dict(label=label, sharpe=round(float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), 2),
                hac_t=round(float(t), 2), dsr=round(float(dsr.get("dsr", float("nan"))), 3),
                mean_bps=round(float(net.mean() * 1e4), 2), maxdd=round(float(mdd), 3),
                wf=round(float(folds["wf_score"]), 2))


# 1) ON_22_8 with vs without the long swap
on_nosw, _ = iz.backtest(piv13, ones13, W(22, 8), cost_bps=2.0, swap_bps=0.0, voltarget=True)
on_sw, _ = iz.backtest(piv13, ones13, W(22, 8), cost_bps=2.0, swap_bps=SWAP_LONG, voltarget=True)
print("=== ON_22_8: the swap is fatal ===")
print("  no swap :", report(on_nosw, "ON_22_8_noswap"))
print("  +swap   :", report(on_sw, "ON_22_8_swap3.3"))

# 2) swap-free candidates (flat across 21:00-22:00 rollover -> swap_bps = 0)
cands = {}
# 2a) Asian long windows that avoid the rollover (start >= 23 or 0/1)
for start in [23, 0, 1]:
    for length in [3, 4, 6, 8, 10]:
        w = W(start, length)
        if crosses_rollover(w):
            continue
        net, _ = iz.backtest(piv13, ones13, w, cost_bps=2.0, swap_bps=0.0, voltarget=True)
        cands[f"ASIA_{start}_{length}"] = net
# 2b) US-session momentum (signal = pre-US move; trade 13:00-21:00, flat before rollover)
for sig_h, sname in [(range(0, 13), "preUS"), (range(0, 8), "asia")]:
    base = iz.win_ret(piv0, sig_h)
    for cond, cname in [(False, ""), (True, "cond")]:
        sig = np.sign(base)
        if cond:
            sig = sig.where(base.abs() > base.abs().median(), 0.0)
        net, _ = iz.backtest(piv0, sig, list(range(13, 21)), cost_bps=2.0, swap_bps=0.0, voltarget=True)
        cands[f"MOM_{sname}{cname}"] = net
# 2c) US-session long & short (is there an intraday directional bias?)
cands["US_long"], _ = iz.backtest(piv0, pd.Series(1.0, index=piv0.index), list(range(13, 21)), cost_bps=2.0, voltarget=True)

rows = [report(s, n) for n, s in cands.items()]
lb = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
print("\n=== swap-free intraday candidates (net 2 bps spread, 0 swap) ===")
print(lb.to_string(index=False))
lb.to_csv(RES / "noswap_leaderboard.csv", index=False)

# 3) best swap-free candidate: OOS + cost grid
best = lb.iloc[0]["label"]
bnet = cands[best]
split = bnet.index[int(0.6 * len(bnet))]
oos = float(S.sharpe_ratio(bnet[bnet.index >= split].to_numpy(), iz.ANN))
print(f"\nbest swap-free = {best} | full Sharpe {lb.iloc[0]['sharpe']} | OOS(40%) Sharpe {oos:.2f}")
json.dump({"on_22_8_swap": report(on_sw, "ON_22_8_swap"),
           "leaderboard": rows, "best": best, "best_oos_sharpe": round(oos, 2)},
          open(RES / "noswap_summary.json", "w"), indent=2)
print("saved noswap_summary")
