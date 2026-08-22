"""FTMO 2-step challenge Monte-Carlo.
Account $10k. P1 target +10% (->$11k), P2 fresh $10k target +5% (->$10.5k).
DD: daily 5% (=$500 from day start; modeled as -5% equity-return bust),
    total 10% (static absolute floor $9,000).
Sizing is RISK-BASED: equity return per day = rho_t * Rmultiple, where Rmultiple is the
strategy's daily outcome in units of trade-risk (stop = -1R). This is how ORB is traded
under a daily-loss cap: risk a fixed fraction rho of equity per trade.
 - fixed:       rho_t = rho
 - floor_taper: rho_t = clip(c*(E-floor)/E, 0, rho_max)   (risk a fraction of distance-to-floor)
Bootstrap: stationary block bootstrap (Politis-Romano) preserves vol clustering / regime runs.
"""
import numpy as np, pandas as pd

def _boot(arr, N, T, block, rng):
    n=len(arr); R=np.empty((N,T)); pos=rng.integers(0,n,size=N); p=1.0/block
    for t in range(T):
        R[:,t]=arr[pos]
        newblk=rng.random(N)<p
        pos=np.where(newblk, rng.integers(0,n,size=N), (pos+1)%n)
    return R

def simulate(daily, N=15000, T=252, rho=0.02, mode="fixed", c=0.2, rho_max=0.045,
             daily_stop=0.045, block=10, seed=0, one_step=False):
    rng=np.random.default_rng(seed)
    arr=np.asarray(daily, float)
    R=_boot(arr,N,T,block,rng)
    floor=9000.0
    E=np.full(N,10000.0); phase=np.ones(N,int); alive=np.ones(N,bool); passed=np.zeros(N,bool)
    day_pass=np.full(N,10**9); day_p1=np.full(N,10**9)
    for t in range(T):
        rho_t=np.full(N,rho) if mode=="fixed" else np.clip(c*(E-floor)/E,0.0,rho_max)
        req=rho_t*R[:,t]
        req=np.maximum(req,-daily_stop)            # personal daily stop
        daily_bust=(req<=-0.05)&alive              # FTMO 5% daily
        Enew=E*(1.0+req)
        total_bust=(Enew<=floor)&alive             # FTMO 10% total (static floor)
        fail=daily_bust|total_bust
        alive=alive&(~fail)
        E=np.where(alive,Enew,E)
        adv1=alive&(phase==1)&(E>=11000.0)
        day_p1=np.where(adv1&(day_p1==10**9),t+1,day_p1)
        if one_step:
            newp=adv1&(~passed)
            day_pass=np.where(newp,t+1,day_pass)
            passed=passed|adv1; alive=alive&(~adv1)
        else:
            phase=np.where(adv1,2,phase); E=np.where(adv1,10000.0,E)
            win=alive&(phase==2)&(E>=10500.0)
            newp=win&(~passed)
            day_pass=np.where(newp,t+1,day_pass)
            passed=passed|win; alive=alive&(~win)
    busted=(~alive)&(~passed)
    # day_p1 = day +10% first reached (= a 1-step challenge pass). busted_p1 only counts pre-P1 busts.
    return dict(day_pass=day_pass, day_p1=day_p1, passed=passed, busted=busted, alive_timeout=alive)

def report(daily, label, sizings, N=15000, T=252, seed=0, horizons=(21,42,63,126,252)):
    out=[]
    for s in sizings:
        r=simulate(daily, N=N, T=T, seed=seed, **s)
        dp=r["day_pass"]
        row=dict(sizing=_name(s))
        for h in horizons: row[f"p<= {h}d"]=float(np.mean(dp<=h))
        row["bust%"]=float(r["busted"].mean())
        row["med_days|pass"]=float(np.median(dp[r["passed"]])) if r["passed"].any() else np.nan
        out.append(row)
    df=pd.DataFrame(out)
    print(f"\n===== {label} =====")
    with pd.option_context("display.width",200,"display.float_format",lambda v:f"{v:.3f}"):
        print(df.to_string(index=False))
    return df

def _name(s):
    if s.get("mode")=="floor_taper": return f"taper c={s.get('c')}"
    return f"fixed rho={s.get('rho')}"

if __name__=="__main__":
    import sys
    scen=sys.argv[1] if len(sys.argv)>1 else "DELAY_full"
    d=pd.read_parquet(f"cache/rmult_{scen}.parquet")["rmult"]
    sizings=[dict(mode="fixed",rho=r) for r in (0.01,0.015,0.02,0.025,0.03,0.04)] + \
            [dict(mode="floor_taper",c=c,rho_max=0.045) for c in (0.1,0.15,0.2,0.3)]
    report(d, scen, sizings)
