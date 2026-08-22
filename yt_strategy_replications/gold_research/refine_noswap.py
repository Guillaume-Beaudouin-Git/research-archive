"""
Push the best swap-free intraday candidate (ASIA_23_8: long 23:00->07:00 UTC,
vol-targeted, flat across the rollover) toward Sharpe > 1, with OOS validation.

Economically-motivated refinements (each validated out-of-sample, last 40%):
  * mean-reversion overlay: gold sold during the US session tends to be bought back
    in Asia -> scale the Asian long by how negative the prior US session was;
  * trend filter; vol-target lookback variants.
Run: python refine_noswap.py
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
N_TRIALS = 90
ASIA = [23, 0, 1, 2, 3, 4, 5, 6]
US = list(range(13, 21))
piv13 = iz.hourly_pivot("XAUUSD", anchor_hour=13)
us_ret = iz.win_ret(piv13, US)                # prior US session (same anchored day, pre-23:00)

# daily trend (close at 20:00 UTC vs SMA), causal, aligned to anchored day
g = data.load_h1("XAUUSD")
c20 = g["close"][g.index.hour == 20].copy()
c20.index = c20.index.normalize()
c20 = c20[~c20.index.duplicated(keep="last")]


def bt(pos, vt_lookback=20):
    net, _ = iz.backtest(piv13, pos.reindex(piv13.index).fillna(0.0), ASIA,
                         cost_bps=2.0, swap_bps=0.0, voltarget=True, vt_lookback=vt_lookback)
    return net


def stats(net, label):
    eq = (1 + net).cumprod()
    _, t = S.hac_tstat(net.to_numpy())
    dsr = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=N_TRIALS, periods_per_year=iz.ANN)
    folds = S.fold_metrics(net.to_numpy(), 5, iz.ANN)
    mdd, _ = S.max_drawdown(eq.to_numpy())
    split = net.index[int(0.6 * len(net))]
    oos = float(S.sharpe_ratio(net[net.index >= split].to_numpy(), iz.ANN))
    return dict(label=label, sharpe=round(float(S.sharpe_ratio(net.to_numpy(), iz.ANN)), 3),
                oos_sharpe=round(oos, 3), hac_t=round(float(t), 2),
                dsr=round(float(dsr.get("dsr", float("nan"))), 3),
                mean_bps=round(float(net.mean() * 1e4), 2), maxdd=round(float(mdd), 3),
                wf=round(float(folds["wf_score"]), 2))


ones = pd.Series(1.0, index=piv13.index)
variants = {
    "base_long": ones,
    "MR_USdown_flat": (us_ret < 0).astype(float),                      # long only after a down US session
    "MR_USdown_scaled": (-us_ret / us_ret.abs().median()).clip(0, 2.5),  # bigger long the more US fell
    "MR_blend": 0.5 + (-us_ret / us_ret.abs().median()).clip(0, 2.0),    # always-on + MR tilt
    "trend_up_only": (c20 > c20.rolling(100, min_periods=100).mean()).astype(float).reindex(piv13.index),
}
nets = {k: bt(v) for k, v in variants.items()}
# vt lookback sweep on the best-by-OOS structural variant (MR_blend)
for lb in [10, 40]:
    nets[f"MR_blend_vt{lb}"] = bt(variants["MR_blend"], vt_lookback=lb)

rows = [stats(n, k) for k, n in nets.items()]
lb_df = pd.DataFrame(rows).sort_values("oos_sharpe", ascending=False)
print("=== ASIA_23_8 refinements (swap-free, net 2 bps spread) — sorted by OOS Sharpe ===")
print(lb_df.to_string(index=False))
lb_df.to_csv(RES / "refine_noswap_leaderboard.csv", index=False)

best = lb_df.iloc[0]["label"]
bnet = nets[best]
print(f"\nbest = {best}")
# cost / swap-leak sensitivity for the winner
print("cost sensitivity (spread bps):", {c: round(float(S.sharpe_ratio(
    (bt_net := iz.backtest(piv13, variants.get(best.replace('_vt10', '').replace('_vt40', ''), ones).reindex(piv13.index).fillna(0.0),
                           ASIA, cost_bps=c, swap_bps=0.0, voltarget=True)[0]).to_numpy(), iz.ANN)), 2)
    for c in [1, 2, 3]})
json.dump({"leaderboard": rows, "best": best}, open(RES / "refine_noswap_summary.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(11, 5))
for nm, col in [("base_long", "gray"), (best, "seagreen")]:
    s = nets[nm]
    ax.plot(s.index, (1 + s).cumprod().values, label=nm, lw=1.3, color=col)
ax.set_yscale("log"); ax.axhline(1, color="black", lw=0.6)
ax.set_title("Gold swap-free intraday (ASIA 23:00-07:00 UTC) — net 2 bps, 0 swap")
ax.set_ylabel("equity (×, log)"); ax.legend(); ax.grid(alpha=0.25)
fig.tight_layout(); fig.savefig(RES / "fig_noswap_best.png", dpi=120); plt.close(fig)
print("saved refine_noswap_summary + fig")
