"""Cache the M1 series both tests need, RAW (no winsorisation anywhere).

Reads READ-ONLY from the main working dir: caches are gitignored and therefore
absent from a fresh worktree.  Writes only to the scratchpad given as argv[1].
No data blob ever enters git.

Also emits the L60 hygiene table (zero-range bars per series per year) and the
L56 clock falsification (winter~summer hourly-vol profile correlation, exchange
clock vs UTC).  Both are N0 diagnostics: they measure no performance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc")
CACHE = Path(sys.argv[1])
CACHE.mkdir(parents=True, exist_ok=True)

# instrument -> exchange tz used for its session clock (L56)
SERIES = {
    "US500": "America/New_York",
    "US100": "America/New_York",
    "US30": "America/New_York",
    "GER40": "Europe/Berlin",
    "XAUUSD": "America/New_York",   # CME Globex reopen 18:00 ET
    "XAGUSD": "America/New_York",
    "USOIL": "America/New_York",
}


def load_m1(name: str) -> pd.DataFrame:
    df = pd.read_csv(
        RAW / f"{name}_M1.csv",
        usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
        dtype={"open": "float64", "high": "float64", "low": "float64",
               "close": "float64", "spread": "float32"},
    )
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    df.index.name = "ts"
    return df.sort_index()


def hour_profile_corr(df: pd.DataFrame, tz: str) -> float:
    """L56: corr of the winter vs summer hourly |return| profile in a given clock."""
    idx = df.index.tz_convert(tz)
    r = (df["close"].pct_change().abs() * 1e4).to_numpy()
    m = idx.month.to_numpy()
    h = idx.hour.to_numpy()
    win, sm = np.isin(m, [12, 1, 2]), np.isin(m, [6, 7, 8])
    a = pd.Series(r[win]).groupby(pd.Series(h[win])).mean()
    b = pd.Series(r[sm]).groupby(pd.Series(h[sm])).mean()
    j = pd.concat([a, b], axis=1).dropna()
    return float(j.iloc[:, 0].corr(j.iloc[:, 1]))


if __name__ == "__main__":
    hyg, clk = [], []
    for name, tz in SERIES.items():
        df = load_m1(name)
        df.to_parquet(CACHE / f"{name}_M1.parquet")
        zr = (df["high"] == df["low"])
        frozen = zr & (df["close"] == df["open"])
        by_year = pd.DataFrame({
            "zero_range_pct": 100 * zr.groupby(df.index.year).mean(),
            "frozen_pct": 100 * frozen.groupby(df.index.year).mean(),
            "spread_zero_pct": 100 * df["spread"].eq(0).groupby(df.index.year).mean(),
        })
        by_year.insert(0, "instr", name)
        hyg.append(by_year.reset_index().rename(columns={"ts": "year"}))
        for label, t in (("EXCH", tz), ("UTC", "UTC")):
            clk.append(dict(instr=name, clock=label, tz=t,
                            corr=hour_profile_corr(df, t)))
        print(f"{name:7s} rows={len(df):>10,}  "
              f"{df.index.min().date()}..{df.index.max().date()}  "
              f"zero-range worst yr={by_year['zero_range_pct'].max():.2f}%")

    H = pd.concat(hyg, ignore_index=True)
    H.to_csv(CACHE / "l60_hygiene.csv", index=False)
    C = pd.DataFrame(clk)
    C.to_csv(CACHE / "l56_clock.csv", index=False)
    print("\n=== L56 clock falsification (winter~summer hourly profile corr) ===")
    print(C.pivot(index="instr", columns="clock", values="corr").round(3).to_string())
