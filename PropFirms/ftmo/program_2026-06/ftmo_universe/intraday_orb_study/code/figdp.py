import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import dp_sizing as D
s=pd.read_parquet("cache/WIN_book.parquet")["rmult"]
_,pol=D.solve(s,T=42,two_step=False)
E1=pol["E1"]; P1=pol["P1"]
M=np.array([P1[d] for d in range(1,43)]).T*100
fig,ax=plt.subplots(figsize=(8.4,4.6))
im=ax.imshow(M,aspect="auto",origin="lower",cmap="viridis",extent=[1,42,E1[0],E1[-1]],vmin=0,vmax=4.5)
ax.axhline(11000,color="w",ls="--",lw=1); ax.text(2,11015,"+10% target",color="w",fontsize=8)
ax.axhline(9000,color="r",ls="--",lw=1)
ax.set_xlabel("trading days remaining"); ax.set_ylabel("account equity ($)")
ax.set_title("Optimal sizing policy rho*(equity, days left) - 1-step book (DP)")
plt.colorbar(im,label="optimal risk/trade rho* (%)"); plt.tight_layout()
plt.savefig("figs/figDP_policy.png"); plt.close(); print("done")
