"""Liquidite nette (Fed - TGA - RRP) -> actions. Spec gelee : ../PREREGISTRATION.md"""
import numpy as np, pandas as pd, statsmodels.api as sm
from pathlib import Path
R=Path("<HOME>/Desktop/Algo_claude"); B=Path(__file__).resolve().parents[1]

def ld(n):
    d=pd.read_csv(B/f"data/{n}.csv",na_values=["."]); d.columns=["date","v"]
    d["date"]=pd.to_datetime(d["date"])
    return pd.to_numeric(d.set_index("date")["v"],errors="coerce").dropna().sort_index()
def hac(x):
    x=np.asarray(x,float)
    if len(x)<3: return np.nan,np.nan
    f=sm.OLS(x,np.ones((len(x),1))).fit(cov_type="HAC",cov_kwds={"maxlags":6})
    return float(f.params[0]),float(f.tvalues[0])

walcl,tga,rrp=ld("WALCL")/1000.0,ld("WTREGEN"),ld("RRPONTSYD")
px=pd.read_csv(R/"data/deep_history_utc/US100_M1.csv",usecols=["timestamp_utc","close"])
px["t"]=pd.to_datetime(px["timestamp_utc"],format="%Y.%m.%d %H:%M:%S")
daily=px.set_index("t")["close"].resample("D").last().dropna()

idx=walcl.index
nl=(walcl - tga.reindex(idx).ffill() - rrp.reindex(idx).ffill()).dropna()
d_nl=nl.diff().dropna()

# point-in-time : donnee du mercredi -> entree cloture du JEUDI suivant
rows=[]
for dt,dv in d_nl.items():
    thu=dt+pd.Timedelta(days=1)
    e=daily.index[daily.index.searchsorted(thu)] if daily.index.searchsorted(thu)<len(daily) else None
    if e is None: continue
    p0=daily.loc[e]
    r={"date":dt,"d_nl":dv,"entry":e}
    for w in (1,4):
        k=daily.index.searchsorted(e+pd.Timedelta(weeks=w))
        if k>=len(daily): r[f"w{w}"]=np.nan; continue
        r[f"w{w}"]=np.sign(dv)*(daily.iloc[k]/p0-1.0)
    rows.append(r)
t=pd.DataFrame(rows).dropna(subset=["w1","w4"])
t=t[t.date>="2008-01-01"]
print(f"n = {len(t)} semaines | {t.date.min().date()} -> {t.date.max().date()}")
print(f"autocorrelation lag-1 de d_NL : {t.d_nl.autocorr(1):.3f}  =>  N_eff ~ "
      f"{len(t)*(1-abs(t.d_nl.autocorr(1)))/(1+abs(t.d_nl.autocorr(1))):.0f} (contre {len(t)} nominal)\n")

print("A. RESULTAT PRINCIPAL (cote = +signe(d_NL), la these)")
print(f"   {'horizon':<10}{'n':<7}{'rendement bps':<16}{'t_HAC'}")
for w in (1,4):
    m,tt=hac(t[f"w{w}"].values); print(f"   {w} sem.{'':<4}{len(t):<7}{m*1e4:+11.1f}     {tt:+7.2f}")

print("\nB. LE TEST DECISIF — stabilite par sous-periode")
print(f"   {'periode':<14}{'n':<7}{'1 sem bps':<14}{'t':<9}{'4 sem bps':<14}{'t'}")
for lab,a,b in [("2008-2019",None,"2019-12-31"),("2020-2021","2020-01-01","2021-12-31"),
                ("2022-2026","2022-01-01",None)]:
    s=t.copy()
    if a: s=s[s.date>=a]
    if b: s=s[s.date<=b]
    m1,t1=hac(s.w1.values); m4,t4=hac(s.w4.values)
    print(f"   {lab:<14}{len(s):<7}{m1*1e4:+11.1f}   {t1:+6.2f}   {m4*1e4:+11.1f}   {t4:+6.2f}")

print("\nC. REGRESSION SIGNEE — l'effet tient-il a la DIRECTION ?")
for w in (1,4):
    d=t.dropna(subset=[f"w{w}"]).copy()
    raw=np.sign(d.d_nl)*d[f"w{w}"]        # rendement brut non signe
    X=sm.add_constant(d["d_nl"].values)
    f=sm.OLS(raw.values*1e4,X).fit(cov_type="HAC",cov_kwds={"maxlags":6})
    print(f"   {w} sem. : pente {f.params[1]:+.4f} bps par milliard, t {f.tvalues[1]:+.2f}")
