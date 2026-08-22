"""B1 Phase 2 — the rate-REGIME test (crucial) + flow-vs-beta (two-sided) + year-by-year + cost/3-nights.
Question: is t=4.65 just 2002-2021 secular bull-bond beta, or a repeatable month-end flow surviving 2022+ ?"""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
P="/sessions/stoic-vigilant-meitner/mnt/data/panels/"
mac=pd.read_csv(P+"macro_etf_panel.csv",parse_dates=["Date"]).set_index("Date").sort_index()
r=np.log(mac["TLT"]).diff(); ym=mac.index.to_period("M"); yr=mac.index.year.values
de=mac.groupby(ym).cumcount(ascending=False)+1
me_mask=de.values<=3                      # last 3 days of month
rv=r.values; rd=(r-r.mean()).values       # demeaned (secular drift removed)
def trade(rr,mask): return pd.Series(rr[mask],index=ym.values[mask]).groupby(level=0).sum().dropna()
def desc(tr,lab):
    m=tr.mean()*1e4; t=m/(tr.std()*1e4/len(tr)**.5)
    print(f"  {lab:34s} mean={m:+.1f}bps t={t:+.2f} skew={skw(tr):+.2f} hit={(tr>0).mean():.2f} n={len(tr)}"); return m

print("=== TEST 3: RATE-REGIME SPLIT (crucial) ===")
for lab,a,b in [("2002-2021 bull-bond (falling rates)",2002,2021),("2022-2026 bear-bond (rising rates)",2022,2026)]:
    desc(trade(rv,me_mask&(yr>=a)&(yr<=b)),lab)

print("\n=== TEST 4: FLOW vs BETA (two-sided) ===")
base3=r.mean()*3*1e4; me_tr=trade(rv,me_mask)
print(f"  baseline = mean daily x3 (secular drift any 3 days) = {base3:+.1f}bps")
print(f"  month-end 3-day mean                                = {me_tr.mean()*1e4:+.1f}bps")
print(f"  EXCESS over baseline (the actual month-end flow)    = {me_tr.mean()*1e4-base3:+.1f}bps")
desc(trade(rd,me_mask),"month-end 3-day DEMEANED (flow only)")
for lab,a,b in [("2002-2021 demeaned-within",2002,2021),("2022-2026 demeaned-within",2022,2026)]:
    sub=(yr>=a)&(yr<=b); rds=(r-r[sub].mean()).values
    desc(trade(rds,me_mask&sub),lab)

print("\n=== year-by-year (bps/trade) ===")
ty=me_tr.groupby([p.year for p in me_tr.index]).mean()*1e4
print({int(k):round(v,0) for k,v in ty.items()})
pos=(ty>0).sum(); print(f"  positive years: {pos}/{len(ty)}")

print("\n=== TEST 2: cost over 3 nights (net of per-night CFD swap) ===")
m=me_tr.mean()*1e4
for sw in [1,2,3,5,8]: print(f"  swap {sw}bps/night x3 = {3*sw}bps -> net {m-3*sw:+.1f}bps ({'ALIVE' if m-3*sw>0 else 'DEAD'})")
print(f"  breakeven swap = {m/3:.1f} bps/night (above this, 3-night carry kills it)")
