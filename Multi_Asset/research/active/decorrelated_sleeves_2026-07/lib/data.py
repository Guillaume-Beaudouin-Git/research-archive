"""Cached bar loader over data/deep_history_utc M1 (TRUE UTC). Resamples once to parquet.

Daily bar  = UTC calendar day OHLCV (last M1 close = daily close).
Hourly bar = UTC hour OHLCV (for the intraday range piste).
"""
from __future__ import annotations
import os
import pandas as pd

REPO = "/sessions/zealous-zen-brahmagupta/mnt/Algo_claude"
RAW = os.path.join(REPO, "data/deep_history_utc")
CACHE = os.path.join(REPO, "Multi_Asset/research/active/decorrelated_sleeves_2026-07/cache")
os.makedirs(CACHE, exist_ok=True)

_COLS = ["timestamp_utc", "open", "high", "low", "close", "tick_volume"]
_AGG = {"open": "first", "high": "max", "low": "min", "close": "last", "tick_volume": "sum"}


def _resample(sym: str, rule: str) -> pd.DataFrame:
    path = os.path.join(RAW, f"{sym}_M1.csv")
    df = pd.read_csv(path, usecols=_COLS, engine="c")
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"]).set_index(ts)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype("float64")
    out = df.resample(rule).agg(_AGG).dropna(subset=["close"])
    out = out[out["tick_volume"] >= 0]
    return out


def load(sym: str, freq: str = "D", rebuild: bool = False) -> pd.DataFrame:
    """freq in {'D','H'}. Cached parquet. Returns OHLCV indexed by UTC timestamp."""
    rule = {"D": "1D", "H": "1h"}[freq]
    cpath = os.path.join(CACHE, f"{sym}_{freq}.pkl")
    if os.path.exists(cpath) and not rebuild:
        return pd.read_pickle(cpath)
    out = _resample(sym, rule)
    out.to_pickle(cpath)
    return out


def close_panel(syms, freq: str = "D") -> pd.DataFrame:
    """Aligned close panel (inner join on common timestamps)."""
    cols = {s: load(s, freq)["close"].rename(s) for s in syms}
    return pd.concat(cols.values(), axis=1, join="inner").dropna()


if __name__ == "__main__":
    import sys
    syms = sys.argv[1].split(",") if len(sys.argv) > 1 else ["US500"]
    freq = sys.argv[2] if len(sys.argv) > 2 else "D"
    for s in syms:
        d = load(s, freq, rebuild=True)
        print(f"{s} {freq}: {len(d):>7} bars  {d.index.min().date()} -> {d.index.max().date()}")
