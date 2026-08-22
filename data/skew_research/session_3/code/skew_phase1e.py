"""Batch 4 PHASE 1 — combos multi-indicateurs, versions canoniques SIMPLES (L10, pas de sweep), TWO-SIDED (L25),
délai+1 intégré (pos décidée en t-1, gagne t). FTMO-tradeable (indices US500 / SPY pour volume).
Pour stratégies daily: la barre est le SHARPE annualisé (t trivialement grand à n élevé), + skew."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"; import glob
def col(f): return pd.read_csv(P+f,parse_dates=["Date"]).set_index("Date")["US500"]
df=pd.concat([col("ftmo_open.csv"),col("ftmo_high.csv"),col("ftmo_low.csv"),col("ftmo_close.csv")],
             axis=1,keys=["open","high","low","close"]).dropna().sort_index()
c=df.close; r=np.log(c).diff()
def strat(pos,rr,lab):
    pos=pd.Series(pos,index=rr.index) if not isinstance(pos,pd.Series) else pos
    x=(pos.shift(1)*rr).dropna()
    if len(x)<30: print(f"  {lab:44s} n={len(x)} insuff"); return
    m=x.mean()*1e4; sh=x.mean()/x.std()*np.sqrt(252); t=x.mean()/(x.std()/np.sqrt(len(x)))
    print(f"  {lab:44s} bps/d={m:+.2f} Sharpe={sh:+.2f} t={t:+.1f} skew={skw(x):+.2f} hit={(x>0).mean():.2f} expo={(pos!=0).mean():.0%}")
ma=lambda n: c.rolling(n).mean()
d=c.diff(); up=d.clip(lower=0).rolling(14).mean(); dn=(-d.clip(upper=0)).rolling(14).mean(); rsi=100-100/(1+up/dn)
m20=ma(20); s20=c.rolling(20).std(); upb=m20+2*s20; lob=m20-2*s20
er=(c-c.shift(20)).abs()/c.diff().abs().rolling(20).sum(); treg=er>er.median()

print("=== B4-1 Trend+MR regime-switch (US500). Mechanism 2x2: trend wins trending? MR wins chop? ===")
ts=np.sign(c-c.shift(50)); ms=-np.sign(c-c.shift(5))
strat(ts.where(treg,0),r,"trend sig | TRENDING"); strat(ts.where(~treg,0),r,"trend sig | CHOP")
strat(ms.where(treg,0),r,"MR sig | TRENDING");    strat(ms.where(~treg,0),r,"MR sig | CHOP")
strat(ts.where(treg,ms),r,"SWITCHED sleeve (trend if trending, else MR)")

print("=== B4-3 Double-timeframe momentum (daily 20d & weekly 60d aligned), two-sided ===")
md=np.sign(c-c.shift(20)); mw=np.sign(c-c.shift(60))
strat(md.where(md==mw,0),r,"double-TF aligned"); strat(md,r,"daily mom alone (ref)")

print("=== B4-4 MR filtered by MA200 trend (buy dip in uptrend) — TWO-SIDED beta check ===")
lL=((rsi<30)&(c>ma(200))).astype(float); sL=-((rsi>70)&(c<ma(200))).astype(float)
strat(lL,r,"long dip in UPtrend ONLY (beta leg?)"); strat(sL,r,"short rip in DOWNtrend ONLY")
strat(lL+sL,r,"two-sided combined"); strat((rsi<30).astype(float)-(rsi>70).astype(float),r,"unconditional MR (ref)")

print("=== B4-5 Bollinger + MA200 filter, two-sided ===")
lB=((c<lob)&(c>ma(200))).astype(float); sB=-((c>upb)&(c<ma(200))).astype(float)
strat(lB,r,"BB-lower in UPtrend (long)"); strat(sB,r,"BB-upper in DOWNtrend (short)")
strat(lB+sB,r,"BB+MA200 two-sided"); strat((c<lob).astype(float)-(c>upb).astype(float),r,"BB naked (ref)")

print("=== B4-2 Breakout + VOLUME confirm (SPY, real volume 2015+; FTMO CFD lacks real volume) ===")
sp=pd.read_parquet(glob.glob("/sessions/stoic-vigilant-meitner/mnt/data/raw/yf_SPY_1d_*.parquet")[0])
cs=sp["close"]; rs=np.log(cs).diff(); v=sp["volume"]
hi=cs.rolling(20).max().shift(1); lo=cs.rolling(20).min().shift(1)
brk=pd.Series(np.where(cs>hi,1.0,np.where(cs<lo,-1.0,0.0)),index=cs.index)
volok=v>1.5*v.rolling(20).mean()
strat(brk.where(volok,0),rs,"breakout + volume-confirmed"); strat(brk.where(~volok,0),rs,"breakout WITHOUT volume")
strat(brk,rs,"breakout naked (ref)")
