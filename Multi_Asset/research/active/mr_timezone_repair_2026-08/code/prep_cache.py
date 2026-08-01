"""Cache deep_history_utc M1 index series to parquet (true UTC), + L60 / L56 hygiene.

Reads READ-ONLY from the main working dir (caches are gitignored, absent from worktrees).
Writes only to the scratchpad. No data blob ever enters git.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc")
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./cache")
CACHE.mkdir(parents=True, exist_ok=True)

INSTR = ["US500", "US100", "US30", "GER40"]


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


def zero_range_by_year(df: pd.DataFrame) -> pd.Series:
    """L60: share of bars with high == low (a settlement print is not a price)."""
    zr = (df["high"] == df["low"])
    return zr.groupby(df.index.year).mean()


def hour_profile(df: pd.DataFrame, tz: str) -> pd.DataFrame:
    """Mean |1-min return| by hour, split winter (Dec-Feb) vs summer (Jun-Aug).

    L56 falsification: an exchange-anchored effect keeps its shape in the EXCHANGE
    clock across DST and shifts by one hour in UTC.  Correlate both.
    """
    idx = df.index.tz_convert(tz)
    r = df["close"].pct_change().abs() * 1e4
    m = idx.month
    win = np.isin(m, [12, 1, 2])
    sum_ = np.isin(m, [6, 7, 8])
    h = idx.hour
    out = pd.DataFrame({
        "winter": pd.Series(r.values[win]).groupby(pd.Series(h[win])).mean(),
        "summer": pd.Series(r.values[sum_]).groupby(pd.Series(h[sum_])).mean(),
    })
    return out


if __name__ == "__main__":
    hyg = []
    for name in INSTR:
        df = load_m1(name)
        df.to_parquet(CACHE / f"{name}_M1.parquet")
        zr = zero_range_by_year(df)
        print(f"\n=== {name} === rows={len(df):,}  span={df.index.min()}..{df.index.max()}")
        print("L60 zero-range share by year (%):")
        print((zr * 100).round(2).to_string())
        print("spread==0 share by year (%):")
        print((df["spread"].eq(0).groupby(df.index.year).mean() * 100).round(1).to_string())
        tz = "Europe/Berlin" if name == "GER40" else "America/New_York"
        for clock, tzz in [("EXCH", tz), ("UTC", "UTC")]:
            hp = hour_profile(df, tzz).dropna()
            c = hp["winter"].corr(hp["summer"])
            print(f"L56 hourly-vol profile corr winter~summer in {clock:4s} clock ({tzz}): {c:.3f}")
            hyg.append(dict(instr=name, clock=clock, corr=c))
    pd.DataFrame(hyg).to_csv(CACHE / "clock_check.csv", index=False)
