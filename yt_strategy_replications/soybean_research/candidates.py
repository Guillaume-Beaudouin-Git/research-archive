"""
SOYBEAN.c (FTMO CFD) intraday candidates — swap-free (flat across the 19:20-01:00
UTC halt/rollover), spread cost only. The binding cost is the wide CFD spread
(~13 bp one-way, ~26 bp round-trip). Tests momentum + seasonality + session and
reports gross edge vs the cost floor and the break-even spread.
Run: python candidates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import stats as S  # noqa: E402
import importlib.util
spec = importlib.util.spec_from_file_location("iz", HERE.parent / "gold_research" / "intraday.py")
iz = importlib.util.module_from_spec(spec); spec.loader.exec_module(iz)  # reuse the engine

ANN = 252.0
RT_SPREAD = 26.0   # round-trip CFD spread (bp) — the binding cost
piv = iz.hourly_pivot("SOYBEAN", anchor_hour=0)
ones = pd.Series(1.0, index=piv.index)
print(f"soybean trading days: {len(piv)}  ({piv.index.min().date()} -> {piv.index.max().date()})")


def sgn(hours):
    return np.sign(iz.win_ret(piv, hours))


def evaluate(name, position, trade_hours, vt=True):
    out = {"name": name}
    for sp in (0.0, RT_SPREAD):
        net, m = iz.backtest(piv, position, trade_hours, cost_bps=sp, swap_bps=0.0, voltarget=vt)
        tag = "gross" if sp == 0 else "net26"
        out[f"sharpe_{tag}"] = round(m["sharpe_net"], 2)
        out[f"bps_{tag}"] = round(m["mean_bps"], 2)
    out["breakeven_spread_bps"] = out["bps_gross"]   # gross edge per trade in bp
    _, t = S.hac_tstat(iz.backtest(piv, position, trade_hours, cost_bps=0.0, voltarget=vt)[0].to_numpy())
    out["gross_hac_t"] = round(float(t), 2)
    return out


US = list(range(13, 19))
candidates = [
    ("SEAS_reopen_1_2", ones, [1, 2]),
    ("SEAS_reopen_1_3", ones, [1, 2, 3]),
    ("SEAS_elec_1_7", ones, [1, 2, 3, 4, 5, 6]),
    ("MOM_elec->US", sgn([1, 2, 3, 4, 5, 6, 7]), US),
    ("MOM_preUS->US", sgn(list(range(1, 13))), US),
    ("US_long", ones, US),
    ("US_short", -ones, US),
    ("FULLDAY_long_1_18", ones, list(range(1, 19))),
]
rows = [evaluate(*c) for c in candidates]
df = pd.DataFrame(rows)[["name", "sharpe_gross", "sharpe_net26", "bps_gross", "bps_net26",
                         "gross_hac_t", "breakeven_spread_bps"]]
print("\n=== candidates: gross vs net (26 bp RT spread) ===")
print(df.to_string(index=False))
print(f"\nbinding cost: round-trip CFD spread ~{RT_SPREAD} bp.  A candidate is viable only if")
print("its GROSS edge per trade (breakeven_spread_bps) exceeds the RT spread.")

# best gross candidate: spread sensitivity
best = df.loc[df["bps_gross"].idxmax(), "name"]
pos_map = dict((c[0], (c[1], c[2])) for c in candidates)
p, h = pos_map[best]
print(f"\n=== spread sensitivity — best-gross candidate '{best}' (net Sharpe) ===")
for sp in [0, 3, 5, 8, 13, 26]:
    net, m = iz.backtest(piv, p, h, cost_bps=sp, swap_bps=0.0, voltarget=True)
    print(f"  spread {sp:2d} bp RT -> Sharpe {m['sharpe_net']:+.2f} | mean {m['mean_bps']:+.2f} bp/day")
