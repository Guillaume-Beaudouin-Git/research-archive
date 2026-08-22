"""
Gold XAUUSD intraday EDA — find where structural edges live before building.

Outputs: hourly return/vol/volume profile, day-of-week, and an intraday-momentum
scan (does the cumulative return over a signal window predict a later trade
window? — Gao-Han-Li-Zhou 2018, "Market Intraday Momentum"). All gross; costs
applied later.
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
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402

RES = HERE / "results"
RES.mkdir(exist_ok=True)

g = data.load_h1("XAUUSD")
g["lr"] = np.log(g["close"] / g["close"].shift(1))
g = g.dropna(subset=["lr"])
g["hour"] = g.index.hour
g["dow"] = g.index.dayofweek
g["date"] = g.index.normalize()

# 1) hourly profile (UTC)
prof = g.groupby("hour").agg(mean_ret=("lr", "mean"), absret=("lr", lambda x: x.abs().mean()),
                             vol=("tick_volume", "mean"), n=("lr", "size"))
prof["mean_bps"] = prof["mean_ret"] * 1e4
prof["absret_bps"] = prof["absret"] * 1e4
print("=== hourly profile (UTC) ===")
print(prof[["mean_bps", "absret_bps", "vol", "n"]].round(2).to_string())

# 2) day-of-week
dow = g.groupby("dow")["lr"].agg(["mean", "count"])
dow["mean_bps"] = dow["mean"] * 1e4
print("\n=== day-of-week (0=Mon) ===")
print(dow.round({"mean_bps": 2}).to_string())

# 3) hourly return pivot (date x hour)
piv = g.pivot_table(index="date", columns="hour", values="lr", aggfunc="sum")
piv = piv[piv.notna().sum(axis=1) >= 18].fillna(0.0)
print(f"\ncomplete trading days: {len(piv)}  ({piv.index.min().date()} -> {piv.index.max().date()})")


def cum(hours):
    return piv[[h for h in hours if h in piv.columns]].sum(axis=1)


signals = {
    "asia_00_07": list(range(0, 7)),
    "london_07_09": [7, 8],
    "preUS_00_13": list(range(0, 13)),
    "usOpen_13": [13],
    "usOpen_13_14": [13, 14],
    "usOpen_13_15": [13, 14, 15],
}
trades = {
    "usPM_15_21": list(range(15, 21)),
    "usLast_20": [20],
    "usLast_19_21": [19, 20],
    "us_13_21": list(range(13, 21)),
}

print("\n=== intraday-momentum scan: position = sign(signal) held over trade window (gross) ===")
rows = []
for sn, sh in signals.items():
    rs = cum(sh)
    for tn, th in trades.items():
        if set(sh) & set(th):
            continue
        rt = cum(th)
        strat = np.sign(rs) * rt
        _, t = S.hac_tstat(strat.to_numpy())
        rows.append(dict(signal=sn, trade=tn, corr=float(np.corrcoef(rs, rt)[0, 1]),
                         sharpe=float(S.sharpe_ratio(strat.to_numpy(), 252)),
                         hac_t=float(t), mean_bps=float(strat.mean() * 1e4),
                         hit=float((np.sign(rs) == np.sign(rt)).mean())))
scan = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
scan.to_csv(RES / "eda_momentum_scan.csv", index=False)
print(scan.round({"corr": 3, "sharpe": 2, "hac_t": 2, "mean_bps": 2, "hit": 3}).to_string(index=False))

# 4) figure: hourly profile
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
a1.bar(prof.index, prof["mean_bps"], color=["seagreen" if v > 0 else "indianred" for v in prof["mean_bps"]])
a1.axhline(0, color="black", lw=0.8); a1.set_ylabel("mean return (bps)")
a1.set_title("XAUUSD intraday profile by hour (UTC), 2007–2026")
a2.bar(prof.index, prof["absret_bps"], color="steelblue", alpha=0.8)
a2.set_ylabel("avg |return| (bps)"); a2.set_xlabel("hour (UTC)"); a2.set_xticks(range(0, 24))
fig.tight_layout(); fig.savefig(RES / "fig_hourly_profile.png", dpi=120); plt.close(fig)
print("\nsaved eda_momentum_scan.csv + fig_hourly_profile.png")
