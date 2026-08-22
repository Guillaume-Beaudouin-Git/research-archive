import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_sim as F, nq
plt.rcParams.update({"figure.dpi":130,"font.size":10,"axes.grid":True,"grid.alpha":0.25})

D_full=pd.read_parquet("cache/rmult_DELAY_full.parquet")["rmult"]
D_lvl =pd.read_parquet("cache/rmult_LEVEL_full.parquet")["rmult"]
D_21  =pd.read_parquet("cache/rmult_DELAY_2021+.parquet")["rmult"]

# ---------- robustness: bootstrap block size ----------
print("=== Robustness: p(<=42d) & eventual by block size (fixed rho=0.025) ===")
for lab,d in [("DELAY_full",D_full),("DELAY_2021+",D_21)]:
    row=[]
    for b in [1,5,10,20,40]:
        r=F.simulate(d,N=20000,T=252,rho=0.025,block=b,seed=1)
        row.append((b,float(np.mean(r["day_pass"]<=42)),float(np.mean(r["day_pass"]<=252)),float(r["busted"].mean())))
    print(lab, " | ".join(f"blk{b}: 42d={p42:.2f} eventual={pe:.2f} bust={bu:.2f}" for b,p42,pe,bu in row))

# ---------- FIG 1: regime dependence (yearly meanR) ----------
trd=nq.orb_nq(delay=True,cost_bps=1.0); trd=trd[trd.R_frac>0]
trd["y"]=pd.to_datetime(trd.date).dt.year
yb=(trd.groupby("y")["net"].mean()*1e4)
fig,ax=plt.subplots(figsize=(9,3.6))
ax.bar(yb.index, yb.values, color=["#c0392b" if v<0 else "#27ae60" for v in yb.values])
ax.axhline(0,color="k",lw=0.8); ax.set_ylabel("mean net / trade (bps)")
ax.set_title("NQ Opening-Range Breakout — edge by year (realistic next-bar fill, 1bp cost)\n"
             "positive only in 2021–2024; negative through most of 2010–2020", fontsize=10)
ax.text(0.01,0.95,"full-sample edge ≈ 0  (Sharpe 0.11, t=0.4)",transform=ax.transAxes,va="top",fontsize=9,color="#555")
plt.tight_layout(); plt.savefig("figs/fig1_regime.png"); plt.close()

# ---------- FIG 2: p(pass <= horizon) curves ----------
H=np.arange(1,253)
fig,ax=plt.subplots(figsize=(8,4.4))
for lab,d,col in [("Honest baseline (16y, real fills)",D_full,"#2c3e50"),
                  ("Optimistic fill (16y, level)",D_lvl,"#2980b9"),
                  ("If 2021+ regime persists",D_21,"#27ae60")]:
    r=F.simulate(d,N=30000,T=252,rho=0.025,block=10,seed=2)
    dp=r["day_pass"]; curve=[np.mean(dp<=h) for h in H]
    ax.plot(H,curve,label=f"{lab}",lw=2,color=col)
ax.axvline(42,color="#e67e22",ls="--",lw=1.2); ax.text(44,0.04,"2 months",color="#e67e22")
ax.axhline(0.5,color="#c0392b",ls=":",lw=1.2); ax.text(150,0.515,"50% target",color="#c0392b")
ax.set_xlabel("trading days"); ax.set_ylabel("P(challenge passed by then)")
ax.set_title("FTMO 2-step pass probability vs time — single attempt, risk 2.5%/trade")
ax.legend(loc="lower right",fontsize=8.5); ax.set_ylim(0,0.8)
plt.tight_layout(); plt.savefig("figs/fig2_ppass.png"); plt.close()

# ---------- FIG 3: fast-vs-safe frontier (p<=42d vs bust%) ----------
sizings=[dict(mode="fixed",rho=r) for r in (0.01,0.015,0.02,0.025,0.03,0.04)]+\
        [dict(mode="floor_taper",c=c,rho_max=0.045) for c in (0.1,0.15,0.2,0.3)]
