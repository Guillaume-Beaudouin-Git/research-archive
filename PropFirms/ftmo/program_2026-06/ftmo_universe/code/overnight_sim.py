"""The winner: overnight Nasdaq drift, midweek nights, net of swap. FTMO 2-step p(pass).
Hold = buy RTH close, sell next RTH open, on Mon-night & Tue-night (open-day Tue & Wed).
Net per night = gross overnight - 3.08 bps swap (1x; 3x is Friday, not held).
No intraday stop on an overnight hold -> the gap is the daily-DD risk (no cap)."""
import pandas as pd, numpy as np, ftmo_sim as F
from scipy.stats import skew as skw
d=pd.read_parquet("cache/NQ_rth.parquet")
g=d.groupby("date"); o=g["open"].first(); c=g["close"].last()
df=pd.DataFrame({"o":o,"c":c}); df.index=pd.to_datetime(df.index)
df["ov"]=df["o"]/df["c"].shift(1)-1          # overnight return (prev close -> open)
df["wd"]=df.index.weekday
SWAP=3.08e-4
mid=df[df.wd.isin([1,2])].copy()             # open-day Tue,Wed  = Mon-night & Tue-night holds
mid["net"]=mid["ov"]-SWAP
alln=df[df.wd.isin([0,1,2,3])].copy(); alln["net"]=alln["ov"]-SWAP  # Mon-Thu open (skip Fri 3x)

def stats(s,lab):
    s=s.dropna(); mu=s.mean()*1e4; t=mu/(s.std()/np.sqrt(len(s))*1e4)
    print(f"{lab}: mean_net={mu:+.2f}bps t={t:+.2f} std={s.std()*1e4:.0f}bps n={len(s)} skew={skw(s):+.2f} worst={s.min()*100:.1f}% best={s.max()*100:.1f}%")
stats(mid["net"],"midweek (Tue+Wed open)")
stats(alln["net"],"Mon-Thu open")

# build all-trading-days series (0 on non-held days) for the time budget
cal=df.index
ser_mid=pd.Series(0.0,index=cal); ser_mid.loc[mid.index]=mid["net"].values
ser_mid=ser_mid.dropna()
print("\n=== FTMO 2-step MC, overnight midweek, net of swap (rho = leverage; gap=daily risk) ===")
for rho in [1.5,2.0,3.0,4.0]:
    r=F.simulate(ser_mid,N=30000,T=252,rho=rho,daily_stop=0.99,seed=7,one_step=False)
    dp=r["day_pass"]
    print(f"  lev={rho}: p(<2mo)={np.mean(dp<=42):.3f} p(<3mo)={np.mean(dp<=63):.3f} eventual={np.mean(dp<=252):.3f} bust={r['busted'].mean():.3f} med|pass={np.median(dp[r['passed']]) if r['passed'].any() else np.nan:.0f}")
# how often does a single night breach -5% at each lev (daily-DD tail)
print("\n  worst-night daily-DD: at lev L, a night of -x% loses L*x%; -5% breach if night < -5/L %")
for rho in [1.5,2.0,3.0,4.0]:
    breach=(mid["net"]*rho<=-0.05).mean(); print(f"   lev={rho}: P(single-night breach 5% daily)={breach:.3%}")
