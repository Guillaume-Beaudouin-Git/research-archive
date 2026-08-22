"""
data.py — Clean FX data loaders for the FTMO research project.

Design notes / data-quality decisions
--------------------------------------
* PRIMARY SOURCE = Dukascopy M1 bars (raw/dukascopy_<SYM>_2020_2024.parquet).
  Dukascopy is tick-derived, true-UTC, single broker -> internally consistent.
  EURUSD and GBPUSD from this source have a contemporaneous 15-min return
  correlation of 0.69 at lag 0 (and ~0 at every other lag), confirming the
  two series are properly time-synchronised.

* DO NOT mix the MT5 export (panels/m5_indices/EURUSD_M1.csv) with Dukascopy.
  The MT5 `timestamp_utc` column is actually broker server time (~UTC+3), not
  true UTC. Mixing it with Dukascopy GBPUSD produced a *spurious* ~0.006
  contemporaneous correlation and a fake "EUR/GBP relative-value edge" that
  was 100% a timestamp-misalignment artifact (see report, Section 3).
  The MT5 file is still useful for ONE thing: the realtime broker `spread`
  column, which we use to calibrate the cost model.

Temporal split (leak-free):
    TRAIN  2020-01-01 .. 2022-12-31   (hypothesis generation, parameter choice)
    VALID  2023-01-01 .. 2023-12-31   (model selection)
    OOS    2024-01-01 .. 2024-12-31   (single, final evaluation — lockbox)
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[2]          # .../Algo_claude/data
RAW = DATA_ROOT / "raw"

SPLITS = {
    "train": ("2020-01-01", "2022-12-31"),
    "valid": ("2023-01-01", "2023-12-31"),
    "oos":   ("2024-01-01", "2024-12-31"),
}


def load_m1(symbol: str) -> pd.DataFrame:
    """Load clean Dukascopy M1 OHLCV for a symbol, indexed by naive UTC."""
    path = RAW / f"dukascopy_{symbol}_2020_2024.parquet"
    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)            # store as naive UTC
    df = df[~df.index.duplicated()].sort_index()
    return df[["open", "high", "low", "close", "volume"]].astype("float64")


def resample_ohlc(df: pd.DataFrame, rule: str = "15min") -> pd.DataFrame:
    """Resample M1 OHLCV to a coarser bar. Right-labelled, no look-ahead."""
    out = df.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min",
         "close": "last", "volume": "sum"}
    ).dropna(subset=["open"])
    return out


def load(symbol: str, rule: str = "15min", split: str | None = None) -> pd.DataFrame:
    """Convenience: load + resample + optional split slice."""
    df = resample_ohlc(load_m1(symbol), rule)
    if split:
        lo, hi = SPLITS[split]
        df = df.loc[lo:hi]
    return df


if __name__ == "__main__":
    for sym in ("EURUSD", "GBPUSD"):
        d = load(sym, "15min")
        print(f"{sym}: {len(d):,} M15 bars  {d.index.min()} -> {d.index.max()}")
