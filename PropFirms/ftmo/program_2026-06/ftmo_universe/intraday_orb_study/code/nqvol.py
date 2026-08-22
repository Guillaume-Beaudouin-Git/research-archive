"""ORB with real edge levers on NQ 2010-2026 (databento volume). Delay fills (realistic).
Levers: relative-volume confirmation, trend alignment, vol-regime gate, exit style, OR window.
Discipline: require robustness across years, not just 2021+."""
import pandas as pd, numpy as np
C="/sessions/stoic-vigilant-meitner/mnt/outputs/ftmo_intraday/cache/"
_df=None; _aux=None
def _load():
    global _df,_aux
    if _df is None:
        _df=pd.read_parquet(C+"NQ_rth_vol.parquet")
        _aux=pd.read_parquet(C+"NQ_daily_aux.parquet")  # index=date
        _aux["ma50"]=_aux["c"].rolling(50).mean().shift(1)   # shift: known at session open
        _aux["ma200"]=_aux["c"].rolling(200).mean().shift(1)
    return _df,_aux

def orbx(or_min=30, delay=True, exit="be", target=2.0, atr_mult=1.5,
         rvol_min=0.0, trend="none", rv20_lo=0.0, rv20_hi=9.9, cost_bps=1.0,
         long_only=False):
    df,aux=_load(); cf=cost_bps*1e-4
    pc=aux["pc"].to_dict(); rv=aux["rv20"].to_dict(); atrd=aux["atr14"].to_dict()
    ma50=aux["ma50"].to_dict(); ma200=aux["ma200"].to_dict()
    trades=[]
    for date,g in df.groupby("date",sort=True):
        r20=rv.get(date,np.nan)
        if not (rv20_lo<=r20<=rv20_hi): continue
        g=g.sort_values("rth_min")
        if len(g)<or_min+5: continue
        orb=g[g.rth_min<or_min]
        if len(orb)<or_min*0.6: continue
        orh,orl=orb.high.max(),orb.low.min()
        if orh<=orl: continue
        entry_ref=orb.close.iloc[-1]
        if (orh-orl)/entry_ref*1e4 < 8: continue
        post=g[g.rth_min>=or_min]
        if len(post)<3: continue
        H,L,Cl,O,RV=post.high.values,post.low.values,post.close.values,post.open.values,post.rvol.values
        pcl=pc.get(date,np.nan); atr=atrd.get(date,np.nan)
        side=0;entry=np.nan;ei=-1
        for i in range(len(post)):
            if H[i]>=orh:
                cand=1
            elif L[i]<=orl:
                cand=-1
            else:
                continue
            # volume confirmation on breakout bar
            if RV[i] < rvol_min:
                continue
            # trend alignment filter
            if trend=="pc" and not np.isnan(pcl):
                if cand==1 and entry_ref< pcl: continue
                if cand==-1 and entry_ref> pcl: continue
            if trend in ("ma50","ma200"):
                mref=(ma50 if trend=="ma50" else ma200).get(date,np.nan)
                if not np.isnan(mref):
                    if cand==1 and entry_ref< mref: continue
                    if cand==-1 and entry_ref> mref: continue
            if long_only and cand==-1: continue
            side=cand
            lvl=orh if cand==1 else orl
            if delay and i+1<len(post): entry=O[i+1];ei=i+1
            else: entry=lvl;ei=i
            break
        if side==0: continue
        stop=orl if side==1 else orh
        R=abs(entry-stop)
        if R<=0: continue
        be=False;exit_px=Cl[-1];reason="close"
        tgt=entry+side*target*R
        for j in range(ei,len(post)):
            hi,lo=H[j],L[j]
            if side==1:
                cs=entry if be else stop
                if lo<=cs: exit_px=cs;reason="stop";break
                if exit in("t2","t3") and hi>=tgt: exit_px=tgt;reason="tgt";break
                if exit=="atr" and be and lo<=max(cs,Cl[j-1]-atr_mult*atr/ max(1,len(post))): pass
                if exit=="be" and not be and hi>=entry+R: be=True
                if exit in("t2","t3") and not be and hi>=entry+R: be=True
            else:
                cs=entry if be else stop
                if hi>=cs: exit_px=cs;reason="stop";break
                if exit in("t2","t3") and lo<=tgt: exit_px=tgt;reason="tgt";break
                if exit=="be" and not be and lo<=entry-R: be=True
                if exit in("t2","t3") and not be and lo<=entry-R: be=True
        gross=side*(exit_px-entry)/entry
        trades.append((date,side,R/entry,gross,gross-cf))
    t=pd.DataFrame(trades,columns=["date","side","R_frac","gross","net"])
    return t

def stats(t,lab):
    if len(t)==0: print(f"{lab}: no trades"); return None
    t=t[t.R_frac>0].copy(); t["rmult"]=t.net/t.R_frac
    d=t.groupby("date")["rmult"].sum(); d.index=pd.to_datetime(d.index)
    sh=d.mean()/d.std()*np.sqrt(252)
    yr=d.groupby(d.index.year).mean(); pos=(yr>0).sum()
    L=t[t.side==1]; S=t[t.side==-1]
    print(f"{lab:42s} n={len(t):5d} meanR={t.net.mean()*1e4:+.2f}bps Sharpe={sh:+.2f} "
          f"posYrs={pos}/{len(yr)} L/S={L.net.mean()*1e4:+.1f}/{S.net.mean()*1e4:+.1f}")
    return d
