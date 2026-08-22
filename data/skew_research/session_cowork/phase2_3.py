#!/usr/bin/env python3
"""Phase 2 (barriers, Donchian) + Phase 3 (correlation matrix = the real criterion)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"
OUT = f"{D}/skew_research/session_cowork"
from phase1_engine import load_basket, voltarget_combine, stats

px = load_basket(); rets = px.pct_change().clip(-0.5, 0.5)
hi = px.rolling(20).max().shift(1); lo = px.rolling(20).min().shift(1)

def donchian(lag=1, long_only=False, short_only=False):
    sig = pd.DataFrame(np.where(px > hi, 1.0, np.where(px < lo, -1.0, np.nan)), index=px.index, columns=px.columns).ffill()
    if long_only: sig = sig.clip(lower=0)
    if short_only: sig = sig.clip(upper=0)
    rv = rets.rolling(60).std()*np.sqrt(252)
    pos = (sig*(0.10/rv).clip(upper=5)).shift(lag)
    gross = (pos*rets).sum(1)
    scale = (0.10/(gross.rolling(60).std()*np.sqrt(252))).clip(upper=3).shift(1)
    port = (gross*scale).fillna(0.0)
    turn = pos.diff().abs().sum(1)
    return port, turn

print("=== PHASE 2 — Donchian breakout barriers ===")
base, turn = donchian()
# cost: held-notional swap (measured equity ~4.5 bps/trading-day long proxy) + turnover spread
def net_cost(port, turn, swap_td_bps, spread_bps):
    return port - turn*spread_bps*1e-4 - swap_td_bps*1e-4   # swap as flat daily drag proxy on ~1x book
for sw,sp,lbl in [(0,0,'gross'),(0,2,'+2bps turnover spread'),(4.5,2,'+meas. equity swap 4.5bps/td +spread')]:
    n=net_cost(base,turn,sw,sp); print(f"  {lbl:42s}: Sharpe {stats(n.values,'')['ann_sharpe']:+.2f}  mean {stats(n.values,'')['mean_bps']:+.2f}bps")
# two-sided split (L25)
lo_,_=donchian(long_only=True); sh_,_=donchian(short_only=True)
print(f"  two-sided split: long-only Sharpe {stats(lo_.values,'')['ann_sharpe']:+.2f}  short-only {stats(sh_.values,'')['ann_sharpe']:+.2f}")
# delay+1 (L26)
d2,_=donchian(lag=2); print(f"  delay+1 test: base Sharpe {stats(base.values,'')['ann_sharpe']:+.2f} -> t+2 Sharpe {stats(d2.values,'')['ann_sharpe']:+.2f} (survives delay = real, not microstructure)")
# OOS (L31)
for loY,hiY,nm in [(2006,2016,'IS 06-15'),(2016,2027,'OOS 16-26')]:
    sub=base[(base.index.year>=loY)&(base.index.year<hiY)]; print(f"  {nm}: Sharpe {stats(sub.values,'')['ann_sharpe']:+.2f}  skew {stats(sub.values,'')['skew']:+.2f}")

print("\n=== PHASE 3 — correlation matrix (the selection criterion: skew+ AND decorrelated) ===")
ser = {}
ser["Donchian"] = base
ser["XS-mom"] = pd.read_csv(f"{OUT}/series_XS-momentum.csv", index_col=0, parse_dates=True).iloc[:,0]
ser["Long-vol"] = pd.read_csv(f"{OUT}/series_Long-vol_VXX.csv", index_col=0, parse_dates=True).iloc[:,0]
try:
    ser["TSMOM"] = pd.read_csv(f"{D}/ftmo_research/tsmom/chosen_returns.csv", index_col=0, parse_dates=True).iloc[:,0]
except Exception as e: print("  (TSMOM series unavailable:", e, ")")
ser["Long-US500"] = rets["US500"]
M = pd.DataFrame(ser).dropna()
print(f"  common window {M.index.min().date()}..{M.index.max().date()} n={len(M)}")
corr = M.corr().round(2)
print(corr.to_string())
corr.to_csv(f"{OUT}/phase3_corr.csv")
print("\n  skew of each (daily):", {k: round(float(pd.Series(v).dropna().skew()),2) for k,v in ser.items()})
