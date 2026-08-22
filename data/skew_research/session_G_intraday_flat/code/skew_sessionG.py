"""session_G — intraday-FLAT candidates (zero swap; spread decides, L33-bis). NQ=US100, true UTC, RTH minute bars.
Conservative spread = 3 bps RT (FLAGGED). Gates: delay-1 (L26), two-sided (L25), OOS, N (L12), DSR (N_tests~150 -> need |t|>~3)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
NQ="/sessions/stoic-vigilant-meitner/mnt/outputs/ftmo_intraday/cache/NQ_rth.parquet"
d=pd.read_parquet(NQ)
mins=[0,5,30,270,285,300,360,361,389]
piv=d[d.rth_min.isin(mins)].pivot_table(index="date",columns="rth_min",values="close")
piv.index=pd.to_datetime(piv.index); piv["pc"]=piv[389].shift(1)
cal=pd.read_csv("/sessions/stoic-vigilant-meitner/mnt/data/panels/economic_calendar.csv")
cal["dt"]=pd.to_datetime(cal["datetime_utc"]); cd=lambda ev:set(pd.to_datetime(cal[cal.event==ev]["date"]).dt.normalize())
SP=3e-4  # conservative round-trip spread (FLAGGED): if edge dies here, dead
def rep(x,lab,ann=None):
    x=pd.Series(x).dropna()
    if len(x)<10: print(f"  {lab:46s} n={len(x)} insuff"); return
    m=x.mean()*1e4; t=m/(x.std()*1e4/np.sqrt(len(x)))
    extra=f" Sharpe={x.mean()/x.std()*np.sqrt(ann):+.2f}" if ann else ""
    print(f"  {lab:46s} n={len(x):4d} mean={m:+.1f}bps t={t:+.2f}{extra} skew={skw(x):+.2f} hit={(x>0).mean():.2f}")

print("=== SG-1 Post-release INTRADAY continuation (flat close) ===")
print("-- FOMC (14:00 ET = rth_min270, intraday): react 270->285, trade 285->close (delay built in) --")
f=piv[piv.index.normalize().isin(cd("FOMC"))].copy()
react=f[285]/f[270]-1; cont=f[389]/f[285]-1; pnl=np.sign(react)*cont
rep(pnl,"FOMC continuation RAW (gross)")
rep(pnl-SP,"FOMC continuation NET 3bps")
rep(cont[react>0],"  two-sided: continuation | react UP (long)")
rep(-cont[react<0],"  two-sided: continuation | react DOWN (short)")
rep((np.sign(react)*(f[389]/f[300]-1))-SP,"  delay sensitivity: enter 300 (30min) NET")
for lab,a,b in [("2020-2022",2020,2022),("2023-2026",2023,2026)]:
    s=pnl[(f.index.year>=a)&(f.index.year<=b)]-SP; rep(s,f"  OOS {lab} NET")
print("-- CPI/NFP (08:30 ET pre-RTH): gap=open/pc, trade open+5min->close (delay-1) --")
g=piv[piv.index.normalize().isin(cd("CPI")|cd("NFP"))].copy()
gap=g[0]/g["pc"]-1; gcont=g[389]/g[5]-1; gp=np.sign(gap)*gcont
rep(gp,"CPI/NFP gap-continuation RAW")
rep(gp-SP,"CPI/NFP gap-continuation NET 3bps")
rep(gcont[gap>0],"  two-sided: cont | gap UP"); rep(-gcont[gap<0],"  two-sided: cont | gap DOWN")
rep(np.sign(gap)*(g[389]/g[5]-1)*-1 - SP,"  REVERSAL variant (fade gap) NET")

print("\n=== SG-2 Gao time-of-day momentum (re-run propre; cf session_3 C3 t=-0.13, intraday-mom-176 mort) ===")
f30=piv[30]/piv[0]-1; l30=piv[389]/piv[360]-1; gao=np.sign(f30)*l30
rep(gao,"sign(first30)*last30 RAW", ann=252)
rep(gao-SP,"sign(first30)*last30 NET 3bps", ann=252)
rep(l30[f30>0],"  two-sided: last30 | first30 UP (long)")
rep(-l30[f30<0],"  two-sided: last30 | first30 DOWN (short)")
yrs=piv.index.year
for lab,a,b in [("pre-2015",2010,2014),("2015-2019",2015,2019),("2020-2026",2020,2026)]:
    s=(gao-SP)[(yrs>=a)&(yrs<=b)]; rep(s,f"  OOS {lab} NET")
print(f"\nDSR context: cumulative N_tests ~O(150) -> multiple-testing bar ~|t|>3 (Bonferroni z). Judge against that.")
