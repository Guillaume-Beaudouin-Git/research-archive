"""
Data loaders for the 8-strategy FTMO rigorous test.

Datasets:
- US500/US100/GER40/UK100 intraday M1
- EURUSD/USDJPY M5 (Forex/data/cache/dukascopy_m5 + data/ftmo_research)
- VIX D1
"""
from __future__ import annotations

import glob
import os
import pandas as pd
import numpy as np


M5_INDICES_DIR = "<HOME>/Desktop/Algo_claude/data/panels/m5_indices"
DUKAS_M5_DIR = "<HOME>/Desktop/Algo_claude/Forex/data/cache/dukascopy_m5"
FTMO_RESEARCH_DIR = "<HOME>/Desktop/Algo_claude/data/ftmo_research"
VIX_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix.csv"


def _parse_dukas_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize index to UTC datetime."""
    if isinstance(df.index, pd.DatetimeIndex):
        return df.sort_index()
    if "timestamp_utc" in df.columns:
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
        df = df.dropna(subset=["timestamp_utc"]).set_index("timestamp_utc")
    return df.sort_index()


def load_index_m1(symbol: str) -> pd.DataFrame:
    """Load M1 index data. symbol in {US500, US100, US30, GER40}."""
    path = f"{M5_INDICES_DIR}/{symbol}_M1.csv"
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    df = _parse_dukas_timestamp(df)
    return df[["open", "high", "low", "close"]]


def load_index_daily(symbol: str) -> pd.DataFrame:
    """Load daily OHLC for an index by resampling M1 to D1 UTC."""
    df = load_index_m1(symbol)
    daily = df.resample("1D").agg({"open": "first", "high": "max",
                                   "low": "min", "close": "last"}).dropna()
    return daily


def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with tz-naive DatetimeIndex (UTC-localized → naive)."""
    if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
        df = df.copy()
        df.index = df.index.tz_convert("UTC").tz_localize(None)
    return df


def load_uk100_m5() -> pd.DataFrame:
    """Load UK100 M5 from Dukascopy parquet files."""
    files = sorted(glob.glob(f"{DUKAS_M5_DIR}/UK100_*_M5.parquet"))
    if not files:
        return pd.DataFrame()
    parts = [pd.read_parquet(p) for p in files]
    df = pd.concat(parts).sort_index()
    df.index = pd.to_datetime(df.index)
    df = _strip_tz(df)
    df = df[~df.index.duplicated(keep="first")]
    return df


def load_eurusd_m5() -> pd.DataFrame:
    """EURUSD M5 — prefer ftmo_research 2020-2026 parquet."""
    p = f"{FTMO_RESEARCH_DIR}/EURUSD_m5.parquet"
    if os.path.exists(p):
        df = pd.read_parquet(p)
        df.index = pd.to_datetime(df.index)
        df = _strip_tz(df)
        return df.sort_index()
    return pd.DataFrame()


def load_usdjpy_m5() -> pd.DataFrame:
    """USDJPY M5 — Dukascopy parquet files if present, else M1 CSV fallback."""
    files = sorted(glob.glob(f"{DUKAS_M5_DIR}/USDJPY_*_M5.parquet"))
    if not files:
        p1 = f"{M5_INDICES_DIR}/USDJPY_M1.csv"
        if os.path.exists(p1):
            df = pd.read_csv(p1)
            df = _parse_dukas_timestamp(df)
            df = _strip_tz(df)
            return df[["open", "high", "low", "close"]]
        return pd.DataFrame()
    parts = [pd.read_parquet(p) for p in files]
    df = pd.concat(parts).sort_index()
    df.index = pd.to_datetime(df.index)
    df = _strip_tz(df)
    return df[~df.index.duplicated(keep="first")]


def load_fx_daily(pair: str) -> pd.DataFrame:
    """Load FX pair as daily — resample from M1 if needed."""
    p1 = f"{M5_INDICES_DIR}/{pair}_M1.csv"
    if os.path.exists(p1):
        df = pd.read_csv(p1)
        df = _parse_dukas_timestamp(df)
        df = df[["open", "high", "low", "close"]]
        daily = df.resample("1D").agg({"open": "first", "high": "max",
                                       "low": "min", "close": "last"}).dropna()
        return daily
    return pd.DataFrame()


def load_vix() -> pd.DataFrame:
    """Load VIX daily."""
    df = pd.read_csv(VIX_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()
    return df


def utc_to_et_hour(ts_utc: pd.Series) -> pd.Series:
    """Convert UTC timestamp to US/Eastern hour, naive (handles DST roughly)."""
    return (ts_utc - pd.Timedelta(hours=5)).dt.hour  # rough EST; for backtest filter precision


def utc_to_et(ts: pd.Timestamp) -> pd.Timestamp:
    return ts - pd.Timedelta(hours=5)
