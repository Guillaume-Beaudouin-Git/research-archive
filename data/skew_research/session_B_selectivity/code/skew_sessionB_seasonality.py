"""session_B #1 — Commodity seasonality OPERATIONALISED (not re-proving the archive edge).
Monthly seasonal means -> deployable calendar mapped to FTMO CFDs; mechanism-anchored sleeves; skew/corr lens."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
def load(f): return pd.read_csv(P+f,parse_dates=["Date"]).set_index("Date").sort_index()
allc=pd.concat([load("commodity_panel.csv"),load("softs_metals.csv"),load("macro_etf_panel.csv")[["GLD","DBC"]]],axis=1)
mc=np.log(allc).resample("ME").last().diff()
ftmo={"USO":"WTI","UKOIL":"Brent","UGA":"Gasoline","UNG":"NatGas","GLD":"Gold","SLV":"Silver","XPTUSD":"Platinum","PALL":"Palladium","CPER":"Copper"}
softs={"COCOA":"Cocoa","COFFEE":"Coffee","SOYBEAN":"Soybean","CORN":"Corn","WEAT":"Wheat"}
print("=== Monthly seasonal mean return (bps/month), full history ===")
print("inst    "+"  ".join(f"{m:>4}" for m in range(1,13))+"   name")
for k in list(ftmo)+list(softs):
    if k in mc.columns:
        s=mc[k].dropna(); mm=s.groupby(s.index.month).mean()*1e4
        row="  ".join((f"{mm[m]:>4.0f}" if m in mm.index else "  na") for m in range(1,13))
        print(f"{k:7s} {row}   {ftmo.get(k,softs.get(k))} (n={len(s)})")
def sleeve(inst,months,lab):
    if inst not in mc.columns: print(f"  {lab}: missing"); return None
    s=mc[inst].dropna(); x=s[s.index.month.isin(months)]
    m=x.mean()*1e4; t=m/(x.std()*1e4/len(x)**.5)
    print(f"  {lab:40s} mean={m:+.0f}bps/mo t={t:+.2f} skew={skw(x):+.2f} hit={(x>0).mean():.2f} n={len(x)}")
    return s.index.month.isin(months).astype(float)*s   # contribution series
print("\n=== Mechanism-anchored seasonal sleeves (pre-specified, not mined) ===")
sleeve("UNG",[9,10,11,12],"NatGas LONG Sep-Dec (winter heating build)")
sleeve("UGA",[2,3,4,5],"Gasoline LONG Feb-May (pre-driving season)")
sleeve("USO",[2,3,4,5],"Crude LONG Feb-May (pre-driving season)")
sleeve("GLD",[1,8,9],"Gold LONG Jan,Aug,Sep (festival/wedding demand)")
sleeve("CPER",[2,3,4],"Copper LONG Feb-Apr (China restock post-CNY)")
print("\n=== Equal-weight mechanism-seasonal sleeve: skew + corr (portfolio lens) ===")
specs={"UNG":[9,10,11,12],"UGA":[2,3,4,5],"USO":[2,3,4,5],"GLD":[1,8,9],"CPER":[2,3,4]}
contrib=[]
for inst,mo in specs.items():
    if inst in mc.columns:
        s=mc[inst].dropna(); contrib.append((s.index.month.isin(mo)).astype(float)*s)
port=pd.concat(contrib,axis=1).mean(axis=1).dropna()
m=port.mean()*1e4; t=m/(port.std()*1e4/len(port)**.5)
print(f"  EW seasonal sleeve: mean={m:+.0f}bps/mo t={t:+.2f} skew={skw(port):+.2f} hit={(port>0).mean():.2f} n={len(port)}")
spy=np.log(load("factor_etf_panel.csv")["SPY"]).resample("ME").last().diff()
print(f"  corr(seasonal sleeve, SPY monthly) = {pd.concat([port.rename('a'),spy.rename('b')],axis=1).dropna().corr().iloc[0,1]:+.3f}")
