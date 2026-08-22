"""Skew research session_3 — PHASE 1: raw edge (no cost), exploratory, generous gate.
Gate: raw t>2 AND skew>=0 -> phase 2 (skew<0 = flag, not auto-kill). Naked literature signals (L10)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
NQ="cache/NQ_rth.parquet"; CAL="/sessions/stoic-vigilant-meitner/mnt/data/panels/economic_calendar.csv"

d=pd.read_parquet(NQ)
g=d.groupby("date")
daily=pd.DataFrame({"o":g["open"].first(),"c":g["close"].last(),
                    "c30":g.apply(lambda x:x.loc[x.rth_min==30,"close"].iloc[0] if (x.rth_min==30).any() else np.nan),
                    "c270":g.apply(lambda x:x.loc[x.rth_min==270,"close"].iloc[0] if (x.rth_min==270).any() else np.nan),
                    "c360":g.apply(lambda x:x.loc[x.rth_min==360,"close"].iloc[0] if (x.rth_min==360).any() else np.nan)})
daily.index=pd.to_datetime(daily.index)
daily["pc"]=daily.c.shift(1)
daily["intraday"]=daily.c/daily.o-1
daily["overnight"]=daily.o/daily.pc-1
daily["first30"]=daily.c30/daily.o-1
daily["last30"]=daily.c/daily.c360-1
daily["prefomc"]=daily.c270/daily.pc-1   # prior close -> 2pm ET (FOMC announce window)

def stat(x,lab):
    x=pd.Series(x).dropna(); m=x.mean()*1e4; t=m/(x.std()*1e4/np.sqrt(len(x))) if x.std()>0 else 0
    hit=(x>0).mean(); sk=skw(x) if len(x)>5 else np.nan
    # tail concentration: share of total positive P&L from top-5% days
    top=np.sort(x.values)[::-1][:max(1,int(0.05*len(x)))].sum(); tot=x[x>0].sum()
    conc=top/tot if tot>0 else np.nan
    print(f"  {lab:34s} n={len(x):5d} mean={m:+.2f}bps t={t:+.2f} hit={hit:.2f} skew={sk:+.2f} top5%P&L={conc:.0%}")
    return dict(n=len(x),mean=m,t=t,hit=hit,skew=sk)

print("=== PHASE 1 raw edge (no cost) ===")
# C1 pre-FOMC
cal=pd.read_csv(CAL); fomc=set(pd.to_datetime(cal[cal.event=="FOMC"]["date"]).dt.normalize())
fd=daily[daily.index.normalize().isin(fomc)]
print("C1 Pre-FOMC drift (prior close -> 2pm ET on FOMC day), LONG:")
stat(fd["prefomc"],"pre-FOMC window long")
stat(daily.loc[daily.index.normalize().isin(fomc),"overnight"]+daily.loc[daily.index.normalize().isin(fomc),"prefomc"],"  (alt: full pre-day+morning)")

print("C2 PEAD on index futures: NO earnings-date data; archive = dead on large-caps since ~2006 -> cite, no compute.")

print("C3 Last-hour momentum (Gao): trade last-30min in sign of first-30min:")
gao=np.sign(daily.first30)*daily.last30
stat(gao,"sign(first30)*last30 two-sided")

print("C4 Conditional overnight (intraday->overnight reversal, Lou-Polk-Skouras):")
# bet overnight reverses the day's intraday move (two-sided, less beta than unconditional)
cond=-np.sign(daily.intraday)*daily.overnight.shift(-1)
stat(cond,"-sign(intraday[t])*overnight[t+1]")
stat(daily.overnight,"  (ref: UNconditional overnight = beta)")

print("C5 OPEX seasonality: 3rd-Friday windows:")
idx=daily.index; opex=[]
for (y,m),grp in daily.groupby([idx.year,idx.month]):
    fri=grp.index[grp.index.weekday==4]
    if len(fri)>=3: opex.append(fri[2])   # 3rd Friday
opex=pd.DatetimeIndex(opex)
quad=opex[opex.month.isin([3,6,9,12])]
dret=daily.c/daily.pc-1
stat(dret.reindex(opex),"OPEX-day return (all months)")
stat(dret.reindex(quad),"quad-witching day return")
# OPEX week (Mon-Fri cumulative ending 3rd Fri)
wk=[]
for f in opex:
    w=daily.loc[(daily.index> f-pd.Timedelta(days=7))&(daily.index<=f),"c"]
    if len(w)>=3: wk.append(w.iloc[-1]/w.iloc[0]-1)
stat(pd.Series(wk),"OPEX-week cum return (all)")
