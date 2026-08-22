"""session_D — RISK OVERLAYS on naked TSMOM (FTMO-tradeable universe, daily).
Judge on SKEW + maxDD-daily + worst-day at EQUAL operational vol (L19 rescale), NOT Sharpe (L15).
Canonical specs only (L10), no sweep. Baseline = naked 12M TSMOM, inverse-vol, EW, FTMO instruments (NO bonds)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
def L(f): return pd.read_csv(P+f,parse_dates=["Date"]).set_index("Date").sort_index()
IDX=["US500","US100","GER40","JP225","US30"]
clo=L("ftmo_close.csv")[IDX]; opn=L("ftmo_open.csv")[IDX]
px=pd.concat([clo, L("macro_etf_panel.csv")[["GLD","DBC"]], L("commodity_panel.csv")[["USO","SLV"]],
              L("fx_panel.csv")[["FXE","FXB","FXY"]], L("btc_full.csv")[["BTC-USD"]], L("crypto_panel.csv")[["ETHUSD"]]],axis=1)
px=px[~px.index.duplicated()].sort_index()
ret=np.log(px).diff()
intr=pd.DataFrame(index=px.index)
for c in IDX: intr[c]=np.log(clo[c]/opn[c])     # intraday-only (close/open) for flat-overnight
sig=np.sign(px/px.shift(252)-1)                 # 12M TSMOM
vol=ret.ewm(span=60,min_periods=20).std()
z=ret/vol                                        # vol-standardized return
base_pnl=(sig.shift(1)*z)                         # per-instrument standardized PnL (delay+1)
raw=base_pnl.mean(axis=1).dropna()               # naked TSMOM portfolio (EW available)
TV=0.15/np.sqrt(252)
def s15(x): x=x.dropna(); return x*TV/x.std()     # ex-post vol-normalise to 15% ann (fair compare, L19)
def report(x,lab):
    xs=s15(x); eq=(1+xs).cumprod(); dd=(eq/eq.cummax()-1)
    sr=xs.mean()/xs.std()*np.sqrt(252)
    print(f"  {lab:32s} SR={sr:+.2f} skew={skw(xs):+.3f} maxDD={dd.min():.1%} worstDay={xs.min():.2%} p1%={np.percentile(xs,1):.2%}")
    return xs
print("=== BASELINE (naked TSMOM, FTMO-only, rescaled 15% ann) ===")
report(raw,"naked TSMOM")
print(f"  (universe n={px.shape[1]} instruments, sample {raw.index.min().date()}..{raw.index.max().date()}, days={len(raw)})")

# ---------- OVERLAYS (each: transform -> rescale 15% -> compare) ----------
def dd_sizing(rawx, ddmax=0.10):
    xs=s15(rawx).values; n=len(xs); out=np.zeros(n); eq=1.0; pk=1.0
    for t in range(n):
        g=np.clip((ddmax-abs(eq/pk-1))/ddmax,0,1)   # throttle by DD at start of day t
        out[t]=g*xs[t]; eq*=(1+out[t]); pk=max(pk,eq)
    return pd.Series(out,index=s15(rawx).index)
print("=== #1 DD-SIZING (recursive throttle, ddmax=10%) ===")
report(dd_sizing(raw),"#1 DD-sizing")
report(dd_sizing(raw[raw.index>='2023-01-01']),"#1 OOS 2023+")
for dm in [0.07,0.13]: report(dd_sizing(raw,dm),f"#1 sens ddmax={dm:.0%}")

print("=== #2 VOL-TARGET symmetric vs ASYMMETRIC ===")
rv=np.sqrt((raw**2).ewm(span=60,min_periods=20).mean())
dvar=np.sqrt((raw.clip(upper=0)**2).ewm(span=20,min_periods=10).mean()*2)   # downside vol, fast
gsym=(raw.std()/rv); gasym=(raw.std()/np.maximum(rv,dvar))                   # asym cuts faster on losses
report(raw*gsym.shift(1),"#2 vol-target SYMMETRIC")
report(raw*gasym.shift(1),"#2 vol-target ASYMMETRIC")

print("=== #3 FLAT-OVERNIGHT (index sleeve = intraday only) ===")
ret3=ret.copy()
for c in IDX: ret3[c]=intr[c]
raw3=(sig.shift(1)*(ret3/vol)).mean(axis=1)        # index PnL uses intraday return; signal unchanged
report(raw3.dropna(),"#3 flat-overnight (idx)")
report(raw,"   (ref: full incl overnight)")

print("=== #4 THROTTLE VOL-OF-VOL (halve gross when vov>median) ===")
xs=s15(raw); rvv=xs.rolling(20).std(); vov=rvv.rolling(20).std()
g4=pd.Series(np.where(vov>vov.median(),0.5,1.0),index=xs.index)
report(raw*g4.shift(1),"#4 vov-throttle")

print("=== #5 PER-SLEEVE VOL CAP (clip each instrument PnL at +/-3z) ===")
raw5=(sig.shift(1)*z).clip(-3,3).mean(axis=1)
report(raw5.dropna(),"#5 per-sleeve cap")
