"""Walk-forward ML filter for the long ORB on NQ 2010-2026.
Decision: given an up-breakout day, should we TAKE the long? Features known at OR-end (no look-ahead).
Strict expanding walk-forward: train on all years < Y, predict year Y. OOS only."""
import pandas as pd, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
C="/sessions/stoic-vigilant-meitner/mnt/outputs/ftmo_intraday/cache/"

def build_samples(or_min=30, cost_bps=1.0, trail_be=True):
    df=pd.read_parquet(C+"NQ_rth_vol.parquet")
    aux=pd.read_parquet(C+"NQ_daily_aux.parquet")
    pc=aux["pc"].to_dict(); rv=aux["rv20"].shift(1).to_dict()  # rv20 known only at PRIOR close
    c=aux["c"]
    ret1=(c.shift(1)/c.shift(2)-1).to_dict()   # prior-day return (known at open)
    ret5=(c.shift(1)/c.shift(6)-1).to_dict()   # 5d return through prior close
    ma50=aux["c"].rolling(50).mean().shift(1).to_dict()
    cf=cost_bps*1e-4; rows=[]
    for date,g in df.groupby("date",sort=True):
        g=g.sort_values("rth_min")
        if len(g)<or_min+5: continue
        orb=g[g.rth_min<or_min]
        if len(orb)<or_min*0.6: continue
        orh,orl=orb.high.max(),orb.low.min()
        if orh<=orl: continue
        dop=g.open.iloc[0]; orc=orb.close.iloc[-1]
        if (orh-orl)/orc*1e4<8: continue
        post=g[g.rth_min>=or_min]
        if len(post)<3: continue
        H,L,Cl,O=post.high.values,post.low.values,post.close.values,post.open.values
        # first up-break only (long)
        ei=-1; entry=np.nan
        for i in range(len(post)):
            if H[i]>=orh:
                if i+1<len(post): entry=O[i+1]; ei=i+1
                else: entry=orh; ei=i
                break
        if ei<0: continue
        stop=orl; R=entry-stop
        if R<=0: continue
        be=False; exit_px=Cl[-1]
        for j in range(ei,len(post)):
            cs=entry if be else stop
            if L[j]<=cs: exit_px=cs; break
            if trail_be and not be and H[j]>=entry+R: be=True
        net=(exit_px-entry)/entry-cf
        pcl=pc.get(date,np.nan); m50=ma50.get(date,np.nan)
        feats=dict(
            gap=(dop/pcl-1) if pcl else 0.0,
            or_ret=orc/dop-1.0,
            or_width=(orh-orl)/orc,
            rv20=rv.get(date,np.nan),
            ret1=ret1.get(date,np.nan), ret5=ret5.get(date,np.nan),
            above_ma50=float(orc>m50) if not np.isnan(m50) else 0.5,
            dist_ma50=(orc/m50-1) if (m50 and not np.isnan(m50)) else 0.0,
            dow=pd.Timestamp(date).dayofweek,
            ervol=float(orb.rvol.mean()),
        )
        feats["date"]=pd.Timestamp(date); feats["net"]=net; feats["R_frac"]=R/entry; feats["rmult"]=net/(R/entry)
        rows.append(feats)
    return pd.DataFrame(rows)

def walkforward(S, thr_mode="proba", start_year=2014):
    S=S.sort_values("date").reset_index(drop=True)
    S["y"]=S["date"].dt.year
    feats=["gap","or_ret","or_width","rv20","ret1","ret5","above_ma50","dist_ma50","dow","ervol"]
    S=S.dropna(subset=feats)
    out=[]
    for Y in range(start_year, 2027):
        tr=S[S.y<Y]; te=S[S.y==Y]
        if len(tr)<300 or len(te)==0: continue
        Xtr,ytr=tr[feats].values,(tr["net"]>0).astype(int).values
        clf=HistGradientBoostingClassifier(max_depth=3,max_iter=150,learning_rate=0.05,
                                           min_samples_leaf=40,l2_regularization=1.0,random_state=0)
        clf.fit(Xtr,ytr)
        p=clf.predict_proba(te[feats].values)[:,1]
        thr=np.median(clf.predict_proba(Xtr[:, :])[:,1])  # take top-half by train median
        sel=te.copy(); sel["p"]=p; sel=sel[sel["p"]>=thr]
        out.append(sel)
    return pd.concat(out) if out else S.iloc[:0]
