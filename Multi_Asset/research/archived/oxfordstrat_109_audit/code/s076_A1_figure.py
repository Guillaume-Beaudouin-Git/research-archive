"""A.1 figure: correlation bars + rolling corr to deployed TSMOM + blend frontier."""
import numpy as np, pandas as pd, os
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab, rosshook as rh

DATA="/sessions/serene-elegant-faraday/mnt/data"; OUT="results"
RF=lab.RISK_FRAC; CLASS=lab.CLASS; MN,HK,TM=10,20,10
uni=lab.load_universe(); costs={t:lab.round_turn_cost_bps(t,df) for t,df in uni.items()}
cal=pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in uni.values()])))
DEPLOY=[t for t in uni if CLASS.get(t) in ('indices','commodities','crypto')]
def rh_daily(instrs):
    s=pd.Series(0.0,index=cal)
    for t in instrs:
        _,dm=rh.simulate_rosshook(uni[t],MN,HK,TM,cost_bps=costs[t],fill='next_open',side='both',daily=True)
        s=s.add(dm.reindex(cal).fillna(0))
    return s*RF
RHk=rh_daily(DEPLOY); RHk=RHk[RHk.index>=RHk[RHk!=0].index.min()]
def load_ser(p,col):
    d=pd.read_csv(os.path.join(DATA,p)); d.columns=['date']+list(d.columns[1:])
    d['date']=pd.to_datetime(d['date']); s=pd.Series(d[col].values,index=d['date']).astype(float)
    nz=s[s!=0]; return s[s.index>=nz.index.min()] if len(nz) else s
tsmom_dep=load_ser('ftmo_research/tsmom/chosen_returns.csv','0')
season=load_ser('skew_research/session_basic_trend/commodity_seasonality_oos.csv','0')
ctab=pd.read_csv(f"{OUT}/s076_A1_corr.csv")

fig,ax=plt.subplots(1,3,figsize=(15,4.6))
# Panel A: corr bars
c=ctab.sort_values('pearson'); cols=['#c0392b' if v>0.2 else ('#7f8c8d' if abs(v)<0.15 else '#e67e22') for v in c['pearson']]
ax[0].barh(c['sleeve'],c['pearson'],color=cols,edgecolor='k',lw=.6)
ax[0].axvline(0,color='k',lw=.8); ax[0].axvline(0.3,color='r',ls='--',lw=.8)
ax[0].set_title("A. Ross Hook correlation to existing sleeves\n(Pearson, max overlap)",fontsize=10,fontweight='bold')
ax[0].set_xlabel("correlation"); ax[0].tick_params(labelsize=8)
for i,(v,n) in enumerate(zip(c['pearson'],c['n'])): ax[0].text(v+(0.01 if v>=0 else -0.01),i,f"{v:+.2f}",va='center',ha='left' if v>=0 else 'right',fontsize=8)
# Panel B: rolling corr to deployed TSMOM
d=pd.concat([RHk,tsmom_dep],axis=1).dropna(); rc=d.iloc[:,0].rolling(252).corr(d.iloc[:,1]).dropna()
ax[1].plot(rc.index,rc.values,color='#c0392b',lw=1); ax[1].axhline(rc.median(),color='k',ls='--',lw=.8,label=f"median {rc.median():+.2f}")
ax[1].axhline(0,color='gray',lw=.6); ax[1].fill_between(rc.index,0,rc.values,where=rc.values>0,alpha=.12,color='#c0392b')
ax[1].set_title("B. Rolling 1y correlation to DEPLOYED TSMOM\n(momentum-family co-movement)",fontsize=10,fontweight='bold')
ax[1].set_ylabel("1y rolling corr"); ax[1].legend(fontsize=8); ax[1].tick_params(labelsize=8); ax[1].set_ylim(-0.4,0.8)
# Panel C: blend frontier
for k,lab_ in [('TSMOM_deployed','vs deployed TSMOM'),('CommoditySeason','vs commodity season')]:
    b=pd.read_csv(f"{OUT}/s076_A1_blend_{k}.csv"); ax[2].plot(b['w_rh'],b['sharpe'],marker='o',ms=3,label=lab_)
ax[2].set_title("C. Blended Sharpe vs Ross Hook weight\n(vol-normed 10%) — diversification gain",fontsize=10,fontweight='bold')
ax[2].set_xlabel("weight on Ross Hook"); ax[2].set_ylabel("blend ann. Sharpe"); ax[2].legend(fontsize=8); ax[2].grid(alpha=.25); ax[2].tick_params(labelsize=8)
plt.tight_layout(); plt.savefig(f"{OUT}/s076_A1_decorrelation.png",dpi=130,bbox_inches='tight'); print("saved",f"{OUT}/s076_A1_decorrelation.png")
