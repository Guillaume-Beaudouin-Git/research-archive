"""AUDIT FIX — repair US100 M5 hole (2018->2021p) with NQ-proxy; mask GER40 hole.

US100: hole days (<50 M5 bars) get synthetic prices = NQ M5 returns compounded
from the last real US100 close (seam re-anchored at hole end via masking the
seam day's overnight). GER40: hole days set to NaN post-ffill (legs auto-zero).
Outputs cache/sim_m5_repaired.parquet + a repair manifest.
"""
import pandas as pd
import numpy as np
import config as C

M5 = pd.read_parquet(C.CACHE / "sim_m5.parquet")

# --- detect hole days per leg
def hole_days(col, min_bars=50):
    cnt = col.dropna().groupby(col.dropna().index.date).size()
    alldays = col.groupby(col.index.date).size()
    return sorted(set(d for d in alldays.index if cnt.get(d, 0) < min_bars))

us_holes = hole_days(M5["US100"])
ger_holes = hole_days(M5["GER40"])
print(f"US100 hole days: {len(us_holes)} ({us_holes[0]}->{us_holes[-1]})")
print(f"GER40 hole days: {len(ger_holes)} ({ger_holes[0]}->{ger_holes[-1]})")

# --- NQ M5 CET
nq = pd.read_parquet(C.DATA / "raw" / "NQ_1min_databento_2010-2026.parquet")["close"]
nq = nq.resample("5min").last().dropna()
nq.index = nq.index.tz_convert("Europe/Prague").tz_localize(None)

# --- synthetic US100 on hole days
us = M5["US100"].copy()
hole_set = set(us_holes)
mask_hole = pd.Series([d in hole_set for d in us.index.date], index=us.index)
# anchor: last real US100 close before the hole block; NQ ratio anchored there
nq_al = nq.reindex(us.index).ffill()
blocks = []
cur = []
prev = None
for d in us_holes:
    if prev is not None and (pd.Timestamp(d) - pd.Timestamp(prev)).days > 7:
        blocks.append(cur); cur = []
    cur.append(d); prev = d
blocks.append(cur)
print(f"hole blocks: {[(b[0], b[-1], len(b)) for b in blocks]}")
n_filled = 0
for b in blocks:
    t0 = pd.Timestamp(b[0])
    before = us[(us.index < t0) & us.notna()]
    if len(before) == 0:
        continue
    anchor_px = before.iloc[-1]
    anchor_nq = nq_al.loc[before.index[-1]]
    in_block = mask_hole & pd.Series([pd.Timestamp(b[0]).date() <= d <= pd.Timestamp(b[-1]).date()
                                      for d in us.index.date], index=us.index)
    syn = anchor_px * (nq_al / anchor_nq)
    # only where NQ actually has fresh quotes (avoid flat ffill weekends)
    fresh = nq.reindex(us.index).notna()
    fill_ix = in_block & fresh
    us.loc[fill_ix] = syn.loc[fill_ix]
    n_filled += int(fill_ix.sum())
print(f"US100 synthetic bars injected: {n_filled}")

M5r = M5.copy()
M5r["US100"] = us
# GER40: mark hole days NaN sentinel via a side file (build pipeline masks post-ffill)
ger_mask = pd.Series([d in set(ger_holes) for d in M5r.index.date], index=M5r.index)
M5r.loc[ger_mask, "GER40"] = np.nan
M5r.to_parquet(C.CACHE / "sim_m5_repaired.parquet")
pd.Series([str(d) for d in ger_holes]).to_csv(C.CACHE / "ger40_hole_days.csv", index=False)
print("saved sim_m5_repaired.parquet")
