"""(b) New signal sources (vectorized, fast). event/news conditioning + intraday cross-sectional momentum."""
import pandas as pd, numpy as np

def event_test():
    d=pd.read_parquet("cache/cand_LO.parquet")["rmult"]      # date-indexed daily R-mult (long ORB)
    cal=pd.read_csv("/sessions/stoic-vigilant-meitner/mnt/data/panels/economic_calendar.csv")
    ev=set(pd.to_datetime(cal[cal["impact"]=="HIGH"]["date"]).dt.normalize())
    idx=pd.to_datetime(d.index); isev=idx.normalize().isin(ev)
    isnext=idx.normalize().isin({e+pd.Timedelta(days=1) for e in ev})
    tr=d!=0   # traded days
    print("=== Event conditioning on long ORB (daily R-mult) ===")
    print(f"  HIGH-event day : mean={d[isev&tr].mean():+.3f} n={int((isev&tr).sum())}")
    print(f"  non-event day  : mean={d[~isev&tr].mean():+.3f} n={int((~isev&tr).sum())}")
    print(f"  day AFTER event: mean={d[isnext&tr].mean():+.3f} n={int((isnext&tr).sum())}")

def xsec_test():
    p=pd.read_parquet("/sessions/stoic-vigilant-meitner/mnt/data/panels/m5_indices/m1_panel.parquet")
    p.index=pd.to_datetime(p.index)
    syms=["US100","US500","US30","US2000"]
    df=pd.DataFrame({s:p[(s,"close")] for s in syms}).dropna()
    tod=df.index.hour*60+df.index.minute
    sess=df[(tod>=16*60+30)&(tod<=22*60+55)].copy()
    sess["date"]=sess.index.date; tt=sess.index.hour*60+sess.index.minute
    opn=sess.groupby("date").first()
    mid=sess[tt<=17*60].groupby("date").last()
    end=sess.groupby("date").last()
    j=opn.index.intersection(mid.index).intersection(end.index)
    opn,mid,end=opn.loc[j,syms],mid.loc[j,syms],end.loc[j,syms]
    morning=(mid.values/opn.values-1); afternoon=(end.values/mid.values-1)
    cost=1e-4
    w=morning-morning.mean(1,keepdims=True); w=w/np.abs(w).sum(1,keepdims=True)
    mom=(w*afternoon).sum(1)-cost*np.abs(w).sum(1)
    rev=(-w*afternoon).sum(1)-cost*np.abs(w).sum(1)
    sh=lambda x: np.nanmean(x)/np.nanstd(x)*np.sqrt(252)
    print("\n=== Intraday cross-sectional US100/500/30/2000 (market-neutral, EOD) ===")
    print(f"  MOMENTUM long-winners: mean/day={np.nanmean(mom)*1e4:+.2f}bps Sharpe={sh(mom):+.2f} n={len(mom)}")
    print(f"  REVERSION long-losers: mean/day={np.nanmean(rev)*1e4:+.2f}bps Sharpe={sh(rev):+.2f}")
    # correlation to the long-beta ORB book
    s=pd.Series(mom,index=pd.to_datetime(j))
    bk=pd.read_parquet("cache/WIN_book.parquet")["rmult"]
    al=pd.concat([s.rename("xs"),bk.rename("bk")],axis=1).dropna()
    print(f"  corr(xsec, long-ORB book)={al.corr().iloc[0,1]:+.2f}  (decorrelated if ~0)")
    s.to_frame("rmult").to_parquet("cache/xsec_mom.parquet")

if __name__=="__main__":
    event_test(); xsec_test()
