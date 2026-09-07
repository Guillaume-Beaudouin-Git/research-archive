"""Segmentation Ranaldo, univers multi-paires. Spec gelee : PREREGISTRATION.md"""
import numpy as np, pandas as pd, statsmodels.api as sm
from zoneinfo import ZoneInfo
from pathlib import Path
R=Path("<HOME>/Desktop/Algo_claude"); ET=ZoneInfo("America/New_York")
# signe +1 : USD au denominateur (short la paire = long USD, spec d'origine)
# signe -1 : USD au numerateur (il faut inverser pour rester long USD)
PAIRS={"EURUSD":+1,"GBPUSD":+1,"AUDUSD":+1,"NZDUSD":+1,"USDJPY":-1,"USDCAD":-1,"USDCHF":-1}

def load(p):
    d=pd.read_csv(R/f"data/deep_history_utc/{p}_M1.csv",usecols=["timestamp_utc","close"])
    d["t"]=pd.to_datetime(d["timestamp_utc"],format="%Y.%m.%d %H:%M:%S")
    return d.set_index("t")["close"].sort_index()

def targets(dates,h):
    return pd.DatetimeIndex([pd.Timestamp(d.date(),tz=ET).replace(hour=h)
                             .tz_convert("UTC").tz_localize(None) for d in dates])

def asof(px,idx):
    return px.reindex(px.index.union(idx)).ffill().reindex(idx)

def hac(x):
    x=np.asarray(x,float)
    f=sm.OLS(x,np.ones((len(x),1))).fit(cov_type="HAC",cov_kwds={"maxlags":6})
    return float(f.params[0]),float(f.tvalues[0])

series={}
print(f"{'paire':<9}{'n jours':<10}{'brut bps/j':<13}{'t_HAC':<9}{'SR brut':<10}{'court':<9}{'long'}")
for p,sgn in PAIRS.items():
    px=load(p); px=px[px.index>="2007-01-01"]
    days=pd.DatetimeIndex(sorted(set(px.index.normalize())))
    days=days[days.dayofweek<5]
    p03,p11,p16=[asof(px,targets(days,h)).values for h in (3,11,16)]
    ok=~(np.isnan(p03)|np.isnan(p11)|np.isnan(p16))
    short_g=-np.log(p11[ok]/p03[ok])*sgn        # long USD 03->11
    long_g=+np.log(p16[ok]/p11[ok])*sgn         # short USD 11->16
    tot=short_g+long_g
    m,t=hac(tot); sr=tot.mean()/tot.std(ddof=1)*np.sqrt(252)
    ms,_=hac(short_g); ml,_=hac(long_g)
    series[p]=pd.Series(tot,index=days[ok])
    print(f"{p:<9}{ok.sum():<10}{m*1e4:+9.2f}    {t:+7.2f}  {sr:+8.2f}  {ms*1e4:+7.2f}  {ml*1e4:+7.2f}")

df=pd.DataFrame(series).dropna()
C=df.corr()
rho=(C.values[np.triu_indices(len(C),1)]).mean()
N=len(df.columns)
print(f"\nCORRELATION MOYENNE entre paires : {rho:+.3f}")
print(f"breadth effective N/(1+(N-1)rho) = {N/(1+(N-1)*rho):.2f}  (contre N={N} nominal)")
print("\nmatrice :"); print(C.round(2).to_string())
port=df.mean(axis=1)
m,t=hac(port.values); sr=port.mean()/port.std(ddof=1)*np.sqrt(252)
print(f"\nPORTEFEUILLE EQUIPONDERE ({N} paires, {len(port)} jours)")
print(f"  brut {m*1e4:+.2f} bps/jour, t_HAC {t:+.2f}, SR brut {sr:+.3f}")
print(f"  (mono-paire EURUSD de reference : SR brut 0.73)")
print(f"\nBUDGET DE COUT au SR agrege")
for lab,c in [("futures 0.40/jambe",0.8),("Eightcap 0.75/jambe",1.5),("FTMO 2.48/jambe",4.96)]:
    net=m*1e4-c; srn=sr*net/(m*1e4) if m>0 else np.nan
    print(f"  {lab:<24} cout {c:.2f} bps/j -> net {net:+.2f} bps, SR net {srn:+.3f}")
budget=m*1e4*(1-0.70/sr) if sr>0.70 else 0.0
print(f"\n  cout total max pour SR net > 0.70 : {budget:.2f} bps/jour = {budget/2:.2f} bps/jambe")
