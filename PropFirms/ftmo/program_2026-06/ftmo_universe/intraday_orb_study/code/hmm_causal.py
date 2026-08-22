"""Causal HMM regime filter (no look-ahead): refit annually on expanding data,
manual forward-filtering for the test year (filtered P(state_t | obs<=t) with frozen params).
Gate / size the long ORB by the calm (low-vol) state probability. MC 1-step & 2-step."""
import pandas as pd, numpy as np, nq_ml as M, ftmo_sim as F
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp
import warnings; warnings.filterwarnings("ignore")

aux=pd.read_parquet("cache/NQ_daily_aux.parquet"); aux.index=pd.to_datetime(aux.index)
ret=np.log(aux["c"]/aux["c"].shift(1)); rv10=ret.rolling(10).std()
F0=pd.DataFrame({"ret":ret,"lrv":np.log(rv10)}).dropna()
# causal standardization (expanding, shifted)
mu=F0.expanding(250).mean().shift(1); sd=F0.expanding(250).std().shift(1)
Z=((F0-mu)/sd).dropna(); idx=Z.index; X=Z.values

def gauss_ll(x, means, vars_):
    # log emission per state for one obs vector x (diag cov)
    d=x[None,:]-means
    return -0.5*np.sum(d*d/vars_ + np.log(2*np.pi*vars_), axis=1)

years=idx.year
states_calm=np.full(len(idx), np.nan)   # filtered P(calm/low-vol state)
log_alpha=None; model=None; calm_idx=None; logT=None
for i,(dt,row) in enumerate(zip(idx, X)):
    Y=dt.year
    # (re)fit on data strictly before this year, once per year
    if model is None or dt.year!=getattr(model,"_yr",None):
        tr=Z[Z.index.year<Y]
        if len(tr)>300:
            m=GaussianHMM(n_components=3,covariance_type="diag",n_iter=150,random_state=0).fit(tr.values)
            m._yr=Y; model=m
            calm_idx=int(np.argmin(m.means_[:,1]))   # lowest lrv mean = calm state
            logT=np.log(m.transmat_+1e-12); log_pi=np.log(m.startprob_+1e-12)
            log_alpha=None
    if model is None: continue
    le=gauss_ll(row, model.means_, model.covars_[:, np.arange(model.n_features), np.arange(model.n_features)] if model.covars_.ndim==3 else model.covars_)
    if log_alpha is None:
        log_alpha=log_pi+le
    else:
        log_alpha=le+logsumexp(log_alpha[:,None]+logT, axis=0)
    p=np.exp(log_alpha-logsumexp(log_alpha))
    states_calm[i]=p[calm_idx]

calm=pd.Series(states_calm, index=idx, name="pcalm").dropna()

# join to ORB long up-break outcomes
S=M.build_samples(); S["d"]=S["date"].dt.normalize(); S=S.set_index("d")
S["pcalm"]=calm.reindex(S.index)
alldates=pd.to_datetime(sorted(pd.read_parquet("cache/NQ_rth_vol.parquet")["date"].unique()))
def ser(v):
    d=v.groupby(v.index).sum(); return d.reindex(alldates).fillna(0.0)
sh=lambda x: x.mean()/x.std()*np.sqrt(252)

base=ser(S["rmult"])
gate=ser(S["rmult"].where(S["pcalm"]<0.5, 0.0))          # skip when likely calm regime
size=ser(S["rmult"]*np.clip(1.5-S["pcalm"],0.4,1.5))     # size down as calm-prob rises
print("=== edge by causal-HMM calm prob ===")
J=S.dropna(subset=["pcalm"])
print("pcalm<0.5 (active):", J[J.pcalm<0.5].rmult.mean().round(3),"n",(J.pcalm<0.5).sum(),
      "| pcalm>=0.5 (calm):", J[J.pcalm>=0.5].rmult.mean().round(3),"n",(J.pcalm>=0.5).sum())
print(f"\n{'variant':14s} Sharpe | 1-STEP <2mo/<3mo/bust | 2-STEP <2mo")
for nm,d in [("baseline",base),("HMM gate",gate),("HMM size",size)]:
    best=None
    for rho in [0.035,0.04,0.045]:
        r=F.simulate(d,N=30000,T=252,rho=rho,daily_stop=0.099,seed=15,one_step=True)
        p=np.mean(r["day_pass"]<=42)
        if best is None or p>best[1]: best=(rho,p,np.mean(r["day_pass"]<=63),r["busted"].mean())
    r2=F.simulate(d,N=30000,T=252,rho=best[0],daily_stop=0.099,seed=15,one_step=False)
    print(f"{nm:14s} {sh(d):+.2f}  | {best[1]:.3f}/{best[2]:.3f}/{best[3]:.2f} (rho={best[0]}) | {np.mean(r2['day_pass']<=42):.3f}")
