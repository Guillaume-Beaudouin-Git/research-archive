import numpy as np, pandas as pd
import ftmo_lab as lab
from strat_s058_oops import run_point
from s060_deepdive import strat_daily, bh_daily, cal, CLASS
RISK=lab.RISK_FRAC

def daily_stats(sd):
    s=sd.dropna(); n=len(s); mu=s.mean(); sg=s.std()
    ann_ret=(1+s).prod()**(252/n)-1
    sharpe=mu/sg*np.sqrt(252) if sg>0 else np.nan
    dn=s[s<0].std(); sortino=mu/dn*np.sqrt(252) if dn>0 else np.nan
    eq=(1+s).cumprod(); dd=(eq/eq.cummax()-1); mdd=dd.min()
    calmar=ann_ret/abs(mdd) if mdd<0 else np.nan
    return dict(ann_ret=ann_ret, vol=sg*np.sqrt(252), sharpe=sharpe, sortino=sortino,
                calmar=calmar, maxdd=mdd, skew=s.skew(), kurt=s.kurt(), posdays=(s>0).mean())

def trade_stats(pool):
    r=pool['netR'].values; w=r[r>0]; l=r[r<0]
    return dict(n=len(r), win=(r>0).mean(), avgWin=w.mean(), avgLoss=l.mean(),
                payoff=w.mean()/abs(l.mean()), pf=w.sum()/abs(l.sum()), exp=r.mean(),
                skew=pd.Series(r).skew(), kurt=pd.Series(r).kurt(), best=r.max(), worst=r.min(),
                hold=pool['hold'].mean())

for fill in ['stop','next_open']:
    pool=run_point(3.0,10,side='long',fill=fill); inst=list(pool['instr'].unique())
    keep=[t for t in inst if CLASS.get(t) in ('indices','commodities','crypto')]
    print(f"\n===================== FILL = {fill} =====================")
    for label,p in [('ALL (4 classes)',pool),('DEPLOY (no FX)',pool[pool['instr'].isin(keep)])]:
        ts=trade_stats(p); sd,_=strat_daily(p); ds=daily_stats(sd)
        print(f"\n-- {label} --")
        print(f"  trades={ts['n']} win={ts['win']*100:.1f}% expR={ts['exp']:+.4f} payoff={ts['payoff']:.2f} PF={ts['pf']:.2f} avgHold={ts['hold']:.1f}d")
        print(f"  per-trade R: skew={ts['skew']:+.2f} kurt={ts['kurt']:+.1f} best={ts['best']:+.1f} worst={ts['worst']:+.1f}")
        print(f"  PORTF daily: annRet={ds['ann_ret']*100:+.1f}% vol={ds['vol']*100:.1f}% Sharpe={ds['sharpe']:.2f} Sortino={ds['sortino']:.2f} Calmar={ds['calmar']:.2f}")
        print(f"  PORTF risk : maxDD={ds['maxdd']*100:.1f}% dailySkew={ds['skew']:+.2f} dailyKurt={ds['kurt']:+.1f} posDays={ds['posdays']*100:.0f}%")
