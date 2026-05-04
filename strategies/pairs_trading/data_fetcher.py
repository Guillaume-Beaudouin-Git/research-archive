"""
Hourly OHLCV data fetcher for pairs trading universe.

Fetches 18 months of hourly data from yfinance for Hyperliquid-listed perps.
Caches to CSV to avoid re-downloading. Split into train (first 12m) / test (last 6m).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Universe: Hyperliquid perp symbols → yfinance tickers
# ---------------------------------------------------------------------------

HYPERLIQUID_UNIVERSE: dict[str, str] = {
    "BTC":   "BTC-USD",
    "ETH":   "ETH-USD",
    "SOL":   "SOL-USD",
    "AVAX":  "AVAX-USD",
    "BNB":   "BNB-USD",
    "MATIC": "MATIC-USD",
    "ARB":   "ARB-USD",
    "OP":    "OP-USD",
    "LINK":  "LINK-USD",
    "ATOM":  "ATOM-USD",
    "DOT":   "DOT-USD",
    "NEAR":  "NEAR-USD",
    "APT":   "APT-USD",
    "SUI":   "SUI-USD",
    "INJ":   "INJ-USD",
    "TIA":   "TIA-USD",
    "SEI":   "SEI-USD",
    "AAVE":  "AAVE-USD",
    "UNI":   "UNI-USD",
    "LDO":   "LDO-USD",
    "ENA":   "ENA-USD",
    "DOGE":  "DOGE-USD",
    "ADA":   "ADA-USD",
}

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CACHE_FILE = DATA_DIR / "pairs_universe_hourly.csv"

# 18-month lookback from today
LOOKBACK_DAYS = 548   # ~18 months
TRAIN_MONTHS = 12
TEST_MONTHS = 6


def fetch_symbol_hourly(sym: str, ticker: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame | None:
    """Download hourly OHLCV for one symbol. Returns None on failure or insufficient history."""
    try:
        # yfinance hourly max is 730 days; we chunk if needed
        raw = yf.download(
            ticker,
            start=start_dt.strftime("%Y-%m-%d"),
            end=end_dt.strftime("%Y-%m-%d"),
            interval="1h",
            auto_adjust=True,
            progress=False,
        )
    except Exception as exc:
        print(f"  [{sym}] download error: {exc}")
        return None

    if raw is None or raw.empty:
        print(f"  [{sym}] no data returned")
        return None

    # Flatten MultiIndex columns if present
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0].lower() for c in raw.columns]
    else:
        raw.columns = [c.lower() for c in raw.columns]

    needed = {"open", "high", "low", "close", "volume"}
    if not needed.issubset(set(raw.columns)):
        print(f"  [{sym}] missing columns: {needed - set(raw.columns)}")
        return None

    df = raw[["open", "high", "low", "close", "volume"]].copy()
    df.index = pd.to_datetime(df.index, utc=True).floor("h")
    df.index.name = "timestamp"
    df["symbol"] = sym
    df = df.reset_index()

    # Drop rows where close is NaN or zero
    df = df[df["close"] > 0].dropna(subset=["close"])

    print(f"  [{sym}] {len(df)} hourly bars  ({df['timestamp'].min().date()} – {df['timestamp'].max().date()})")
    return df


def build_universe_csv(force_refresh: bool = False) -> pd.DataFrame:
    """Download hourly data for entire universe and cache to CSV."""
    DATA_DIR.mkdir(exist_ok=True)

    if CACHE_FILE.exists() and not force_refresh:
        print(f"Loading cached data from {CACHE_FILE}")
        df = pd.read_csv(CACHE_FILE, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df

    end_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_dt = end_dt - timedelta(days=LOOKBACK_DAYS)

    print(f"Fetching hourly data: {start_dt.date()} → {end_dt.date()}")
    all_dfs = []

    for sym, ticker in HYPERLIQUID_UNIVERSE.items():
        df = fetch_symbol_hourly(sym, ticker, start_dt, end_dt)
        if df is not None:
            all_dfs.append(df)
        time.sleep(0.5)   # be nice to yfinance

    if not all_dfs:
        raise RuntimeError("No data fetched — check network / yfinance.")

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    combined.to_csv(CACHE_FILE, index=False)
    print(f"\nSaved {len(combined)} rows to {CACHE_FILE}")
    return combined


def get_train_test_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split universe into train (first 12m) and test (last 6m) by timestamp."""
    timestamps = df["timestamp"].sort_values()
    t_min = timestamps.min()
    t_max = timestamps.max()
    total_days = (t_max - t_min).days
    print(f"Data range: {t_min.date()} → {t_max.date()} ({total_days} days)")

    # Split at 12-month mark from start
    split_ts = t_min + timedelta(days=365)
    train = df[df["timestamp"] < split_ts].copy()
    test = df[df["timestamp"] >= split_ts].copy()

    print(f"Train: {train['timestamp'].min().date()} → {train['timestamp'].max().date()} "
          f"({len(train)} rows, {train['symbol'].nunique()} symbols)")
    print(f"Test:  {test['timestamp'].min().date()} → {test['timestamp'].max().date()} "
          f"({len(test)} rows, {test['symbol'].nunique()} symbols)")
    return train, test


def pivot_close(df: pd.DataFrame) -> pd.DataFrame:
    """Return wide DataFrame: timestamp × symbol → close price."""
    wide = df.pivot_table(index="timestamp", columns="symbol", values="close", aggfunc="last")
    wide = wide.sort_index()
    return wide


def pivot_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Return wide DataFrame: timestamp × symbol → volume (USD)."""
    # volume in native units; multiply by close to get USD volume
    df = df.copy()
    df["vol_usd"] = df["volume"] * df["close"]
    wide = df.pivot_table(index="timestamp", columns="symbol", values="vol_usd", aggfunc="last")
    return wide.sort_index()
