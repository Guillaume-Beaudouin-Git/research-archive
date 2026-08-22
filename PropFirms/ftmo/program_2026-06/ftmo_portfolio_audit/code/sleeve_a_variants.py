"""
sleeve_a_variants.py — charitable reproduction sweep for Sleeve A's ann Sharpe ~0.97.
Tries every reasonable interpretation to see if ANY hits ~0.97 (positive every year).
"""
from __future__ import annotations
import numpy as np, pandas as pd
from audit_common import load_daily, rsi, point_size, metrics, vol_target, per_year_sharpe, FX

FULL = ["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDCHF","USDJPY","US500","US100","US30","GER40","XAUUSD"]
IDX5 = ["US500","US100","US30","GER40","XAUUSD"]
IDX4 = ["US500","US100","US30","GER40"]
FX_COMM = 5.0/100_000


def sim(df, sym, side="both", regime=None, exit_mode="revert50", thr=10.0, max_hold=8,
        markup=2.0, swap=0.5):
    o=df["open"].values.astype(float); c=df["close"].values.astype(float)
    sp=np.maximum(df["spread_open"].values, df["spread_mean"].values).astype(float)
    sp=np.where(np.isfinite(sp)&(sp>0),sp,np.nan)
    cs=pd.Series(c,index=df.index)
    R=rsi(cs,2).values; ma200=cs.rolling(200).mean().values; ma5=cs.rolling(5).mean().values
    n=len(df); pt=point_size(sym); comm=(FX_COMM/2) if sym in FX else 0.0
    g=np.zeros(n); k=np.zeros(n)
    med=np.nanmedian(sp)
    rts=lambda i: (sp[i] if np.isfinite(sp[i]) else med)*pt*markup/c[i]
    i=205
    while i<n-1:
        longsig = R[i]<thr and (regime is None or c[i]>ma200[i])
        shortsig= R[i]>(100-thr) and (regime is None or c[i]<ma200[i])
        sig = 1 if longsig else (-1 if (shortsig and side=="both") else 0)
        if sig==0: i+=1; continue
        e=i+1
        if e>n-1: break
        g[e]+=sig*(c[e]/o[e]-1.0); k[e]+=0.5*rts(e)+comm
        last=e
        for j in range(e,n):
            hd=j-e+1
            if exit_mode=="revert50":
                ex=(sig==1 and R[j]>=50) or (sig==-1 and R[j]<=50)
            elif exit_mode=="sma5":
                ex=(sig==1 and c[j]>ma5[j]) or (sig==-1 and c[j]<ma5[j])
            else:  # nday
                ex=False
            if ex or hd>=max_hold or j>=n-2:
                xe=min(j+1,n-1); g[xe]+=sig*(o[xe]/c[j]-1.0); k[xe]+=0.5*rts(xe)+comm
                k[xe]+=(xe-e)*swap/1e4; last=j; break
            else:
                g[j+1]+=sig*(c[j+1]/c[j]-1.0)
        i=last+1
    out=pd.DataFrame({"net":g-k},index=df.index); return out["net"]


def build(universe, weight="invvol", **kw):
    start,end=kw.pop("start","2022-01-01"),kw.pop("end","2026-06-05")
    tz=kw.pop("tz","EET")
    nets={s:sim(load_daily(s,tz).loc[:end],s,**kw) for s in universe}
    N=pd.DataFrame(nets).sort_index()
    if weight=="invvol":
        vol=N.rolling(90).std().shift(1); inv=1.0/vol.replace(0,np.nan); w=inv.div(inv.sum(axis=1),axis=0)
        gross=(w*N).sum(axis=1)
    else:
        gross=N.mean(axis=1)
    gross=gross.loc[start:end]
    net=vol_target(gross,0.01,63,4.0).loc[start:end].dropna()
    return net


def main():
    rows=[]
    cfgs=[
        ("two-sided full invvol EET",           dict(universe=FULL,weight="invvol",side="both",tz="EET")),
        ("two-sided full equalwt EET",          dict(universe=FULL,weight="equal", side="both",tz="EET")),
        ("two-sided full invvol UTC",           dict(universe=FULL,weight="invvol",side="both",tz="UTC")),
        ("LONG-only full invvol EET",           dict(universe=FULL,weight="invvol",side="long",tz="EET")),
        ("two-sided idx5 invvol EET",           dict(universe=IDX5,weight="invvol",side="both",tz="EET")),
        ("two-sided idx4 invvol EET",           dict(universe=IDX4,weight="invvol",side="both",tz="EET")),
        ("LONG idx5 +SMA200 invvol EET",        dict(universe=IDX5,weight="invvol",side="long",regime="sma200",tz="EET")),
        ("classic Connors(SMA200,sma5 exit,long) idx5 EET", dict(universe=IDX5,weight="invvol",side="long",regime="sma200",exit_mode="sma5",tz="EET")),
        ("two-sided idx5 invvol UTC",           dict(universe=IDX5,weight="invvol",side="both",tz="UTC")),
        ("two-sided idx5 invvol EET markup1 swap0", dict(universe=IDX5,weight="invvol",side="both",tz="EET",markup=1.0,swap=0.0)),
    ]
    for label,cfg in cfgs:
        for win in [("2022-01-01","2026-06-05"),("2018-01-01","2026-06-05")]:
            net=build(start=win[0],end=win[1],**cfg)
            m=metrics(net); ys=per_year_sharpe(net)
            allpos=all(v>0 for v in ys.values())
            rows.append((label,win[0][:4]+"-26",round(m["ann_sharpe"],2),round(m["excess_kurtosis"],1),
                         allpos,{k:round(v,1) for k,v in ys.items()}))
    print(f"{'variant':52s} {'win':8s} {'annSh':>6s} {'kurt':>5s} {'allyr+':>6s}  per-year")
    for r in rows:
        print(f"{r[0]:52s} {r[1]:8s} {r[2]:>6.2f} {r[3]:>5.1f} {str(r[4]):>6s}  {r[5]}")
    print("\nREPORT Sleeve A claim: ann Sharpe ~0.97, kurt ~14, POSITIVE EVERY YEAR")


if __name__=="__main__":
    main()
