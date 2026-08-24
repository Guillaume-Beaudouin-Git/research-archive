"""VOLET C — does FTMO Swing swap turn the always-on BTC trend sleeve net-negative?
Swap −30%/yr = 8.22 bps/night (x3 Fri) on held notional, both sides. Comm 6.5 + spread 4 bps/RT."""
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("<HOME>/Desktop/Algo_claude")
btc = pd.read_csv(ROOT/"data/panels/btc_full.csv", parse_dates=["Date"]).set_index("Date")["BTC-USD"].astype(float).sort_index()
r = np.log(btc).diff()
mom = np.sign(sum((btc/btc.shift(n)-1.0) for n in (60,120,250)))
vol = (r.rolling(60).std()*np.sqrt(365)).clip(lower=1e-3)
pos = (mom*(0.10/vol)).clip(-3,3).shift(1)          # notional/equity, vol-target 10%, no look-ahead
gross = pos*r
# swap: 8.22 bps/night on |pos|, x3 Friday (Fri=4). trade cost: (6.5+4)=10.5 bps on |Δpos|
swap_night = 8.22e-4
fri = pd.Series(btc.index.dayofweek==4, index=btc.index).astype(float)*2 + 1   # x3 Fri, x1 else
swap = -np.abs(pos)*swap_night*fri
tc = -np.abs(pos.diff())*10.5e-4
net = gross+swap+tc

def sh(x): x=x.dropna(); return x.mean()/x.std()*np.sqrt(365)
def ann(x): return x.dropna().mean()*365*100
for lab, idx in [("full 2014+", gross.dropna().index), ("2023+", gross.loc["2023":].dropna().index)]:
    g, n, s, t = gross.loc[idx], net.loc[idx], swap.loc[idx], tc.loc[idx]
    print(f"=== {lab}  N={len(idx)}  avg|pos|={np.abs(pos.loc[idx]).mean():.2f} ===")
    print(f"  GROSS: Sharpe {sh(g):+.2f}  ann {ann(g):+.1f}%")
    print(f"  swap drag {ann(s):+.1f}%/yr   trade drag {ann(t):+.1f}%/yr")
    print(f"  NET(swap+cost): Sharpe {sh(n):+.2f}  ann {ann(n):+.1f}%   [swap kill: net<=0 -> NO-GO]")
# regime-gated (report #2 sleeve: long only in bull-calm) for contrast
up = (btc>btc.rolling(50).mean()); lo = (vol<vol.rolling(500).median())
posr = ((up&lo).astype(float)*(0.10/vol)).clip(0,3).shift(1)
netr = posr*r - np.abs(posr)*swap_night*fri - np.abs(posr.diff())*10.5e-4
print(f"\n=== regime-gated (long bull-calm only) 2014+ : NET Sharpe {sh(netr.dropna()):+.2f} ann {ann(netr):+.1f}%  frac-in-mkt {(posr>0).mean():.2f} ===")
