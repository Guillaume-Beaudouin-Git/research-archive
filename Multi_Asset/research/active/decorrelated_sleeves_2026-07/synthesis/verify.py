"""INDEPENDENT VERIFICATION (author != auditor). Fresh code, does NOT import the piste engines or lib/.
Recomputes the 3 decisive claims directly from cached pickles."""
import numpy as np, pandas as pd
from statsmodels.tsa.stattools import adfuller
from scipy import stats as sps

C = "/sessions/zealous-zen-brahmagupta/mnt/Algo_claude/Multi_Asset/research/active/decorrelated_sleeves_2026-07/cache"
def D(s, f="D"): return pd.read_pickle(f"{C}/{s}_{f}.pkl")

print("="*70, "\nCLAIM A — US500/US30 not OOS-cointegrated; profit is directional drift\n", "="*70)
a, b = np.log(D("US500")["close"]), np.log(D("US30")["close"])
df = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
n = len(df); h = n // 2
# A1 OOS EG
X = np.column_stack([np.ones(h), df["b"].values[:h]])
beta = np.linalg.lstsq(X, df["a"].values[:h], rcond=None)[0]
res_oos = df["a"].values[h:] - (beta[0] + beta[1] * df["b"].values[h:])
p_oos = adfuller(res_oos, maxlag=1, autolag=None)[1]
print(f"A1  OOS Engle-Granger ADF p = {p_oos:.3f}   -> {'NOT coint (p>0.05)' if p_oos>0.05 else 'coint'}")
# A2 per-year
yrs = df.groupby(df.index.year)
ps = []
for y, g in yrs:
    if len(g) < 60: continue
    Xy = np.column_stack([np.ones(len(g)), g["b"].values])
    by = np.linalg.lstsq(Xy, g["a"].values, rcond=None)[0]
    ry = g["a"].values - (by[0] + by[1] * g["b"].values)
    ps.append(adfuller(ry, maxlag=1, autolag=None)[1])
print(f"A2  per-year coint frac (p<0.05) = {np.mean([p<0.05 for p in ps]):.2f}  ({sum(p<0.05 for p in ps)}/{len(ps)} yrs)")
# A3 leg asymmetry
bw = 252; zw = 60
mb = df["b"].rolling(bw).mean(); ma = df["a"].rolling(bw).mean()
cov = (df["a"]*df["b"]).rolling(bw).mean() - ma*mb
var = (df["b"]*df["b"]).rolling(bw).mean() - mb*mb
bt = (cov/var).shift(1)
spread = df["a"] - bt*df["b"]
z = (spread - spread.rolling(zw).mean())/spread.rolling(zw).std()
ret = df["a"].diff() - bt.shift(1)*df["b"].diff()
zc = z.values; rc = ret.values
pos = np.zeros(n); cur = 0
for t in range(n):
    if np.isnan(zc[t]): pos[t]=0; cur=0; continue
    if cur==0:
        if zc[t]<=-2: cur=1
        elif zc[t]>=2: cur=-1
    elif abs(zc[t])<0.5: cur=0
    pos[t]=cur
posx = np.concatenate([[0],pos[:-1]])
pnl = posx*np.nan_to_num(rc)
# per-trade grouping
long_tr, short_tr = [], []
i=0
while i<n:
    if posx[i]!=0:
        d=posx[i]; j=i
        while j<n and posx[j]==d: j+=1
        r=np.nansum(pnl[i:j]); (long_tr if d>0 else short_tr).append(r); i=j
    else: i+=1
def wr(x): return 100*np.mean([v>0 for v in x]) if x else 0
print(f"A3  long-spread: n={len(long_tr)} mean={np.mean(long_tr)*1e4:+.0f}bps win%={wr(long_tr):.0f} | "
      f"short-spread: n={len(short_tr)} mean={np.mean(short_tr)*1e4:+.0f}bps win%={wr(short_tr):.0f}")

print("\n" + "="*70, "\nCLAIM B — fading overbought indices fails (event study, no state machine)\n", "="*70)
def rsi(c, nn):
    d=c.diff(); up=d.clip(lower=0); dn=(-d).clip(lower=0)
    return (100-100/(1+up.ewm(alpha=1/nn,adjust=False).mean()/dn.ewm(alpha=1/nn,adjust=False).mean().replace(0,np.nan))).fillna(50)
for s in ["US100","US500","US30","GER40"]:
    c=D(s)["close"]; lc=np.log(c); r2=rsi(c,2)
    fwd5 = lc.shift(-5)-lc                       # forward 5-day log return
    ob = r2>90
    x = fwd5[ob].dropna()
    t = x.mean()/(x.std()/np.sqrt(len(x)))
    unc = fwd5.dropna().mean()
    verdict = "SHORT LOSES (fwd>=0)" if x.mean()>=0 else "short wins"
    print(f"  {s}: after RSI2>90  fwd5 mean={x.mean()*1e4:+.0f}bps (t={t:+.2f}, n={len(x)}) | uncond={unc*1e4:+.0f}bps  -> {verdict}")

print("\n" + "="*70, "\nCLAIM C — range-fade edge is look-ahead (EURUSD hourly, fixed 8-bar hold)\n", "="*70)
h1 = D("EURUSD","H"); c=h1["close"]; lc=np.log(c); ret=lc.diff()
sma=c.rolling(20).mean(); sd=c.rolling(20).std(); up=sma+2*sd; dn=sma-2*sd
# ADX(14)
hh,ll,cc=h1["high"],h1["low"],h1["close"]; pc=cc.shift(1)
plus=(hh.diff()).clip(lower=0); minus=(-ll.diff()).clip(lower=0)
plus=plus.where(plus>minus,0.0); minus=minus.where(minus>plus,0.0)
tr=pd.concat([hh-ll,(hh-pc).abs(),(ll-pc).abs()],axis=1).max(axis=1)
atr=tr.ewm(alpha=1/14,adjust=False).mean()
pdi=100*plus.ewm(alpha=1/14,adjust=False).mean()/atr; mdi=100*minus.ewm(alpha=1/14,adjust=False).mean()/atr
dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan); adx=dx.ewm(alpha=1/14,adjust=False).mean()
fwd8 = lc.shift(-8)-lc
sig = np.where(c>=up,-1,np.where(c<=dn,1,0))     # short at upper, long at lower
trade = sig!=0
fut_vol = ret.shift(-1).rolling(8).std().shift(-7)
causal = trade & (adx.shift(1).values<25)
oracle = trade & (fut_vol.values < np.nanquantile(fut_vol.values,0.40))
for name,msk in [("CAUSAL(ADX<25 trailing)",causal),("ORACLE(next-8-vol low)",oracle)]:
    pr = (sig*fwd8.values)[msk]; pr=pr[~np.isnan(pr)]
    shp = pr.mean()/pr.std()*np.sqrt(252*24/8) if pr.std()>0 else 0
    print(f"  {name}: mean={pr.mean()*1e4:+.2f}bps/trade  n={len(pr)}  ann.Sharpe~{shp:+.2f}")
print("\nDONE.")
