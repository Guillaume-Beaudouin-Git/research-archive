"""TEST B, addendum 2 — intra-window ADVERSE EXCURSION as a function of entry delay.

Motivation (imposed constraint, 2026-08-02): 80.2 % of this book's deaths are breaches
of the FTMO -5 % DAILY barrier, which is enforced on EQUITY, not on the close.  So if a
sub-window turns out to be executable, what decides is the intra-day PATH, not the Sharpe.

This measures, RAW on M1 (no winsorisation anywhere), the maximum adverse excursion of a
LONG position opened d minutes after the first executable print and held to the window end.
It answers a question the delay ladder cannot: does entering later ALSO buy a smaller tail?

No p(pass) is computed here and none is claimed: a p(pass) would require the
autocorrelation-matched circular-shift placebo, which is out of this mandate's scope.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(sys.argv[1])
OUT = CACHE / "testB"
REOPEN_ET, WINDOW_HOURS = 18, 8
DELAYS = (0, 5, 10, 15, 30)
NS_MIN = np.int64(60_000_000_000)

df = pd.read_parquet(CACHE / "XAUUSD_M1.parquet")
keys = df.index.asi8
close = df["close"].to_numpy()
low = df["low"].to_numpy()
high = df["high"].to_numpy()

et = df.index.tz_convert("America/New_York")
sess = pd.DatetimeIndex(np.unique(et.normalize().tz_localize(None)))
reopen = (sess + pd.Timedelta(hours=REOPEN_ET)).tz_localize(
    "America/New_York", nonexistent="shift_forward", ambiguous=True).tz_convert("UTC")
base = reopen.asi8

i0 = np.searchsorted(keys, base, "left")
ok = (i0 < len(keys)) & ((keys[np.clip(i0, 0, len(keys) - 1)] - base) <= 60 * NS_MIN)
t0 = np.where(ok, keys[np.clip(i0, 0, len(keys) - 1)], base)

rows = []
for k in range(len(sess)):
    if not ok[k]:
        continue
    end = t0[k] + WINDOW_HOURS * 60 * NS_MIN
    r = dict(day=sess[k], year=sess[k].year)
    for d in DELAYS:
        s = t0[k] + d * NS_MIN
        a = np.searchsorted(keys, s, "left")
        b = np.searchsorted(keys, end, "right")
        if b - a < 60 or a >= len(keys):
            r[f"mae{d}"] = np.nan
            r[f"ret{d}"] = np.nan
            continue
        p = close[a]
        r[f"mae{d}"] = (low[a:b].min() / p - 1.0) * 1e4      # worst adverse move, LONG
        r[f"mfe{d}"] = (high[a:b].max() / p - 1.0) * 1e4
        r[f"ret{d}"] = (close[b - 1] / p - 1.0) * 1e4
    rows.append(r)

E = pd.DataFrame(rows).set_index("day")
E.to_parquet(OUT / "b_excursion.parquet")
pd.set_option("display.width", 240, "display.max_columns", 40)

print("=== B · intra-window adverse excursion by entry delay (RAW M1, LONG) ===")
out = []
for lab, g in (("full", E), ("post2021", E[E.year >= 2021])):
    for d in DELAYS:
        m = g[f"mae{d}"].dropna()
        out.append(dict(sample=lab, delay=d, n=len(m), mean_mae=m.mean(),
                        med_mae=m.median(), p05_mae=m.quantile(0.05),
                        p01_mae=m.quantile(0.01), worst_mae=m.min(),
                        mean_ret=g[f"ret{d}"].mean(),
                        frac_mae_lt_100bp=(m < -100).mean(),
                        frac_mae_lt_200bp=(m < -200).mean()))
O = pd.DataFrame(out)
O.to_csv(OUT / "b_excursion_summary.csv", index=False)
print(O.round(2).to_string(index=False))

print("\n--- what a -5 % DAILY equity barrier implies, by notional multiplier vm ---")
print("   (share of sessions whose intra-window excursion alone would breach -5 %)")
br = []
for lab, g in (("full", E), ("post2021", E[E.year >= 2021])):
    for d in DELAYS:
        m = g[f"mae{d}"].dropna()
        row = dict(sample=lab, delay=d, n=len(m))
        for vm in (2, 5, 10, 14):
            row[f"vm{vm}"] = 100 * (m * vm / 1e4 < -0.05).mean()
        br.append(row)
B = pd.DataFrame(br)
B.to_csv(OUT / "b_excursion_barrier.csv", index=False)
print(B.round(3).to_string(index=False))

print("\n--- winsorisation check on the EXCURSION (what the inherited chain truncated) ---")
for lab, g in (("full", E), ("post2021", E[E.year >= 2021])):
    for d in (0, 15):
        m = g[f"mae{d}"].dropna()
        mw = m.clip(*m.quantile([0.005, 0.995]))
        print(f"{lab:9s} d={d:2d}  raw worst {m.min():9.1f} bps | winsorised worst "
              f"{mw.min():9.1f} bps | raw kurtosis {m.kurtosis():7.2f} -> {mw.kurtosis():6.2f}")
