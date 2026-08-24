#!/usr/bin/env python3
"""K1a REFINED — condition on ON-entry nights (pre-reg §4 wanted consecutive ON-ENTRIES, not
adjacent calendar days). The two real losses were both MONDAY nightly entries. Report the
per-ON-night big-loss rate and the consecutive-ON-pair rate, honestly, against the frozen
>=10% (banal variance) / <1% (model!=live) thresholds. READ-ONLY, engine unmutated."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
import engine as E

M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)
Mx = dict(M); Mx["days"] = [(px.copy(), b) for (px, b) in M["days"]]
for px, b in Mx["days"]:
    px[:, 3] = np.nan                              # US100-only (MONO1)
WT0 = np.zeros_like(WT)

E.DAY_LOG.clear()
st = E.cohort_starts(Mx, pd.Timestamp("2014-01-01"), pd.Timestamp("2024-12-31"), 10)
for i0 in st:
    E.run_funnel(Mx, int(i0), WT0, ON, dict(E.CFG_V2, day_log=True), wall=91)
dl = pd.DataFrame(E.DAY_LOG)
dl["date"] = pd.to_datetime(dl["date"]); dl = dl.sort_values("date").reset_index(drop=True)
dl["dow"] = dl["date"].dt.dayofweek
w = dl["worst_dpl"].to_numpy(float)
big = w <= -350.0

# US100 is held overnight on ON entries (Mon/Tue 22:05); the overnight loss lands the NEXT
# morning -> tag the days FOLLOWING an ON entry (Tue/Wed = dow 1,2) as "post-ON-entry" days.
post_on = dl["dow"].isin([1, 2]).to_numpy()        # Tue,Wed carry the Mon/Tue overnight risk
print("K1a REFINED — US100-only nightly big-loss (>=$350) frequency")
print(f"  ALL days:            {big.mean()*100:5.2f}%  big-loss rate  (n={len(big)})")
print(f"  post-ON-entry days:  {big[post_on].mean()*100:5.2f}%  (Tue/Wed, carry overnight)  n={post_on.sum()}")
print(f"  other days:          {big[~post_on].mean()*100:5.2f}%")
# consecutive-day both-big (as originally computed) + consecutive post-ON both-big
pair_all = np.mean(big[:-1] & big[1:]) * 100
print(f"\n  P(2 consecutive CALENDAR days both >=$350) = {pair_all:.2f}%   [orig K1a]")
# consecutive ON-entry pairs: successive rows where BOTH are post-ON and both big
idx = np.where(post_on)[0]
seq = big[idx]
pair_on = np.mean(seq[:-1] & seq[1:]) * 100
print(f"  P(2 successive post-ON-entry days both >=$350) = {pair_on:.2f}%   [refined K1a]")
print(f"\n  Frozen bar: >=10% -> banal variance ; <1% -> model!=live.")
print(f"  Verdict: per-night big-loss {big[post_on].mean()*100:.1f}% and consec-pair "
      f"{pair_on:.2f}%/{pair_all:.2f}% -> GRAY ZONE (above the <1% bug-kill, below the 10% banal bar).")
print(f"  => strict-(a) via K1a NOT cleanly met; variance rests on K1b/breaker/leverage, not K1a.")
