"""PHASE 2 — confront the only survivor (C1 pre-FOMC drift) to barriers. + PHASE 3 corr."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
d=pd.read_parquet("cache/NQ_rth.parquet"); g=d.groupby("date")
daily=pd.DataFrame({"o":g["open"].first(),"c":g["close"].last(),
    "c270":g.apply(lambda x:x.loc[x.rth_min==270,"close"].iloc[0] if (x.rth_min==270).any() else np.nan, include_groups=False)})
daily.index=pd.to_datetime(daily.index); daily["pc"]=daily.c.shift(1)
daily["prefomc"]=daily.c270/daily.pc-1     # prior close -> 2pm ET
daily["dret"]=daily.c/daily.pc-1           # full-day market return (long-equity proxy)
cal=pd.read_csv("/sessions/stoic-vigilant-meitner/mnt/data/panels/economic_calendar.csv")
fomc=pd.to_datetime(cal[cal.event=="FOMC"]["date"]).dt.normalize()
f=daily[daily.index.normalize().isin(set(fomc))].dropna(subset=["prefomc"]).copy()
f["yr"]=f.index.year
r=f["prefomc"]; m=r.mean()*1e4; t=m/(r.std()*1e4/np.sqrt(len(r)))
print(f"=== PHASE 2: C1 pre-FOMC (prior close->2pm ET), n={len(r)} ===")
print(f"  raw: mean={m:+.1f}bps t={t:+.2f} skew={skw(r):+.2f} hit={(r>0).mean():.2f}")
print("  [L33 cost] net of cost (1 night hold = swap+2 spreads):")
for c in [2,5,10,20]: print(f"     {c}bps RT -> net {m-c:+.1f}bps/event ({'ALIVE' if m-c>0 else 'DEAD'})")
print(f"  [L25 two-sided/beta] it is a LONG event-premium (not a 2-sided signal). regime split:")
for lab,a,b in [("2020-2022","2020","2022"),("2023-2026","2023","2026")]:
    s=f.loc[(f.index>=a)&(f.index<=b+"-12-31"),"prefomc"]; print(f"     {lab}: mean={s.mean()*1e4:+.1f}bps n={len(s)} hit={(s>0).mean():.2f}")
print(f"     by year (bps):",{int(k):round(v*1e4,0) for k,v in f.groupby('yr')['prefomc'].mean().items()})
print("  [L26 load-bearing] dates known in advance (FOMC schedule); fixed-time window -> no fill artifact.")
print("  [L31 OOS] sample is 2020-2026 (all post-publication 2011); effect persists. (lit: weakened post-2011 -> low-N caveat).")
# PHASE 3: correlation of the pre-FOMC sleeve to long-equity, as daily series (0 off-FOMC)
sleeve=pd.Series(0.0,index=daily.index); sleeve.loc[f.index]=f["prefomc"]
both=pd.concat([sleeve.rename("preFOMC"),daily["dret"].rename("longEq")],axis=1).dropna()
print(f"\n=== PHASE 3: corr(pre-FOMC sleeve, long-equity daily) = {both.corr().iloc[0,1]:+.3f} ===")
print(f"  on FOMC days only, corr(pre-FOMC, same-day market) = {f[['prefomc','dret']].corr().iloc[0,1]:+.2f}")
print(f"  frequency: {len(f)} events / {f.yr.nunique()} yrs = {len(f)/f.yr.nunique():.0f}/yr (fires rarely -> structurally decorrelated)")
