"""FTMO 1-STEP challenge with the REAL rules (Feb 2026):
 - Profit target +10%
 - Max DAILY loss 3% of initial (recalculated each day) -> bust if day return <= -3%
 - Max loss 10% TRAILING end-of-day: floor = max(9000, highest_EOD_balance - 1000), never decreases
 - Best Day Rule: pass requires best single-day profit <= 50% of total profit (else keep trading)
Sizing rho per trade (a stop = -1R ~ -rho equity; rho<3% to respect daily; book=2 sleeves so 2*rho)."""
import numpy as np, pandas as pd
from ftmo_sim import _boot

def sim_1step(daily, N=25000, T=42, rho=0.02, block=10, seed=0, best_day_rule=True):
    rng=np.random.default_rng(seed); arr=np.asarray(daily,float)
    R=_boot(arr,N,T,block,rng)
    E=np.full(N,10000.0); eod_high=np.full(N,10000.0); floor=np.full(N,9000.0)
    maxday=np.zeros(N); alive=np.ones(N,bool); passed=np.zeros(N,bool); dpass=np.full(N,10**9)
    for t in range(T):
        req=rho*R[:,t]
        daily_bust=(req<=-0.03)&alive                 # 3% daily rule
        En=E*(1.0+req)
        trail_bust=(En<=floor)&alive                  # trailing 10% floor
        fail=daily_bust|trail_bust
        alive&=~fail
        daypnl=np.where(alive,En-E,0.0)
        E=np.where(alive,En,E)
        maxday=np.maximum(maxday,daypnl)
        eod_high=np.maximum(eod_high,E)
        floor=np.maximum(floor,eod_high-1000.0)       # trail up only
        total=E-10000.0
        target=E>=11000.0
        bd_ok=(maxday<=0.5*np.maximum(total,1e-9)) if best_day_rule else True
        win=alive&target&bd_ok&(~passed)
        dpass=np.where(win,t+1,dpass); passed|=win; alive&=~win
    return dict(dpass=dpass,passed=passed,bust=(~alive&~passed).mean())

if __name__=="__main__":
    series={"book US100+GER40 (2022+)":("cache/WIN_book.parquet",[0.008,0.010,0.012,0.014]),
            "Nasdaq full 16y":("cache/cand_LO.parquet",[0.015,0.020,0.025,0.027])}
    for name,(path,rhos) in series.items():
        d=pd.read_parquet(path)["rmult"]
        print(f"\n##### {name} — REAL 1-step rules #####")
        for rho in rhos:
            a=sim_1step(d,rho=rho,T=42,best_day_rule=True,seed=1)
            b=sim_1step(d,rho=rho,T=42,best_day_rule=False,seed=1)
            print(f"  rho={rho:.3f}: p(<2mo) with best-day-rule={np.mean(a['dpass']<=42):.3f} "
                  f"| WITHOUT best-day={np.mean(b['dpass']<=42):.3f} | bust={a['bust']:.2f}")
