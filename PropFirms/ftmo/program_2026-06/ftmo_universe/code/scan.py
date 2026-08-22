"""Systematic seasonality scan: mean return of each session window x weekday, fixed-time entries
(no fill artifact). Gate flags: |t|>2 full-sample, same sign OOS, coherent. Returns in bps."""
import pandas as pd, numpy as np, sys
WD=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def load(sym):
    d=pd.read_parquet(f"cache/{sym}.parquet", columns=["dt","close","tod"])
    d["date"]=pd.to_datetime(d["dt"]).dt.normalize(); d["wd"]=pd.to_datetime(d["dt"]).dt.weekday
    return d

def close_at(d, tod):
    s=d[d.tod==tod][["date","close","wd"]].drop_duplicates("date").set_index("date")
    return s

def window(d, t0, t1, lab, overnight=False):
    a=close_at(d,t0)
    if overnight:
        b=close_at(d,t1).copy(); b.index=b.index - pd.Timedelta(days=1)  # exit is NEXT day's t1
        b=b[["close"]].rename(columns={"close":"px1"})
    else:
        b=close_at(d,t1)[["close"]].rename(columns={"close":"px1"})
    m=a.join(b,how="inner"); m["r"]=(m["px1"]/m["close"]-1)*1e4
    m=m.dropna(subset=["r"]); m["yr"]=m.index.year
    rows=[]
    for wd in range(5):
        s=m[m.wd==wd]
        if len(s)<50: continue
        mu=s.r.mean(); t=mu/(s.r.std()/np.sqrt(len(s)))
        oos=s[s.yr>=2023].r.mean(); ins=s[s.yr<2023].r.mean()
        flag=""
        if abs(t)>2 and np.sign(oos)==np.sign(mu) and abs(oos)>1: flag=" <== PASSES gate"
        rows.append((lab,WD[wd],len(s),round(mu,2),round(t,2),round(ins,2),round(oos,2),flag))
    # also all-days
    mu=m.r.mean(); t=mu/(m.r.std()/np.sqrt(len(m)))
    oos=m[m.yr>=2023].r.mean(); ins=m[m.yr<2023].r.mean()
    f=" <== PASSES" if abs(t)>2 and np.sign(oos)==np.sign(mu) and abs(oos)>1 else ""
    rows.append((lab,"ALL",len(m),round(mu,2),round(t,2),round(ins,2),round(oos,2),f))
    return rows

if __name__=="__main__":
    sym=sys.argv[1]; d=load(sym)
    wins=eval(sys.argv[2])  # list of (t0,t1,lab,overnight)
    print(f"=== {sym}: mean window return (bps) by weekday | t-stat | IN/OOS ===")
    print(f"{'window':14s} {'wd':4s} {'n':>5s} {'mean':>7s} {'t':>6s} {'IN':>6s} {'OOS':>6s}")
    for w in wins:
        for r in window(d,*w):
            print(f"{r[0]:14s} {r[1]:4s} {r[2]:5d} {r[3]:7.2f} {r[4]:6.2f} {r[5]:6.2f} {r[6]:6.2f}{r[7]}")
        print()
