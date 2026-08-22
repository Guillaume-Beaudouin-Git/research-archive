"""B1 survivor (month-end bond 'dash for cash') — HOLDING-HORIZON return + delay+1 (L26), cost, corr-to-equity.
Phase-1 refinement requested: skew at the HOLDING horizon (per-trade), not daily. TLT full history 2002-2026."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
mac=pd.read_csv(P+"macro_etf_panel.csv",parse_dates=["Date"]).set_index("Date").sort_index()
r=np.log(mac["TLT"]).diff(); ym=mac.index.to_period("M")
de=mac.groupby(ym).cumcount(ascending=False)+1
def hold(mask,lab):
    tr=pd.Series(r.values[mask],index=ym.values[mask]).groupby(level=0).sum().dropna()
    m=tr.mean()*1e4; t=m/(tr.std()*1e4/len(tr)**.5)
    print(f"  {lab:38s} mean={m:+.1f}bps/trade t={t:+.2f} skew={skw(tr):+.2f} hit={(tr>0).mean():.2f} n={len(tr)}")
    return tr
print("B1 TLT month-end — HOLDING-HORIZON (per-month cumulative) + delay+1:")
hold(de.values<=3,"3-day hold (dend 3,2,1) NO-delay")
hold(de.values<=2,"delay+1 (enter 1d late, hold dend 2,1)")
hold(de.values==1,"last day only (dend 1)")
tr=pd.Series(r.values[de.values<=3],index=ym.values[de.values<=3]).groupby(level=0).sum().dropna()
print("  cost-death (per trade):",{f"{c}bps":round(tr.mean()*1e4-c,1) for c in [2,4,6]})
fac=pd.read_csv(P+"factor_etf_panel.csv",parse_dates=["Date"]).set_index("Date").sort_index()
rs=np.log(fac["SPY"]).diff()
sleeve=pd.Series(0.0,index=mac.index); sleeve[de.values<=3]=r[de.values<=3]
both=pd.concat([sleeve.rename("B1"),rs.rename("SPY")],axis=1).dropna()
print(f"  corr(B1 sleeve daily, SPY) = {both.corr().iloc[0,1]:+.3f}")
