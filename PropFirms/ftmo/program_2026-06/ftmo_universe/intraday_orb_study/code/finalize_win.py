import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_sim as F
plt.rcParams.update({"figure.dpi":130,"font.size":10,"axes.grid":True,"grid.alpha":0.25})
book=pd.read_parquet("cache/WIN_book.parquet")["rmult"]
nq=pd.read_parquet("cache/cand_LO.parquet")["rmult"]
H=np.arange(1,190)
def curve(d,rho,one_step,seed=3):
    r=F.simulate(d,N=50000,T=189,rho=rho,daily_stop=0.099,seed=seed,one_step=one_step)
    dp=r["day_pass"]; return np.array([np.mean(dp<=h) for h in H]), r["busted"].mean()

c_nq,b_nq=curve(nq,0.045,True)
c_bk,b_bk=curve(book,0.02,True)
c_bk2,_=curve(book,0.02,False)   # 2-step for contrast

# FIG: 1-step pass curves
fig,ax=plt.subplots(figsize=(8.2,4.5))
ax.plot(H,c_bk,color="#27ae60",lw=2.2,label=f"1-step, US100+GER40 book ρ=2% (bust {b_bk:.0%})")
ax.plot(H,c_nq,color="#2980b9",lw=2.2,label=f"1-step, Nasdaq full 16y ρ=4.5% (bust {b_nq:.0%})")
ax.plot(H,c_bk2,color="#7f8c8d",lw=1.8,ls="--",label="2-step (+10%/+5%) same book — fails")
ax.axvline(42,color="#e67e22",ls="--"); ax.text(43,0.04,"2 months",color="#e67e22",fontsize=9)
ax.axvline(63,color="#e67e22",ls=":",alpha=0.6); ax.text(64,0.04,"3 mo",color="#e67e22",fontsize=8)
ax.axhline(0.5,color="#c0392b",ls=":"); ax.text(120,0.515,"50% target",color="#c0392b",fontsize=9)
ax.set_xlabel("trading days"); ax.set_ylabel("P(challenge passed)"); ax.set_ylim(0,0.85)
ax.set_title("The configuration that PASSES: 1-step (+10%) challenge\nlong-only gap/trend ORB on Nasdaq, max sizing under the 5% daily cap")
ax.legend(loc="lower right",fontsize=8.5); plt.tight_layout(); plt.savefig("figs/figW1_pass.png"); plt.close()

# FIG: sample equity paths (book rho=0.02, 1-step)
rng=np.random.default_rng(5); arr=book.values; n=len(arr); N=500; T=63
R=F._boot(arr,N,T,10,rng); Eq=np.full(N,10000.0); traj=np.full((N,T+1),np.nan); traj[:,0]=Eq
alive=np.ones(N,bool); passed=np.zeros(N,bool)
for t in range(T):
    req=np.maximum(0.02*R[:,t],-0.049); En=Eq*(1+req)
    fail=((req<=-0.05)|(En<=9000))&alive; alive&=~fail; Eq=np.where(alive,En,Eq)
    win=alive&(Eq>=11000); passed|=win; alive&=~win
    traj[:,t+1]=Eq; traj[~alive&~passed,t+1:]=np.nan; traj[passed,t+1:]=np.where(np.isnan(traj[passed,t+1:]),Eq[passed,None],traj[passed,t+1:])
fig,ax=plt.subplots(figsize=(8.2,4.3))
for i in range(N):
    col="#27ae60" if passed[i] else ("#c0392b" if not alive[i] else "#bdc3c7")
    ax.plot(traj[i],color=col,lw=0.5,alpha=0.45)
ax.axhline(11000,color="#27ae60",ls="--",lw=1.2); ax.text(1,11050,"+10% target",color="#27ae60",fontsize=8)
ax.axhline(9000,color="#c0392b",ls="--",lw=1.2); ax.text(1,8830,"−10% bust",color="#c0392b",fontsize=8)
ax.set_xlabel("trading days"); ax.set_ylabel("equity ($)")
ax.set_title("500 sample paths — 1-step book, risk 2%/sleeve\ngreen = passed +10%, red = busted, grey = still trading at 3 months")
plt.tight_layout(); plt.savefig("figs/figW2_paths.png"); plt.close()
print("figs done; bust nq=%.2f book=%.2f"%(b_nq,b_bk))