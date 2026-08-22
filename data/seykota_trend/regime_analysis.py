"""Regime-by-regime chronology and drawdown episode timeline (cash variant, 2014-2026)."""
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
RES = HERE / "results"
eq = pd.read_csv(RES/"equity_extended_capped.csv", index_col=0, parse_dates=True)
tr = pd.read_csv(RES/"trades_extended_capped.csv", parse_dates=["entry_date","exit_date"])
e = eq["equity"]
r = e.pct_change().fillna(0)

def stats(seg_r, seg_e):
    if len(seg_r) < 2: return {}
    yrs = (seg_r.index[-1]-seg_r.index[0]).days/365.25
    nyr = len(seg_r)/yrs if yrs>0 else np.nan
    tot = seg_e.iloc[-1]/seg_e.iloc[0]-1
    cagr = (1+tot)**(1/yrs)-1 if yrs>0 else np.nan
    vol = seg_r.std(ddof=1)*np.sqrt(nyr)
    sharpe = seg_r.mean()/seg_r.std(ddof=1)*np.sqrt(nyr) if seg_r.std()>0 else np.nan
    dd = (seg_e/seg_e.cummax()-1).min()
    return dict(total_return=tot, cagr=cagr, ann_vol=vol, sharpe=sharpe, max_dd=dd)

# economically meaningful regimes
REGIMES = [
 ("Échantillon initial (pré-vidéo)","2014-09-17","2017-12-31","Marchés calmes, premier bull crypto 2017"),
 ("Choc volatilité 2018","2018-01-01","2018-12-31","Volmageddon fév., selloff actions Q4"),
 ("Reprise 2019","2019-01-01","2020-02-19","Détente Fed, rallye risk-on"),
 ("Krach COVID","2020-02-20","2020-04-07","Effondrement éclair puis rebond"),
 ("Reflation + bull crypto I","2020-04-08","2021-11-10","Liquidité massive, BTC 11k→69k"),
 ("Bear cross-asset / rate shock","2021-11-11","2022-12-31","Resserrement Fed, crypto winter, USD/énergie up"),
 ("Désinflation 2023","2023-01-01","2023-12-31","Reprise actions/tech, range or"),
 ("Range / chop 2024","2024-01-01","2024-12-31","Whipsaws multi-actifs, pire année"),
 ("Bull or/crypto/IA 2025-26","2025-01-01","2026-06-05","Rallye or, nouveaux ATH crypto/actions"),
]
rows=[]
for name,s,en,desc in REGIMES:
    m = (e.index>=s)&(e.index<=en)
    seg_e=e[m]; seg_r=r[m]
    st=stats(seg_r,seg_e)
    # trades closed in window
    tw = tr[(tr.exit_date>=s)&(tr.exit_date<=en)]
    st.update(start=s,end=en,regime=name,desc=desc,
              trades=len(tw), win_rate=(tw.pnl_net>0).mean() if len(tw) else np.nan,
              pnl=tw.pnl_net.sum())
    rows.append(st)
rg=pd.DataFrame(rows)[["regime","start","end","total_return","cagr","ann_vol","sharpe","max_dd","trades","win_rate","pnl","desc"]]
rg.to_csv(RES/"regime_table.csv",index=False)
pd.set_option("display.width",240); pd.set_option("display.float_format",lambda x:f"{x:.3f}")
print("===== REGIMES ====="); print(rg.drop(columns="desc").to_string(index=False))

# drawdown episodes >= 8%
dd = e/e.cummax()-1
under = dd<-1e-9
grp = (~under).cumsum()
eps=[]
for g,seg in dd[under].groupby(grp[under]):
    peak_date=e[:seg.index[0]].idxmax()
    trough_date=seg.idxmin(); depth=seg.min()
    # recovery = first date after trough where equity exceeds prior peak
    peak_val=e.loc[peak_date]
    after=e[e.index>trough_date]
    rec=after[after>=peak_val]
    rec_date=rec.index[0] if len(rec) else None
    eps.append(dict(peak=peak_date.date(),trough=trough_date.date(),
                    recovery=rec_date.date() if rec_date else "en cours",
                    depth=depth,
                    drawdown_days=(trough_date-peak_date).days,
                    recovery_days=((rec_date-trough_date).days if rec_date else np.nan)))
ep=pd.DataFrame(eps)
ep=ep[ep.depth<=-0.08].sort_values("depth")
ep.to_csv(RES/"drawdown_episodes.csv",index=False)
print("\n===== DRAWDOWN EPISODES (>=8%) =====")
print(ep.to_string(index=False))

# yearly with both variants + benchmark spx
spx=pd.read_parquet(HERE/"daily/US500.parquet")["close"]
spx_y=spx.resample("YE").last().pct_change()
ey=e.resample("YE").last()
y0=e.iloc[0]
yr=ey.pct_change(); yr.iloc[0]=ey.iloc[0]/y0-1
yt=pd.DataFrame({"strategy":yr.round(4)})
yt.index=yt.index.year
print("\n===== YEARLY (cash) =====")
print(yt.to_string())
