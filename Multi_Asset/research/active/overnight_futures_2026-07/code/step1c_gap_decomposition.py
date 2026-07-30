"""Step 1c — is the reopen-hour drift CAPTURABLE, or is it the settlement-halt GAP?

The whole edge sits in the first hour after the CME reopen (18:00 ET metals/energy,
20:00 ET grains). CME halts 17:00-18:00 ET. On M1 we separate, per session:

  gap            = log(first print at/after reopen / last print before the halt)
  hour1_cap      = log(price 1h after reopen / first print at/after reopen)
  window_cap     = log(price at window end   / first print at/after reopen)   <- TRADABLE
  window_incl_gap= log(price at window end   / last print before the halt)    <- what the
                    archived H1 study measures whenever the halt hour is unquoted

A gap is not tradable: the market is closed. If the archived edge is mostly gap,
the CFD -> futures transfer is void.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import OUT, REPO, SLEEVES, hac_t, sharpe, us_dst

CACHE = OUT.parent / "code" / "_m1cache"
CACHE.mkdir(exist_ok=True)

WINDOW_HOURS = {"GOLD": 8, "SILVER": 8, "WTI": 8, "SOYBEAN": 6}
REOPEN_ET = {"GOLD": 18, "SILVER": 18, "WTI": 18, "SOYBEAN": 20}


def load_m1(cfd: str, start: str) -> pd.DataFrame:
    f = CACHE / f"{cfd}_m1.parquet"
    if f.exists():
        return pd.read_parquet(f)
    src = REPO / "data" / "deep_history_utc" / f"{cfd}_M1.csv"
    parts = []
    for ch in pd.read_csv(src, usecols=["timestamp_utc", "close"], chunksize=2_000_000):
        ts = pd.to_datetime(ch["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
        d = pd.DataFrame({"ts": ts, "close": ch["close"].astype("float64")})
        d = d[d["ts"] >= pd.Timestamp(start)]
        if len(d):
            parts.append(d)
    df = pd.concat(parts, ignore_index=True).sort_values("ts").reset_index(drop=True)
    df.to_parquet(f)
    return df


def price_at(vals, keys, t, mode, max_gap_min):
    """mode='last'  : last print strictly before t, within max_gap_min minutes.
       mode='first' : first print at/after t, within max_gap_min minutes."""
    tol = np.int64(max_gap_min) * np.int64(60_000_000_000)
    if mode == "last":
        i = np.searchsorted(keys, t, side="left") - 1
        ok = (i >= 0) & (t - keys[np.clip(i, 0, len(keys) - 1)] <= tol)
    else:
        i = np.searchsorted(keys, t, side="left")
        ok = (i < len(keys)) & (keys[np.clip(i, 0, len(keys) - 1)] - t <= tol)
    i = np.clip(i, 0, len(keys) - 1)
    out = vals[i].astype(float)
    out[~ok] = np.nan
    return out


rows, detail = [], []
H = np.int64(3_600_000_000_000)

for name, sp in SLEEVES.items():
    df = load_m1(sp["cfd"], sp["sample_start"])
    ts = pd.DatetimeIndex(df["ts"])
    dst = us_dst(ts)
    et = ts - pd.to_timedelta(np.where(dst, 4, 5), unit="h")     # US Eastern wall clock
    keys = et.asi8
    vals = df["close"].to_numpy()

    ro, hours = REOPEN_ET[name], WINDOW_HOURS[name]
    sessions = pd.DatetimeIndex(np.unique(pd.DatetimeIndex(et).normalize()))
    base = (sessions + pd.Timedelta(hours=ro)).asi8

    p_pre = price_at(vals, keys, base - H, "last", 60)     # last print in 16:00-17:00 ET
    p_open = price_at(vals, keys, base, "first", 20)       # first print at/after reopen
    p_h1 = price_at(vals, keys, base + H, "last", 20)
    p_end = price_at(vals, keys, base + hours * H, "last", 30)
    halt_n = (np.searchsorted(keys, base, "left") - np.searchsorted(keys, base - H, "left"))

    o = pd.DataFrame(dict(gap=np.log(p_open / p_pre), hour1_cap=np.log(p_h1 / p_open),
                          window_cap=np.log(p_end / p_open),
                          window_incl_gap=np.log(p_end / p_pre), halt_bars=halt_n),
                     index=sessions).dropna()
    num = ["gap", "hour1_cap", "window_cap", "window_incl_gap"]
    o = o[np.isfinite(o[num].to_numpy(dtype=float)).all(axis=1)]
    for c in num:                                  # winsorise as the source studies do
        lo, hi = o[c].quantile([0.005, 0.995])
        o[c] = o[c].clip(lo, hi)

    d = us_dst(o.index)
    for regime, m in (("all", np.ones(len(o), bool)), ("winter", ~d), ("summer", d)):
        s = o[m]
        if len(s) < 100:
            continue
        r = dict(sleeve=name, dst=regime, N=len(s),
                 halt_quoted_frac=round(float((s["halt_bars"] > 5).mean()), 3),
                 gap_bps=round(1e4 * s["gap"].mean(), 2),
                 hour1_cap_bps=round(1e4 * s["hour1_cap"].mean(), 2),
                 window_cap_bps=round(1e4 * s["window_cap"].mean(), 2),
                 window_incl_gap_bps=round(1e4 * s["window_incl_gap"].mean(), 2))
        r["gap_share_pct"] = (round(100 * r["gap_bps"] / r["window_incl_gap_bps"], 1)
                              if r["window_incl_gap_bps"] > 0 else np.nan)
        r["t_gap"] = round(hac_t(s["gap"])[1], 2)
        r["t_window_cap"] = round(hac_t(s["window_cap"])[1], 2)
        r["SR_window_cap"] = round(sharpe(s["window_cap"]), 3)
        r["SR_window_incl_gap"] = round(sharpe(s["window_incl_gap"]), 3)
        rows.append(r)
    o.insert(0, "sleeve", name)
    detail.append(o)

res = pd.DataFrame(rows)
pd.set_option("display.width", 260, "display.max_columns", 40)
print(res.to_string(index=False))
res.to_csv(OUT / "step1c_gap_decomposition.csv", index=False)
pd.concat(detail).to_csv(OUT / "step1c_daily_series.csv")
