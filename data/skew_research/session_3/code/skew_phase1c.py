"""Batch 3 PHASE 1 (daily/monthly) — FTMO-tradeable instruments only. Naked/literature signals (L10).
#1 pre-OPEX index drift (gamma proxy), #2 TOM conditioned on month perf, #4 commodity seasonality (skew/corr lens)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
cl=pd.read_csv(P+"ftmo_close.csv",parse_dates=["Date"]).set_index("Date").sort_index()
def desc(x,lab):
    x=pd.Series(x).dropna()
    if len(x)<8: print(f"  {lab:44s} n={len(x)} insuff"); return
    m=x.mean()*1e4; t=m/(x.std()*1e4/len(x)**.5)
    print(f"  {lab:44s} n={len(x):4d} mean={m:+.1f}bps t={t:+.2f} skew={skw(x):+.2f} hit={(x>0).mean():.2f}")

print("=== B3-1 Pre-OPEX index drift (US500=SPX, FTMO-tradeable), gamma PROXY (no OI/GEX data) ===")
s=cl["US500"].dropna(); idx=s.index; opex=[]
for (y,m),g in s.groupby([idx.year,idx.month]):
    fri=g.index[g.index.weekday==4]
    if len(fri)>=3: opex.append(fri[2])
opex=pd.DatetimeIndex(opex); pos=s.index.get_indexer(opex)
keep=pos>=25; opex,pos=opex[keep],pos[keep]
wk=pd.Series(s.values[pos]/s.values[pos-5]-1,index=opex)
prior=pd.Series(s.values[pos-5]/s.values[pos-25]-1,index=opex)
rv=pd.Series([np.std(np.diff(np.log(s.values[p-25:p-5]))) for p in pos],index=opex)
desc(wk,"OPEX week naked (ref)")
desc(wk[prior>0],"OPEX week | prior-trend UP (long-gamma/pin proxy)")
desc(wk[prior<0],"OPEX week | prior-trend DOWN (short-gamma proxy)")
desc(wk[rv<rv.median()],"OPEX week | low-RV (long-gamma proxy)")
desc(wk[rv>=rv.median()],"OPEX week | high-RV (short-gamma proxy)")

print("=== B3-2 TOM conditioned on month perf (rebound of underperformer) ===")
inds=["US30","GER40","US500","US100","US2000","JP225","HK50","UK100","EU50","AUS200"]
mret={}; f3={}
for c in inds:
    x=cl[c].dropna(); lr=np.log(x).diff(); ym=x.index.to_period("M"); ds=x.groupby(ym).cumcount()+1
    mret[c]=lr.groupby(ym).sum()
    f3[c]=pd.Series(lr.values[ds.values<=3],index=ym.values[ds.values<=3]).groupby(level=0).sum()
MR=pd.DataFrame(mret); F3=pd.DataFrame(f3)
desc(F3["US500"],"first-3-day US500 naked (ref)")
desc((-np.sign(MR["US500"].shift(1))*F3["US500"]).dropna(),"TS US500: -sign(prev m) x first3 [long loser]")
pr=MR.shift(1).rank(axis=1); mx=pr.max(axis=1)
longw=pr<=2; shortw=pr.ge((mx-1).values[:,None])
desc((F3[longw].mean(axis=1)-F3[shortw].mean(axis=1)).dropna(),"XS: long 2 prev-losers - short 2 winners")

print("=== B3-4 Commodity seasonality (FTMO-tradeable; archive keeper Sharpe0.30 -> skew/corr lens, NOT re-proving) ===")
com=pd.read_csv(P+"commodity_panel.csv",parse_dates=["Date"]).set_index("Date").sort_index()
mc=np.log(com).resample("ME").last().diff()
sig=pd.DataFrame(index=mc.index,columns=mc.columns,dtype=float)
for col in mc.columns:
    x=mc[col].dropna()
    for i in range(13,len(x)):
        cm=x.index[i].month; past=x.iloc[:i]
        sig.loc[x.index[i],col]=np.sign(past[past.index.month==cm].mean())
port=(sig*mc).mean(axis=1).dropna()
desc(port,"commodity seasonality sleeve (monthly OOS expanding)")
spy=np.log(pd.read_csv(P+"factor_etf_panel.csv",parse_dates=["Date"]).set_index("Date")["SPY"]).resample("ME").last().diff()
cc=pd.concat([port.rename("c"),spy.rename("s")],axis=1).dropna()
print(f"  corr(commodity-seasonality, SPY monthly) = {cc.corr().iloc[0,1]:+.3f}  n={len(port)}")
