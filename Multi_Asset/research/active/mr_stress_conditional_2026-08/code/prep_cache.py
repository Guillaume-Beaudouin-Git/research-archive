"""Cache `deep_history_utc` M1 index series to parquet (true UTC) + L60 / L56 hygiene.

Reads READ-ONLY from the main working dir (caches are gitignored -> absent from a
worktree).  Writes only to the scratchpad.  No data blob ever enters git.

Hygiene run BEFORE any use of the series, per mandate:
  L60 - share of zero-range bars (high == low), per series and per year.
  L56 - hourly |return| profile correlation winter~summer, exchange clock vs UTC.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc")
VIX = Path("<HOME>/Desktop/Algo_claude/data/panels/vix.csv")
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./cache")
CACHE.mkdir(parents=True, exist_ok=True)

INSTR = ["US500", "US100", "US30", "GER40"]
TZ = {"US500": "America/New_York", "US100": "America/New_York",
      "US30": "America/New_York", "GER40": "Europe/Berlin"}


def load_m1(name: str) -> pd.DataFrame:
    df = pd.read_csv(
        RAW / f"{name}_M1.csv",
        usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
        dtype={"open": "float32", "high": "float32", "low": "float32",
               "close": "float32", "spread": "float32"},
    )
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    df.index.name = "ts"
    return df.sort_index()


def hour_profile(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    idx = df.index.tz_convert(tz)
    r = df["close"].pct_change().abs() * 1e4
    m, h = idx.month, idx.hour
    win, sum_ = np.isin(m, [12, 1, 2]), np.isin(m, [6, 7, 8])
    return pd.DataFrame({
        "winter": pd.Series(r.values[win]).groupby(pd.Series(h[win])).mean(),
        "summer": pd.Series(r.values[sum_]).groupby(pd.Series(h[sum_])).mean(),
    })


if __name__ == "__main__":
    hyg, zr_rows = [], []
    for name in INSTR:
        df = load_m1(name)
        df.to_parquet(CACHE / f"{name}_M1.parquet")
        print(f"\n=== {name} === rows={len(df):,}  span={df.index.min()}..{df.index.max()}")

        # ---- L60: zero-range share, per year (whole series and RTH only) ----
        idx = df.index.tz_convert(TZ[name])
        mod = idx.hour * 60 + idx.minute
        om, cl = (9 * 60, 17 * 60 + 30) if name == "GER40" else (9 * 60 + 30, 16 * 60)
        rth = (mod >= om) & (mod < cl) & (idx.dayofweek < 5)
        zr_all = (df["high"] == df["low"]).groupby(idx.year).mean() * 100
        zr_rth = (df["high"] == df["low"])[rth].groupby(idx[rth].year).mean() * 100
        print("L60 zero-range %% by year  [all-hours | RTH]:")
        for y in sorted(set(zr_all.index) & set(zr_rth.index)):
            print(f"   {y}: {zr_all[y]:6.2f} | {zr_rth[y]:6.2f}")
            zr_rows.append(dict(instr=name, year=int(y), zr_all=zr_all[y], zr_rth=zr_rth[y]))
        sp0 = df["spread"].eq(0).groupby(idx.year).mean() * 100
        print("spread==0 %% by year (NOT used as a cost, reported for the record): "
              + " ".join(f"{y}:{v:.0f}" for y, v in sp0.items()))

        # ---- L56: exchange-clock anchoring ----
        for clock, tzz in [("EXCH", TZ[name]), ("UTC", "UTC")]:
            hp = hour_profile(df, tzz).dropna()
            c = float(hp["winter"].corr(hp["summer"]))
            print(f"L56 hourly-vol profile corr winter~summer, {clock:4s} clock: {c:.3f}")
            hyg.append(dict(instr=name, clock=clock, corr=c))

    pd.DataFrame(hyg).to_csv(CACHE / "clock_check.csv", index=False)
    pd.DataFrame(zr_rows).to_csv(CACHE / "zero_range.csv", index=False)

    # ---- VIX (state proxy P1) ----
    v = pd.read_csv(VIX, parse_dates=["Date"]).rename(columns={"^VIX": "vix"})[["Date", "vix"]]
    v = v.dropna().sort_values("Date").reset_index(drop=True)
    v.to_parquet(CACHE / "vix.parquet")
    print(f"\n=== VIX === rows={len(v)} span={v.Date.min().date()}..{v.Date.max().date()} "
          f"nan={v.vix.isna().sum()}")
