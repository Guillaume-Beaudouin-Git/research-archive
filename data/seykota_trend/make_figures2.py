"""Additional institutional figures: underwater curve w/ episodes, regime bars, rolling exposure heat."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np, pandas as pd
HERE=Path(__file__).resolve().parent; RES=HERE/"results"; FIG=HERE/"figures"
plt.rcParams.update({"figure.facecolor":"white","axes.grid":True,"grid.alpha":0.25,
 "axes.spines.top":False,"axes.spines.right":False,"font.size":10,"axes.titlesize":11,"axes.titleweight":"bold"})
C={"capped":"#1f4e79","pos":"#2e7d32","neg":"#c0504d","amber":"#e8a33d"}
eq=pd.read_csv(RES/"equity_extended_capped.csv",index_col=0,parse_dates=True)["equity"]
rg=pd.read_csv(RES/"regime_table.csv")

# fig8: regime CAGR vs vol bars
fig,ax=plt.subplots(figsize=(11,4.6))
x=np.arange(len(rg))
cagr=rg["cagr"].values*100
cols=[C["pos"] if v>=0 else C["neg"] for v in cagr]
b=ax.bar(x,cagr,color=cols,width=0.62)
ax.set_xticks(x,[r.replace(" ","\n",1) for r in rg["regime"]],fontsize=7.4)
ax.axhline(0,color="k",lw=0.8); ax.set_ylabel("CAGR annualisé (%)")
ax.set_title("Performance par régime de marché — variante cash, 2014–2026")
for xi,v,s in zip(x,cagr,rg["sharpe"]):
    ax.text(xi,v+(3 if v>=0 else -3),f"{v:.0f}%\nSh {s:.2f}",ha="center",
            va="bottom" if v>=0 else "top",fontsize=7)
fig.tight_layout(); fig.savefig(FIG/"fig8_regimes.png",dpi=150); plt.close(fig)

# fig9: underwater curve with episode annotations
dd=(eq/eq.cummax()-1)*100
fig,ax=plt.subplots(figsize=(11,4.0))
ax.fill_between(dd.index,dd,0,color=C["neg"],alpha=0.5,lw=0)
ax.plot(dd.index,dd,color=C["neg"],lw=0.7)
ax.set_title("Courbe underwater (drawdown %) — cash, 2014–2026")
ax.set_ylabel("%")
ep=pd.read_csv(RES/"drawdown_episodes.csv").sort_values("depth").head(3)
for _,e in ep.iterrows():
    t=pd.Timestamp(e["trough"])
    ax.annotate(f"{e['depth']*100:.0f}%\n{t.date()}",xy=(t,e["depth"]*100),
                xytext=(t,e["depth"]*100-4),fontsize=7.5,ha="center",
                arrowprops=dict(arrowstyle="-",lw=0.6,color="k"))
fig.tight_layout(); fig.savefig(FIG/"fig9_underwater.png",dpi=150); plt.close(fig)

# fig10: yearly returns strategy vs spx
spx=pd.read_parquet(HERE/"daily/US500.parquet")["close"]
sy=spx.resample("YE").last().pct_change()*100
ey=eq.resample("YE").last(); yr=ey.pct_change(); yr.iloc[0]=ey.iloc[0]/eq.iloc[0]-1; yr*=100
yr.index=yr.index.year; sy.index=sy.index.year
yrs=[y for y in yr.index if y in sy.index or y==yr.index[0]]
fig,ax=plt.subplots(figsize=(11,4.0))
x=np.arange(len(yr)); w=0.4
ax.bar(x-w/2,yr.values,w,color=C["capped"],label="Stratégie (cash)")
sv=[sy.get(y,np.nan) for y in yr.index]
ax.bar(x+w/2,sv,w,color="#9e9e9e",label="US500 (prix)")
ax.set_xticks(x,yr.index,fontsize=8); ax.axhline(0,color="k",lw=0.8)
ax.set_ylabel("Rendement annuel (%)"); ax.legend(frameon=False,fontsize=9)
ax.set_title("Rendements annuels : stratégie vs US500 buy & hold")
fig.tight_layout(); fig.savefig(FIG/"fig10_yearly.png",dpi=150); plt.close(fig)
print("ok", sorted(p.name for p in FIG.glob("fig8*"))+sorted(p.name for p in FIG.glob("fig9*"))+sorted(p.name for p in FIG.glob("fig10*")))
