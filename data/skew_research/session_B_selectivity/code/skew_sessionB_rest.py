"""session_B #2-#5 exploration. Canonical signals (L10), two-sided (L25), delay+1, FTMO-tradeable.
#2 crypto trend, #3 cross-asset rotation vs EW, #4 crypto weekend (mechanism), #5 vol-conditioned (median split)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
def L(f): return pd.read_csv(P+f,parse_dates=["Date"]).set_index("Date").sort_index()
btc=L("btc_full.csv")["BTC-USD"].dropna(); eth=L("crypto_panel.csv")["ETHUSD"].dropna()
mac=L("macro_etf_panel.csv"); fac=L("factor_etf_panel.csv")
def rep(x,lab,ann):
    x=x.dropna()
    if len(x)<20: print(f"  {lab:34s} n={len(x)} insuff"); return
    print(f"  {lab:34s} Sharpe={x.mean()/x.std()*np.sqrt(ann):+.2f} skew={skw(x):+.2f} hit={(x>0).mean():.2f} mean={x.mean()*1e4:+.1f}bps n={len(x)}")
def trend_ret(px,n=100): r=np.log(px).diff(); return np.sign(px-px.shift(n)).shift(1)*r

print("=== SB-2 Crypto trend (BTC/ETH 100d), skew+ ? corr TSMOM ? ===")
b=trend_ret(btc); e=trend_ret(eth)
rep(b,"BTC 100d trend (two-sided)",365); rep(e,"ETH 100d trend (two-sided)",365)
rep((np.sign(btc-btc.shift(100)).clip(lower=0).shift(1)*np.log(btc).diff()),"BTC trend LONG-only",365)
tsmom=pd.concat([trend_ret(mac[c]) for c in ["DBC","GLD","UUP"]],axis=1).mean(axis=1)
cc=pd.concat([b.rename("b"),tsmom.rename("t")],axis=1).dropna()
rho=cc.corr().iloc[0,1]; print(f"  corr(BTC trend, commo/FX TSMOM) = {rho:+.2f} -> {'REDUNDANT(tuning)' if abs(rho)>0.5 else 'distinct brick'}")

print("=== SB-3 Cross-asset momentum rotation vs EW (FTMO classes, NO bonds) ===")
A=pd.concat([fac["SPY"],mac["GLD"],mac["DBC"],btc,mac["UUP"]],axis=1,keys=["SPY","GLD","DBC","BTC","UUP"]).dropna()
px=np.log(A).resample("ME").last(); mret=px.diff(); mom=px-px.shift(3)
rk=mom.shift(1).rank(axis=1); top=rk.eq(rk.max(axis=1),axis=0); bot=rk.eq(rk.min(axis=1),axis=0)
rep((mret[top].mean(axis=1)-mret[bot].mean(axis=1)),"rotation L/S (top-bottom)",12)
rep(mret[top].mean(axis=1),"rotation LONG-top only",12); rep(mret.mean(axis=1),"EW long basket (ref)",12)

print("=== SB-4 Crypto weekend (pre-specified: 24/7 low weekend liquidity; NO day mining) ===")
r=np.log(btc).diff(); wd=btc.index.weekday
def mt(x): x=x.dropna(); return x.mean()*1e4, x.mean()/(x.std()/np.sqrt(len(x))), skw(x), len(x)
for lab,m in [("weekend (Sat+Sun)",wd>=5),("weekday (Mon-Fri)",wd<5)]:
    a,t,s,n=mt(r[m]); print(f"  BTC {lab:18s} mean={a:+.1f}bps t={t:+.2f} skew={s:+.2f} n={n}")

print("=== SB-5 Vol-conditioned (US500, VIX MEDIAN split, no tuning) ===")
c=L("ftmo_close.csv")["US500"].dropna(); rr=np.log(c).diff()
vx=L("vix.csv"); vix=vx.iloc[:,0].reindex(c.index).ffill(); hi=vix>vix.median()
d=c.diff(); u=d.clip(lower=0).rolling(14).mean(); dn=(-d.clip(upper=0)).rolling(14).mean(); rsi=100-100/(1+u/dn)
mr=(rsi<30).astype(float)-(rsi>70).astype(float); tr=np.sign(c-c.shift(50))
rep((mr.where(hi,0).shift(1)*rr),"MR | HIGH vol",252); rep((mr.where(~hi,0).shift(1)*rr),"MR | LOW vol",252); rep((mr.shift(1)*rr),"MR unconditional (ref)",252)
rep((tr.where(hi,0).shift(1)*rr),"trend | HIGH vol",252); rep((tr.where(~hi,0).shift(1)*rr),"trend | LOW vol",252); rep((tr.shift(1)*rr),"trend unconditional (ref)",252)
