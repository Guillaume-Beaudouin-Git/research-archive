import pandas as pd, numpy as np
syms=["US100","US500","US30","US2000"]
full=pd.read_parquet("/sessions/stoic-vigilant-meitner/mnt/data/panels/m5_indices/m1_panel.parquet")
p=pd.DataFrame({s:full[(s,"close")] for s in syms})
idx=pd.to_datetime(p.index.values)
tod=idx.hour*60+idx.minute
mask=(tod>=16*60+30)&(tod<=22*60+55)
p=p.iloc[mask]; idx=idx[mask]; tod=tod[mask]
datekey=idx.year*10000+idx.month*100+idx.day
C=p.values  # [n,4]
df=pd.DataFrame(C,columns=syms); df["dk"]=datekey; df["tt"]=tod
opn=df.groupby("dk",sort=True).first()
end=df.groupby("dk",sort=True).last()
mid=df[df["tt"]<=17*60].groupby("dk",sort=True).last()
j=opn.index.intersection(mid.index).intersection(end.index)
O=opn.loc[j,syms].values; Mi=mid.loc[j,syms].values; E=end.loc[j,syms].values
morning=Mi/O-1; afternoon=E/Mi-1
cost=1e-4
w=morning-morning.mean(1,keepdims=True); w=w/np.abs(w).sum(1,keepdims=True)
mom=(w*afternoon).sum(1)-cost*np.abs(w).sum(1)
rev=(-w*afternoon).sum(1)-cost*np.abs(w).sum(1)
sh=lambda x: np.nanmean(x)/np.nanstd(x)*np.sqrt(252)
print(f"xsec MOMENTUM: mean/day={np.nanmean(mom)*1e4:+.2f}bps Sharpe={sh(mom):+.2f} n={len(mom)}")
print(f"xsec REVERSION: mean/day={np.nanmean(rev)*1e4:+.2f}bps Sharpe={sh(rev):+.2f}")
s=pd.Series(mom,index=pd.to_datetime(j.astype(str),format="%Y%m%d"))
bk=pd.read_parquet("cache/WIN_book.parquet")["rmult"]
al=pd.concat([s.rename("xs"),bk.rename("bk")],axis=1).dropna()
print(f"corr(xsec, long-ORB book)={al.corr().iloc[0,1]:+.2f} | overlap {len(al)}")
s.to_frame("rmult").to_parquet("cache/xsec_mom.parquet")
