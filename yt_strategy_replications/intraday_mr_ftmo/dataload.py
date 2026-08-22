"""
Data loader for the intraday-MR FTMO study.

Resamples the repo's canonical true-UTC deep_history M1 series to intraday bars,
filters to a liquid session window, carries the calibrated `spread` column, and
caches per-instrument parquet. Memory-safe single-pass read.

Session windows (UTC, pre-registered):
  indices US100/US500/US30/GER40 : 13:30-20:00 (US cash overlap; all index CFDs liquid)
  FX EURUSD/GBPUSD/USDJPY        : 07:00-16:00 (London/NY overlap)
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                      # .../Algo_claude
DEEP = REPO / "data" / "deep_history_utc"
CACHE = HERE / "_cache"
CACHE.mkdir(exist_ok=True)

INDICES = ["US100", "US500", "US30", "GER40"]
FX = ["EURUSD", "GBPUSD", "USDJPY"]
ALL = INDICES + FX

# MT5 digits per instrument (point size = 10**-digits) for spread->price conversion.
DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2,
          "EURUSD": 5, "GBPUSD": 5, "USDJPY": 3}

SESSION = {s: ("13:30", "20:00") for s in INDICES}
SESSION.update({s: ("07:00", "16:00") for s in FX})


def _session_mask(idx: pd.DatetimeIndex, start: str, end: str) -> np.ndarray:
    t = idx.time
    s = pd.Timestamp(start).time(); e = pd.Timestamp(end).time()
    return (t >= s) & (t < e)


def build(symbol: str, bar: str = "15min", force: bool = False) -> pd.DataFrame:
    out = CACHE / f"{symbol}_{bar}.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    usecols = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"]
    df = pd.read_csv(DEEP / f"{symbol}_M1.csv", usecols=usecols,
                     dtype={"open": "float64", "high": "float64", "low": "float64",
                            "close": "float64", "tick_volume": "float64", "spread": "float64"})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"])
    agg = (df.resample(bar)
             .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                   "tick_volume": "sum", "spread": "mean"})
             .dropna(subset=["open", "high", "low", "close"]))
    st, en = SESSION[symbol]
    agg = agg[_session_mask(agg.index, st, en)].copy()
    # spread in bps of price (point size * spread_points / price)
    pt = 10.0 ** (-DIGITS[symbol])
    agg["spread_bps"] = (agg["spread"] * pt) / agg["close"] * 1e4
    agg["session_date"] = agg.index.normalize()
    agg.to_parquet(out)
    return agg


def load(symbol: str, bar: str = "15min", start=None, end=None) -> pd.DataFrame:
    df = build(symbol, bar)
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


if __name__ == "__main__":
    force = "--force" in sys.argv
    print(f"{'sym':7} {'bars':>9} {'from':>12} {'to':>12} {'bars/day':>9} "
          f"{'med_spr_bps':>11} {'p90_spr_bps':>11} {'med|ret|bps':>11}")
    for s in ALL:
        df = build(s, force=force)
        rng = df.index
        bpd = df.groupby("session_date").size()
        ret = (df["close"] / df["open"] - 1.0).abs() * 1e4
        print(f"{s:7} {len(df):>9} {str(rng.min().date()):>12} {str(rng.max().date()):>12} "
              f"{bpd.median():>9.0f} {df['spread_bps'].median():>11.3f} "
              f"{df['spread_bps'].quantile(0.90):>11.3f} {ret.median():>11.2f}")
