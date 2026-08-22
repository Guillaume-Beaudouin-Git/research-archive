"""ORB on NQ databento RTH (2010-2026), the long-history Nasdaq proxy for US100 CFD.
Cost applied as a fixed round-trip bps (US100 CFD ~1bp). is_rth defines the cash session."""
import pandas as pd, numpy as np
CACHE="/sessions/stoic-vigilant-meitner/mnt/outputs/ftmo_intraday/cache/"

def load_nq():
    return pd.read_parquet(CACHE+"NQ_rth.parquet")

def orb_nq(or_min=30, min_width_bps=10.0, trail_be=True, delay=False, cost_bps=1.0):
    df=load_nq()
    cf=cost_bps*1e-4
    trades=[]
    for date,g in df.groupby("date",sort=True):
        g=g.sort_values("rth_min")
        if len(g)<or_min+5: continue
        orb=g[g.rth_min<or_min]
        if len(orb)<or_min*0.6: continue
        orh,orl=orb.high.max(),orb.low.min()
        if orh<=orl: continue
        entry_ref=orb.close.iloc[-1]
        if (orh-orl)/entry_ref*1e4 < min_width_bps: continue
        post=g[g.rth_min>=or_min]
        if len(post)<3: continue
        H,L,C,O=post.high.values,post.low.values,post.close.values,post.open.values
        side=0;entry=np.nan;ei=-1
        for i in range(len(post)):
            if H[i]>=orh:
                side=1
                if delay and i+1<len(post): entry=O[i+1];ei=i+1
                else: entry=orh;ei=i
                break
            if L[i]<=orl:
                side=-1
                if delay and i+1<len(post): entry=O[i+1];ei=i+1
                else: entry=orl;ei=i
                break
        if side==0: continue
        stop=orl if side==1 else orh
        R=abs(entry-stop)
        if R<=0: continue
        be=False;exit_px=C[-1];reason="close"
        for j in range(ei,len(post)):
            if side==1:
                cs=entry if be else stop
                if L[j]<=cs: exit_px=cs;reason=("be" if be else "stop");break
                if trail_be and not be and H[j]>=entry+R: be=True
            else:
                cs=entry if be else stop
                if H[j]>=cs: exit_px=cs;reason=("be" if be else "stop");break
                if trail_be and not be and L[j]<=entry-R: be=True
        gross=side*(exit_px-entry)/entry
        trades.append((date,side,entry,exit_px,R/entry,gross,gross-cf,reason))
    return pd.DataFrame(trades,columns=["date","side","entry","exit","R_frac","gross","net","reason"])

def daily(tr):
    d=tr.groupby("date")["net"].sum(); d.index=pd.to_datetime(d.index); return d.sort_index()
