"""Step 2 — rebuild the already-measured window series and add the INTRADAY PATH.

Nothing is re-optimised: the spec (LONG at the first M1 print at/after the 18:00 ET
Globex reopen, exit at the last print at/before +8h, settlement gap excluded) is copied
verbatim from `overnight_futures_2026-07/code/step3_performance.py:tradable_series`,
including its price-lookup tolerances (20 min on entry, 30 min on exit).

TWO deliberate departures, both of which MATTER for a barrier study and neither of
which touches the signal:

 1. **No winsorisation.** The archived `tradable_series` clips at the 0.5/99.5
    quantiles. That is defensible for a Sharpe; it is *disqualifying* for a
    first-passage simulation, because the clipped tail is precisely the tail that
    touches the FTMO floor. We keep the raw series and report what the clip hid.
 2. **Intra-window path.** FTMO enforces the daily loss on EQUITY, not on the close.
    A session that closes flat can still breach on its excursion. We therefore carry
    `mae` (worst cumulative excursion inside the window) alongside `ret`.

Reproduction gate: on the sessions the archived series did NOT clip, `ret` must match
it to machine precision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common_reopen import OUT, PRIOR_SERIES, REOPEN_ET, WINDOW_HOURS, load_m1, us_dst

H = np.int64(3_600_000_000_000)

m1 = load_m1()
ts = pd.DatetimeIndex(m1["ts"])
et = ts - pd.to_timedelta(np.where(us_dst(ts), 4, 5), unit="h")   # US Eastern wall clock
keys = et.asi8
px = m1["close"].to_numpy(float)

sess = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
base = (sess + pd.Timedelta(hours=REOPEN_ET)).asi8
endt = base + WINDOW_HOURS * H

# entry: first print at/after reopen, within 20 min (archived tolerance)
i0 = np.searchsorted(keys, base, side="left")
ok0 = (i0 < len(keys)) & (keys[np.clip(i0, 0, len(keys) - 1)] - base <= 20 * 60_000_000_000)
# exit: last print at/before window end, within 30 min (archived tolerance)
i1 = np.searchsorted(keys, endt, side="left") - 1
ok1 = (i1 >= 0) & (endt - keys[np.clip(i1, 0, len(keys) - 1)] <= 30 * 60_000_000_000)

rec = []
for k in range(len(sess)):
    if not (ok0[k] and ok1[k]) or i1[k] <= i0[k]:
        continue
    seg = px[i0[k]:i1[k] + 1]
    lr = np.log(seg / seg[0])
    rec.append((sess[k], float(lr[-1]), float(min(lr.min(), 0.0)),
                float(max(lr.max(), 0.0)), len(seg)))

df = pd.DataFrame(rec, columns=["date", "ret", "mae", "mfe", "nbars"]).set_index("date")
df = df[np.isfinite(df[["ret", "mae", "mfe"]].to_numpy()).all(axis=1)]

# ── reproduction gate ────────────────────────────────────────────────────────
prior = pd.read_csv(PRIOR_SERIES, index_col=0, parse_dates=True)["GOLD"].dropna()
common = df.index.intersection(prior.index)
lo, hi = df.loc[common, "ret"].quantile([0.005, 0.995])
unclipped = common[(df.loc[common, "ret"] > lo) & (df.loc[common, "ret"] < hi)]
d_unclipped = (df.loc[unclipped, "ret"] - prior.loc[unclipped]).abs().max()
d_all = (df.loc[common, "ret"] - prior.loc[common]).abs().max()
print(f"reproduction gate: n_common={len(common)}  max|diff| unclipped={d_unclipped:.3e} "
      f"(all={d_all:.3e})")
assert d_unclipped < 1e-9, "raw series does NOT reproduce the archived measurement"

df.to_csv(OUT / "step2_gold_window_path.csv", float_format="%.8g")

raw, wins = df["ret"], df["ret"].clip(lo, hi)
print(f"\nN={len(df)}  {df.index.min().date()} -> {df.index.max().date()}")
print(f"{'':14s}{'mean bps':>10s}{'sd bps':>10s}{'skew':>8s}{'kurt':>8s}{'min %':>9s}{'p01 %':>9s}")
for lab, s in (("ret RAW", raw), ("ret winsorised", wins), ("mae RAW", df["mae"])):
    print(f"{lab:14s}{s.mean()*1e4:10.3f}{s.std()*1e4:10.3f}{s.skew():8.2f}"
          f"{s.kurtosis():8.2f}{s.min()*100:9.2f}{s.quantile(.01)*100:9.2f}")
print(f"\nwhat the 0.5/99.5 clip hid: worst session {raw.min()*100:.2f}% -> "
      f"{wins.min()*100:.2f}%  |  sessions <= -1%: raw {int((raw<=-0.01).sum())}, "
      f"winsorised {int((wins<=-0.01).sum())}")
print(f"intraday penalty: median (mae - min(ret,0)) = "
      f"{(df['mae'] - df['ret'].clip(upper=0)).median()*1e4:.1f} bps; "
      f"p99 excursion {df['mae'].quantile(.01)*100:.2f}% vs p99 close {raw.quantile(.01)*100:.2f}%")
print(f"nbars median {df.nbars.median():.0f}  p01 {df.nbars.quantile(.01):.0f}")
