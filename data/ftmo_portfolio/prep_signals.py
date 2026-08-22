"""Build daily inputs for the simulator: M5 joint frame, trend weights, ON flag.
Saves: cache/sim_m5.parquet, cache/sim_WT.parquet, cache/sim_ON.parquet
"""
import numpy as np
import pandas as pd
import config as C
from sleeves import trend_book, realized_vol

LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]

# --- M5 joint (CET tz-aware -> naive CET wall time)
m5 = {}
for s in LEGS:
    x = pd.read_parquet(C.CACHE / f"{s}_m5_close.parquet")["close"]
    if x.index.tz is not None:
        x.index = x.index.tz_localize(None)        # already CET wall time
    m5[s] = x
M5 = pd.DataFrame(m5).sort_index()
M5 = M5.loc["2013-09-25":]
M5.to_parquet(C.CACHE / "sim_m5.parquet")
print("M5 joint:", M5.shape, M5.index.min(), "->", M5.index.max())

# --- daily panel signals (same as phase1)
px = pd.read_parquet(C.CACHE / "panel_px.parquet")
rets = pd.read_parquet(C.CACHE / "panel_rets.parquet")
swap_L = pd.read_parquet(C.CACHE / "panel_swapL.parquet")
swap_S = pd.read_parquet(C.CACHE / "panel_swapS.parquet")
mult = pd.read_parquet(C.CACHE / "panel_mult.parquet")
rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]

# gold sleeve positions (vol-targeted 10% book) -> notional fraction series
g = trend_book(rets, px, swap_L, swap_S, mult, rt, {"m": ["XAUUSD"]}, {"m": 1.0},
               carry_adj=True)
w_gold = g["pos"]["XAUUSD"]

# J1: USDJPY 12-1 LO vol-targeted
p = px["USDJPY"].dropna()
mom = p.shift(21) / p.shift(252) - 1.0
sig = (mom > 0).astype(float)
rv = realized_vol(rets["USDJPY"]).clip(lower=1e-4)
w_jpy = (sig * (0.10 / rv).clip(upper=5.0)).shift(1)

WT = pd.DataFrame({"XAUUSD": w_gold, "USDJPY": w_jpy}).fillna(0.0)
# per-leg notional cap (margin/risk practice): vol-target cascade can blow up
# notionals in quiet-vol regimes (p95 was 2.85x, max 9.6x) -> cap at 1.5x
WT = WT.clip(lower=-1.5, upper=1.5)
WT.to_parquet(C.CACHE / "sim_WT.parquet")

# ON flag: hold tonight if today is Mon or Tue (verified midweek premium)
ON = pd.Series(0.0, index=WT.index)
ON[WT.index.dayofweek.isin([0, 1])] = 1.0
ON.to_frame("on").to_parquet(C.CACHE / "sim_ON.parquet")
print("WT:", WT.shape, " gold active %:", (WT['XAUUSD'].abs() > 0).mean().round(2),
      " jpy active %:", (WT['USDJPY'].abs() > 0).mean().round(2))
