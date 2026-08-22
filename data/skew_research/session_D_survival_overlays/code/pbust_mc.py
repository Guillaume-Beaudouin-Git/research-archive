"""session_D — p(bust) MC (block bootstrap) for baseline vs survivors (#1 DD-sizing, #5 cap, #1+#5).
FTMO 2-step proxy: bust if cum<=-10% (static) OR any day<=-5% (daily); pass if cum>=+10%. Equal 15% vol (L19)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
def L(f): return pd.read_csv(P+f,parse_dates=["Date"]).set_index("Date").sort_index()
IDX=["US500","US100","GER40","JP225","US30"]
px=pd.concat([L("ftmo_close.csv")[IDX], L("macro_etf_panel.csv")[["GLD","DBC"]], L("commodity_panel.csv")[["USO","SLV"]],
              L("fx_panel.csv")[["FXE","FXB","FXY"]], L("btc_full.csv")[["BTC-USD"]], L("crypto_panel.csv")[["ETHUSD"]]],axis=1)
px=px[~px.index.duplicated()].sort_index(); ret=np.log(px).diff()
sig=np.sign(px/px.shift(252)-1); vol=ret.ewm(span=60,min_periods=20).std(); z=ret/vol
raw=(sig.shift(1)*z).mean(axis=1).dropna()
rawcap=((sig.shift(1)*z).clip(-3,3)).mean(axis=1).dropna()    # #5
TV=0.15/np.sqrt(252)
def s15(x): x=x.dropna(); return x*TV/x.std()
def dd_sizing(rawx, ddmax=0.10):
    xs=s15(rawx).values; n=len(xs); out=np.zeros(n); eq=1.0; pk=1.0
    for t in range(n):
        g=np.clip((ddmax-abs(eq/pk-1))/ddmax,0,1); out[t]=g*xs[t]; eq*=(1+out[t]); pk=max(pk,eq)
    return pd.Series(out,index=s15(rawx).index)
base=s15(raw); cap=s15(rawcap); dds=s15(dd_sizing(raw)); dds_cap=s15(dd_sizing(rawcap))
def MC(xs,lev,H=60,B=10,nsim=6000,dds_=0.10,ddd=0.05,tgt=0.10,seed=1):
    a=xs.dropna().values*lev; n=len(a); rng=np.random.default_rng(seed); nb=H//B; bust=pas=0
    for _ in range(nsim):
        st=rng.integers(0,n-B,nb); path=np.concatenate([a[s:s+B] for s in st]); eq=0.0; b=p=False
        for r in path:
            if r<=-ddd: b=True; break
            eq=(1+eq)*(1+r)-1
            if eq<=-dds_: b=True; break
            if eq>=tgt: p=True; break
        bust+=b; pas+=p
    return bust/nsim,pas/nsim
def line(xs,lab):
    sk=skw(xs.dropna()); wd=xs.min()
    print(f"  {lab:20s} skew={sk:+.2f} worstDay={wd:.2%}", end="")
    for lev,tag in [(1.0,"15%"),(2.0,"30%")]:
        b,p=MC(xs,lev); print(f"  | lev{tag}: p(bust)={b:.1%} p(pass)={p:.1%}", end="")
    print()
print("=== p(bust) MC — FTMO 2-step proxy (cum-10% / day-5% / target+10%), 60d, block=10 ===")
line(base,"baseline TSMOM"); line(cap,"#5 per-sleeve cap"); line(dds,"#1 DD-sizing"); line(dds_cap,"#1+#5 combined")
# DSR context
sr=base.mean()/base.std()*np.sqrt(252)
print(f"\nbaseline SR={sr:.2f} over {len(base)}d; cumulative N_tests across sessions ~ O(150) -> DSR haircut applies to SR claims,")
print("but overlays are judged on skew/worstDay/p(bust) at equal vol (L15), not SR -> SR≈const by construction.")
