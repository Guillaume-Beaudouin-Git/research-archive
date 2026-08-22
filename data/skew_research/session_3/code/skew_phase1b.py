"""Skew session_3 — batch 2 (flux/mechanical). PHASE 1 raw edge. Naked signals (L10)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
fac=pd.read_csv(P+"factor_etf_panel.csv",parse_dates=["Date"]).set_index("Date").sort_index()
mac=pd.read_csv(P+"macro_etf_panel.csv",parse_dates=["Date"]).set_index("Date").sort_index()
df=pd.concat([fac["SPY"],mac[["TLT","IEF","DBC","GLD"]]],axis=1).dropna()
R=np.log(df).diff()
ym=df.index.to_period("M")
dstart=df.groupby(ym).cumcount()+1
dend=df.groupby(ym).cumcount(ascending=False)+1
def stat(x,lab):
    x=pd.Series(x).dropna()
    if len(x)<5: print(f"  {lab:34s} n={len(x)} (insufficient)"); return
    m=x.mean()*1e4; t=m/(x.std()*1e4/np.sqrt(len(x))); print(f"  {lab:34s} n={len(x):4d} mean={m:+.2f}bps t={t:+.2f} hit={(x>0).mean():.2f} skew={skw(x):+.2f}")
print(f"data {df.index.min().date()}..{df.index.max().date()}")
print("\n=== C1 Month-end rebalancing (Etula 'dash for cash') ===")
# (a) bond month-end rally: TLT return on last 3 days of month
stat(R["TLT"][dend.values<=3],"(a) TLT last-3-day-of-month LONG")
stat(R["SPY"][dend.values<=3],"    SPY last-3-day-of-month")
# (b) rebalance LS: after equities outperform bonds in the month, sell eq/buy bond at month-end
me=pd.DataFrame({"ym":ym,"dend":dend.values,"spy":R.SPY.values,"tlt":R.TLT.values},index=df.index)
mret=me.groupby("ym")[["spy","tlt"]].sum()             # month cumulative
last3=me[me.dend<=3].groupby("ym")[["spy","tlt"]].sum() # last-3-day cumulative
j=mret.join(last3,rsuffix="_l3").dropna()
j["sig"]=-np.sign(j.spy - j.tlt)                        # fade the month's eq-bond divergence
j["ls"]=j.sig*((j.spy_l3)-(j.tlt_l3))                   # apply to eq-bond spread over last 3 days
stat(j["ls"],"(b) rebalance LS (eq-bond fade) ")

print("\n=== C2 Index reconstitution: index-level effect ~0 (single-stock event) + no recon dates -> NOT applicable on index CFD. cite. ===")

print("\n=== C3 Quarter-end window dressing ===")
qe=(df.index.month.isin([3,6,9,12]))&(dend.values<=3)
qstart=(df.index.month.isin([1,4,7,10]))&(dstart.values<=3)
stat(R["SPY"][qe],"SPY quarter-end last-3-day LONG")
stat(R["SPY"][qstart],"SPY 1st-3-day next-Q (reversal?)")

print("\n=== C4 ETF NAV premium/discount arb: need intraday NAV (absent) + ETFs not FTMO-tradeable. cite. ===")

print("\n=== C5 Turn-of-Month MULTI-ASSET (archive: equity TOM dead) ===")
tom=(dend.values==1)|(dstart.values<=3)
for a in ["SPY","TLT","IEF","DBC","GLD"]:
    stat(R[a][tom],f"TOM long {a}")
