import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_sim as F
plt.rcParams.update({"figure.dpi":130,"font.size":10,"axes.grid":True,"grid.alpha":0.25})
panel=pd.read_parquet("cache/sleeve_panel.parquet"); ann=np.sqrt(252)
POS=["US100_NY","US500_NY","GER40_cash","XAU_NY"]
sub=panel[POS].loc[panel.index>="2022-01-01"].fillna(0.0)
mu=sub.mean().values; cov=sub.cov().values
# long-only tangency (clip negatives, renormalize)
w=np.linalg.solve(cov,mu); w=np.clip(w,0,None); w=w/w.sum()
tang=(sub*w).sum(axis=1)
eqr=sub.sum(axis=1)
def sh(s): return s.mean()/s.std()*ann
print("tangency weights:",dict(zip(POS,np.round(w,2))))
print(f"single US100 Sharpe={sh(panel['US100_NY'].loc[panel.index>='2022-01-01'].dropna()):.2f}")
print(f"equal-risk book Sharpe={sh(eqr):.2f}   tangency book Sharpe={sh(tang):.2f}")
print(f"uncorrelated upper bound sqrt(sum SR^2)={np.sqrt(sum((mu/sub.std().values)**2)*252):.2f}")
tang.to_frame("rmult").to_parquet("cache/book_tangency.parquet")

# MC curves
us=pd.read_parquet("cache/rmult_DELAY_2021+.parquet")["rmult"]
def curve(d,rho,T=252,N=40000,seed=11):
    r=F.simulate(d,N=N,T=T,rho=rho,block=10,seed=seed); dp=r["day_pass"]
    return np.array([np.mean(dp<=h) for h in range(1,T+1)]), r["busted"].mean()
# pick sizing giving best p<=42d for each
def best(d,grid,T=252):
    best=None
    for rho in grid:
        r=F.simulate(d,N=30000,T=T,rho=rho,seed=12); p42=np.mean(r["day_pass"]<=42)
        if best is None or p42>best[1]: best=(rho,p42,r["busted"].mean(),np.mean(r["day_pass"]<=252))
    return best
bt=best(tang,[0.006,0.008,0.01,0.0125,0.015]); bu=best(us,[0.02,0.025,0.03,0.04])
print("tangency best:",bt,"  US100 best:",bu)
ct,_=curve(tang,bt[0]); cu,_=curve(us,bu[0])

# FIG B1: correlation heatmap
allc=["US100_NY","US500_NY","GER40_cash","XAU_London","XAU_NY","EUR_London","EUR_NY"]
C=panel[allc].loc[panel.index>="2022-01-01"].dropna().corr().values
fig,ax=plt.subplots(figsize=(6.2,5.2)); im=ax.imshow(C,cmap="RdBu_r",vmin=-1,vmax=1)
ax.set_xticks(range(len(allc))); ax.set_yticks(range(len(allc)))
ax.set_xticklabels(allc,rotation=45,ha="right",fontsize=8); ax.set_yticklabels(allc,fontsize=8)
for i in range(len(allc)):
    for j in range(len(allc)): ax.text(j,i,f"{C[i,j]:.2f}",ha="center",va="center",fontsize=7,
        color="white" if abs(C[i,j])>0.5 else "black")
ax.set_title("Daily-return correlation of ORB sleeves (2022+)\nnear-zero everywhere except US100/US500")
plt.colorbar(im,fraction=0.046); plt.tight_layout(); plt.savefig("figs/figB1_corr.png"); plt.close()

# FIG B2: Sharpe bars
labs=["US100\n(best single)","US500","GER40","XAU_NY","equal-risk\nbook","tangency\nbook","uncorr.\nupper bound"]
vals=[sh(panel['US100_NY'].loc[panel.index>='2022-01-01'].dropna()),
      sh(panel['US500_NY'].loc[panel.index>='2022-01-01'].dropna()),
      sh(panel['GER40_cash'].loc[panel.index>='2022-01-01'].dropna()),
      sh(panel['XAU_NY'].loc[panel.index>='2022-01-01'].dropna()),
      sh(eqr),sh(tang),np.sqrt(sum((mu/sub.std().values)**2)*252)]
fig,ax=plt.subplots(figsize=(8,4))
cols=["#27ae60","#7f8c8d","#7f8c8d","#7f8c8d","#e67e22","#2980b9","#95a5a6"]
ax.bar(range(len(labs)),vals,color=cols); ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs,fontsize=8)
ax.axhline(vals[0],color="#27ae60",ls=":",lw=1)
ax.set_ylabel("daily Sharpe (annualized, 2022+)")
ax.set_title("Diversification dilutes, then barely beats, the best single sleeve\nequal-risk book < US100; even optimal tangency only ~+25%")
for i,v in enumerate(vals): ax.text(i,v+0.02,f"{v:.2f}",ha="center",fontsize=8)
plt.tight_layout(); plt.savefig("figs/figB2_sharpe.png"); plt.close()

# FIG B3: p(pass) book vs single
H=np.arange(1,253)
fig,ax=plt.subplots(figsize=(8,4.3))
ax.plot(H,cu,label=f"single US100 (rho={bu[0]})",color="#27ae60",lw=2)
ax.plot(H,ct,label=f"tangency book (rho={bt[0]})",color="#2980b9",lw=2)
ax.axvline(42,color="#e67e22",ls="--"); ax.text(44,0.05,"2 months",color="#e67e22")
ax.axhline(0.5,color="#c0392b",ls=":"); ax.text(150,0.515,"50% target",color="#c0392b")
ax.set_xlabel("trading days"); ax.set_ylabel("P(passed)"); ax.set_ylim(0,0.8)
ax.set_title("Diversified book vs best single sleeve (2022+ regime)\nbook lifts the EVENTUAL pass rate, not the 2-month rate")
ax.legend(loc="lower right"); plt.tight_layout(); plt.savefig("figs/figB3_book_ppass.png"); plt.close()
print("figs done")
