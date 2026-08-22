"""Batch 3 PHASE 1 (intraday) — FTMO-tradeable. #3 FX month-end London fix (EURUSD M1, true UTC),
#5 crypto funding-reset timing (BTC 8h + funding, ≠ carry). Naked signals (L10)."""
import pandas as pd, numpy as np
from scipy.stats import skew as skw
D="/sessions/stoic-vigilant-meitner/mnt/data/"
def desc(x,lab):
    x=pd.Series(x).dropna()
    if len(x)<8: print(f"  {lab:46s} n={len(x)} insuff"); return
    m=x.mean()*1e4; t=m/(x.std()*1e4/len(x)**.5)
    print(f"  {lab:46s} n={len(x):5d} mean={m:+.1f}bps t={t:+.2f} skew={skw(x):+.2f} hit={(x>0).mean():.2f}")

print("=== B3-3 FX month-end London 4pm fix (EURUSD, UTC 2020-2026) ===")
e=pd.read_parquet(D+"ftmo_research/EURUSD_m1.parquet")["close"]
hr=e.resample("1h").last().dropna(); lr=np.log(hr).diff(); h=hr.index.hour
days=pd.Index(sorted(set(hr.index.normalize())))
dser=pd.Series(days); lbd=set(pd.to_datetime(dser.groupby(dser.dt.to_period("M")).max().values))
me=hr.index.normalize().isin(lbd)
# London 16:00 = 16:00 UTC (winter) / 15:00 UTC (summer) -> scan 15h & 16h bars
for hh in [15,16,17]:
    sel=(h==hh)
    desc(lr[sel&me], f"EURUSD {hh-1}->{hh}h UTC | MONTH-END")
    desc(lr[sel&~me], f"  {hh-1}->{hh}h UTC | normal day (ref)")
# directional into-fix (15->16 UTC) month-end, both signs check
desc(lr[(h==16)&me], "into-fix 15->16h month-end (long EUR)")
desc(-lr[(h==16)&me], "into-fix 15->16h month-end (short EUR)")

print("=== B3-5 Crypto funding-reset timing (BTC 8h + funding, 2023-2026) ===")
b=pd.read_csv(D+"funding_carry/prices/BTC_8h.csv",parse_dates=["timestamp"]).set_index("timestamp").sort_index()
f=pd.read_csv(D+"funding_carry/BTC_funding.csv",parse_dates=["timestamp"]).set_index("timestamp").sort_index()
r=np.log(b["close"]).diff()
df=pd.concat([r.rename("r"),f["funding_rate_1h"].rename("f")],axis=1).dropna()
df["rnext"]=df["r"].shift(-1)
desc(df["r"], "raw 8h bar return (ref)")
desc((np.sign(df.f)*df.rnext).dropna(), "sign(funding) x next-8h [carry dir, archive-killed]")
desc((-np.sign(df.f)*df.rnext).dropna(), "-sign(funding) x next-8h [fade crowded, NEW timing angle]")
# reset-time conditioning: which 8h slot (00/08/16 UTC) carries drift?
df["hr"]=df.index.hour
for hh in [0,8,16]:
    desc(df.r[df.hr==hh], f"8h bar starting {hh:02d}:00 UTC (raw)")
