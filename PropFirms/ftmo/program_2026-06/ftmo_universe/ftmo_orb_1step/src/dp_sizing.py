"""Optimal bet-sizing via dynamic programming + HONEST validation in block-bootstrap.
DP (IID) yields the optimal state-dependent policy rho*(equity, days_left, phase).
We then VALIDATE that policy in the clustering-aware stationary block bootstrap (apples-to-apples
vs fixed sizing) -> the honest p(pass) of optimal sizing."""
import numpy as np, pandas as pd
from ftmo_sim import _boot

RHOS=np.round(np.arange(0.0,0.0451,0.0025),4)
def Rdist(series,bins=70):
    x=np.asarray(series,float); h,e=np.histogram(x,bins=bins)
    c=0.5*(e[:-1]+e[1:]); p=h/h.sum(); m=p>0; return c[m],p[m]

def solve(series,T=42,two_step=True,floor=9000.,p1=11000.,p2=10500.,step=10.0):
    rc,pp=Rdist(series)
    E2=np.arange(floor,p2+step,step); V2=np.zeros((T+1,len(E2))); P2=np.zeros((T+1,len(E2)))
    V2[:,E2>=p2]=1.0
    for d in range(1,T+1):
        prev=V2[d-1]; best=np.full(len(E2),-1.0); bestr=np.zeros(len(E2))
        for rho in RHOS:
            mult=1+rho*rc; ok=(rho*rc)>-0.05
            Ep=np.outer(E2,mult); vn=np.interp(Ep,E2,prev,left=0.0,right=1.0)
            vn[Ep<=floor]=0.0; vn[Ep>=p2]=1.0; vn[:,~ok]=0.0
            ev=vn@pp; upd=ev>best; best=np.where(upd,ev,best); bestr=np.where(upd,rho,bestr)
        best[E2>=p2]=1.0; best[E2<=floor]=0.0
        V2[d]=best; P2[d]=bestr
    if not two_step:
        E1=np.arange(floor,p1+step,step); V=np.zeros((T+1,len(E1))); P=np.zeros((T+1,len(E1))); V[:,E1>=p1]=1.0
        for d in range(1,T+1):
            prev=V[d-1]; best=np.full(len(E1),-1.0); bestr=np.zeros(len(E1))
            for rho in RHOS:
                mult=1+rho*rc; ok=(rho*rc)>-0.05
                Ep=np.outer(E1,mult); vn=np.interp(Ep,E1,prev,left=0.0,right=1.0)
                vn[Ep<=floor]=0.0; vn[Ep>=p1]=1.0; vn[:,~ok]=0.0
                ev=vn@pp; upd=ev>best; best=np.where(upd,ev,best); bestr=np.where(upd,rho,bestr)
            best[E1>=p1]=1.0; best[E1<=floor]=0.0; V[d]=best; P[d]=bestr
        return float(np.interp(10000.,E1,V[T])),dict(E1=E1,P1=P,E2=None,P2=None,one=True)
    E1=np.arange(floor,p1+step,step); V1=np.zeros((T+1,len(E1))); P1a=np.zeros((T+1,len(E1)))
    for d in range(1,T+1):
        prev=V1[d-1]; v2_next=float(np.interp(10000.,E2,V2[d-1]))
        best=np.full(len(E1),-1.0); bestr=np.zeros(len(E1))
        for rho in RHOS:
            mult=1+rho*rc; ok=(rho*rc)>-0.05
            Ep=np.outer(E1,mult); vn=np.interp(Ep,E1,prev,left=0.0,right=v2_next)
            vn[Ep>=p1]=v2_next; vn[Ep<=floor]=0.0; vn[:,~ok]=0.0
            ev=vn@pp; upd=ev>best; best=np.where(upd,ev,best); bestr=np.where(upd,rho,bestr)
        best[E1<=floor]=0.0; V1[d]=best; P1a[d]=bestr
    return float(np.interp(10000.,E1,V1[T])),dict(E1=E1,P1=P1a,E2=E2,P2=P2,one=False)

def validate(series,pol,T=42,N=40000,block=10,seed=3):
    """Run the DP-optimal policy through the stationary block bootstrap (clustering-aware)."""
    rng=np.random.default_rng(seed); arr=np.asarray(series,float)
    R=_boot(arr,N,T,block,rng); floor=9000.
    E=np.full(N,10000.); phase=np.ones(N,int); alive=np.ones(N,bool); passed=np.zeros(N,bool)
    dpass=np.full(N,10**9)
    E1=pol["E1"]; P1=pol["P1"]; one=pol["one"]; E2=pol["E2"]; P2=pol["P2"]
    for t in range(T):
        d=T-t
        rho=np.empty(N)
        m1=alive&(phase==1); rho[m1]=np.interp(E[m1],E1,P1[d])
        if not one:
            m2=alive&(phase==2); rho[m2]=np.interp(E[m2],E2,P2[d])
        rho[~alive]=0.0
        req=rho*R[:,t]
        bust=(req<=-0.05)&alive
        En=E*(1+req); bust|=(En<=floor)&alive
        alive&=~bust; E=np.where(alive,En,E)
        if one:
            win=alive&(E>=11000.); newp=win&~passed; dpass=np.where(newp,t+1,dpass); passed|=win; alive&=~win
        else:
            adv=alive&(phase==1)&(E>=11000.); phase=np.where(adv,2,phase); E=np.where(adv,10000.,E)
            win=alive&(phase==2)&(E>=10500.); newp=win&~passed; dpass=np.where(newp,t+1,dpass); passed|=win; alive&=~win
    return dict(p=passed.mean(),bust=(~alive&~passed).mean(),dpass=dpass)

if __name__=="__main__":
    import ftmo_sim as F
    series={"book US100+GER40 (2022+)":pd.read_parquet("cache/WIN_book.parquet")["rmult"],
            "NQ long-only (full 16y)":pd.read_parquet("cache/cand_LO.parquet")["rmult"]}
    for name,s in series.items():
        print(f"\n##### {name} #####")
        for two,lab in [(False,"1-STEP"),(True,"2-STEP")]:
            pdp,pol=solve(s,T=42,two_step=two)
            v=validate(s,pol,T=42)
            # fixed best in SAME block bootstrap
            fb=0
            for rho in [0.02,0.03,0.04,0.045]:
                r=F.simulate(s,N=40000,T=42,rho=rho,daily_stop=0.099,seed=3,one_step=not two)
                fb=max(fb,np.mean(r["day_pass"]<=42))
            print(f"  {lab} <2mo: DP(IID)={pdp:.3f} | DP-policy VALIDATED(block-boot)={v['p']:.3f} (bust {v['bust']:.2f}) | best FIXED={fb:.3f}")