fig,ax=plt.subplots(figsize=(7.5,4.4))
for lab,d,col in [("Honest baseline",D_full,"#2c3e50"),("2021+ regime",D_21,"#27ae60")]:
    xs,ys,tags=[],[],[]
    for s in sizings:
        r=F.simulate(d,N=20000,T=252,seed=3,**s)
        xs.append(float(r["busted"].mean())); ys.append(float(np.mean(r["day_pass"]<=42)))
        tags.append(F._name(s).replace("fixed ","").replace("floor_taper ",""))
    ax.scatter(xs,ys,color=col,label=lab,s=28)
    for x,y,t in zip(xs,ys,tags): ax.annotate(t,(x,y),fontsize=6.5,color=col,xytext=(2,2),textcoords="offset points")
ax.axhline(0.5,color="#c0392b",ls=":",lw=1); ax.text(0.02,0.515,"50% target",color="#c0392b",fontsize=8)
ax.set_xlabel("P(bust the account)"); ax.set_ylabel("P(pass within 2 months)")
ax.set_title("The fundamental trade-off: speed vs survival (single attempt)\nno sizing reaches 50% in 2 months")
ax.legend(); plt.tight_layout(); plt.savefig("figs/fig3_tradeoff.png"); plt.close()

# ---------- FIG 4: multiple attempts ----------
n=np.arange(1,6)
fig,ax=plt.subplots(figsize=(7,4))
for p,lab,col in [(0.274,"honest, fast sizing (p=27%/try)","#2c3e50"),
                  (0.384,"2021+ regime, fast (p=38%/try)","#27ae60")]:
    ax.plot(n,1-(1-p)**n,"-o",label=lab,color=col)
ax.axhline(0.5,color="#c0392b",ls=":"); ax.text(1,0.52,"50%",color="#c0392b")
ax.set_xlabel("number of attempts (parallel or sequential)"); ax.set_ylabel("P(≥1 pass)")
ax.set_xticks(n); ax.set_title("The only honest route to >50% in <2 months:\nmultiple cheap attempts, 1−(1−p)ⁿ")
ax.legend(loc="lower right"); plt.tight_layout(); plt.savefig("figs/fig4_attempts.png"); plt.close()

# ---------- FIG 5: sample equity paths ----------
def sample_paths(d,rho,T=63,N=400,seed=7):
    rng=np.random.default_rng(seed); arr=d.values; n=len(arr)
    R=F._boot(arr,N,T,10,rng); E=np.full(N,10000.0); floor=9000.0
    phase=np.ones(N,int); alive=np.ones(N,bool); passed=np.zeros(N,bool); traj=np.full((N,T+1),np.nan); traj[:,0]=E
    for t in range(T):
        req=np.maximum(rho*R[:,t],-0.045); Enew=E*(1+req)
        fail=((req<=-0.05)|(Enew<=floor))&alive; alive&=~fail; E=np.where(alive,Enew,E)
        adv1=alive&(phase==1)&(E>=11000); phase=np.where(adv1,2,phase); E=np.where(adv1,10000.0,E)
        win=alive&(phase==2)&(E>=10500); passed|=win; alive&=~win
        traj[:,t+1]=np.where(alive|passed|(~alive),E,E)
        traj[~alive&~passed,t+1:]=np.nan  # stop drawing busted
    return traj,passed,alive
traj,passed,alive=sample_paths(D_full,0.025)
fig,ax=plt.subplots(figsize=(8,4.2))
for i in range(traj.shape[0]):
    c="#27ae60" if passed[i] else ("#c0392b" if not alive[i] else "#95a5a6")
    ax.plot(traj[i],color=c,lw=0.5,alpha=0.5)
ax.axhline(11000,color="#27ae60",ls="--",lw=1); ax.axhline(9000,color="#c0392b",ls="--",lw=1)
ax.text(1,11050,"P1 +10%",color="#27ae60",fontsize=8); ax.text(1,8850,"bust −10%",color="#c0392b",fontsize=8)
ax.set_xlabel("trading days"); ax.set_ylabel("equity ($)")
ax.set_title(f"400 sample paths — honest baseline, risk 2.5%/trade\n"
             f"green=passed both steps, red=busted, grey=still grinding (P1 phase shown)")
plt.tight_layout(); plt.savefig("figs/fig5_paths.png"); plt.close()
print("\nfigures written:", [f for f in __import__('os').listdir('figs')])
print("\n=== Multiple-attempts (P[>=1 pass] in <2 months) ===")
for p,lab in [(0.274,"honest fast"),(0.384,"2021+ fast")]:
    print(lab, {k:round(1-(1-p)**k,3) for k in (1,2,3,4)})
