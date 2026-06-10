"""
fx_data.py — intraday FX/CFD data access for the FTMO alpha program
=====================================================================

Two sources, both 1-minute, UTC:
  - MT5 panel  : data/panels/m5_indices/<SYM>_M1.csv  (has a realised `spread`
                 column → FTMO-faithful; EURUSD/indices/metals, to 2026).
  - Dukascopy  : data/raw/dukascopy_<SYM>_2020_2024.parquet (mid OHLCV, no spread;
                 independent feed → cross-check against MT5 artefacts).

Provides causal resampling to a working frequency, a liquid-hours session filter
(avoids the 21:00-22:00 UTC rollover spread blow-out and thin late-Asia), and a
helper to aggregate a per-bar return series into clean daily returns.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
PANEL = REPO / "data" / "panels" / "m5_indices"
RAW = REPO / "data" / "raw"


def load_mt5_panel(symbol: str, start: str | None = None,
                   end: str | None = None) -> pd.DataFrame:
    """Load an MT5 1-min panel with OHLC + spread (points). UTC index, deduped, sorted."""
    p = PANEL / f"{symbol}_M1.csv"
    df = pd.read_csv(p)
    df["ts"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S",
                              errors="coerce")
    df = (df.dropna(subset=["ts"]).set_index("ts").sort_index()
            [["open", "high", "low", "close", "tick_volume", "spread"]])
    df = df[~df.index.duplicated(keep="first")]
    if start:
        df = df.loc[start:]
    if end:
        df = df.loc[:end]
    return df


def load_dukascopy(symbol: str, start: str | None = None,
                   end: str | None = None) -> pd.DataFrame:
    """Load Dukascopy 1-min mid OHLCV (no spread). UTC index."""
    p = RAW / f"dukascopy_{symbol}_2020_2024.parquet"
    df = pd.read_parquet(p)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert("UTC").tz_localize(None)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    if start:
        df = df.loc[start:]
    if end:
        df = df.loc[:end]
    return df


def resample_ohlc(df: pd.DataFrame, freq: str = "5min") -> pd.DataFrame:
    """Causal OHLC(+spread mean, volume sum) resample; empty (weekend) bars dropped."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "spread" in df.columns:
        agg["spread"] = "mean"
    if "tick_volume" in df.columns:
        agg["tick_volume"] = "sum"
    elif "volume" in df.columns:
        agg["volume"] = "sum"
    out = df.resample(freq, label="right", closed="right").agg(agg)
    return out.dropna(subset=["close"])


def session_filter(df: pd.DataFrame, start_hour: int = 7, end_hour: int = 20,
                   drop_weekend: bool = True) -> pd.DataFrame:
    """
    Keep liquid hours [start_hour, end_hour) UTC (London + NY), Mon-Fri.
    Excludes the 21:00-22:00 UTC rollover (spread blow-out) and thin late Asia.
    """
    h = df.index.hour
    mask = (h >= start_hour) & (h < end_hour)
    if drop_weekend:
        mask &= df.index.dayofweek < 5
    return df[mask]


def to_daily_returns(bar_ret: pd.Series) -> pd.Series:
    """Aggregate an intraday per-bar (additive) return series into daily returns."""
    return bar_ret.groupby(bar_ret.index.normalize()).sum().rename("daily_ret")
