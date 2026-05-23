"""
Fetch and cache Fear & Greed Index + BTC daily price for FGVD H1 analysis.

Sources:
  - Fear & Greed: alternative.me public API (no key, free, daily since 2018-02)
  - BTC price: CoinGecko free API (daily close, unlimited history)

Outputs (parquet, written to data/ relative to this file):
  - data/fg_raw.parquet      : date, value (int 0-100)
  - data/btc_price_raw.parquet : date, close (float USD)
  - data/merged.parquet      : date, fg, close, log_ret (aligned, no gaps)
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

FG_URL = "https://api.alternative.me/fng/?limit=0"

FG_CACHE = DATA_DIR / "fg_raw.parquet"
BTC_CACHE = DATA_DIR / "btc_price_raw.parquet"
MERGED_CACHE = DATA_DIR / "merged.parquet"


def fetch_fg() -> pd.DataFrame:
    """Fetch Fear & Greed daily index from alternative.me.

    Returns DataFrame with columns: date (DatetimeIndex), value (int).
    """
    if FG_CACHE.exists():
        df = pd.read_parquet(FG_CACHE)
        print(f"[FG] Loaded from cache: {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}")
        return df

    print("[FG] Fetching from alternative.me …")
    resp = requests.get(FG_URL, timeout=30)
    resp.raise_for_status()
    records = resp.json()["data"]

    rows = []
    for r in records:
        ts = int(r["timestamp"])
        date = pd.Timestamp(ts, unit="s").normalize()
        value = int(r["value"])
        rows.append({"date": date, "value": value})

    df = (
        pd.DataFrame(rows)
        .drop_duplicates("date")
        .set_index("date")
        .sort_index()
    )
    df.index = pd.DatetimeIndex(df.index)
    df.to_parquet(FG_CACHE)
    print(f"[FG] Fetched {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}")
    return df


def fetch_btc() -> pd.DataFrame:
    """Fetch BTC daily close from Yahoo Finance (BTC-USD).

    Returns DataFrame with columns: date (DatetimeIndex), close (float).
    """
    if BTC_CACHE.exists():
        df = pd.read_parquet(BTC_CACHE)
        print(f"[BTC] Loaded from cache: {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}")
        return df

    print("[BTC] Fetching from Yahoo Finance (BTC-USD) …")
    raw = yf.download("BTC-USD", start="2017-01-01", auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError("yfinance returned empty dataframe for BTC-USD")

    # Handle both single-ticker (flat) and multi-ticker (MultiIndex) column shapes
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw[("Close", "BTC-USD")]
    else:
        close = raw["Close"]

    df = close.to_frame(name="close")
    df.index = pd.DatetimeIndex(df.index.normalize())
    df = df.drop_duplicates().sort_index()
    df.to_parquet(BTC_CACHE)
    print(f"[BTC] Fetched {len(df)} rows, {df.index.min().date()} → {df.index.max().date()}")
    return df


def build_merged() -> pd.DataFrame:
    """Merge FG and BTC price on date, compute log returns, filter to FG window.

    Returns DataFrame with columns:
        fg (float), close (float), log_ret (float).
    Index: DatetimeIndex (daily, date only).
    Rows where either series is NaN are dropped.
    """
    if MERGED_CACHE.exists():
        df = pd.read_parquet(MERGED_CACHE)
        print(f"[Merged] Loaded from cache: {len(df)} rows")
        return df

    fg = fetch_fg().rename(columns={"value": "fg"})
    btc = fetch_btc().rename(columns={"close": "close"})

    # Align on date index — inner join (only dates where both exist)
    merged = fg.join(btc, how="inner")

    # Forward-fill any single-day F&G gaps (rare maintenance gaps)
    merged["fg"] = merged["fg"].ffill()
    merged = merged.dropna()

    # Log return (daily)
    merged["log_ret"] = np.log(merged["close"] / merged["close"].shift(1))
    merged = merged.iloc[1:]  # drop first row (NaN log_ret)

    # Restrict to F&G coverage start
    merged = merged[merged.index >= "2018-02-01"]

    merged.to_parquet(MERGED_CACHE)
    print(f"[Merged] Built: {len(merged)} rows, {merged.index.min().date()} → {merged.index.max().date()}")
    return merged


if __name__ == "__main__":
    df = build_merged()
    print(df.tail())
    print(f"\nF&G range: {df['fg'].min():.0f} – {df['fg'].max():.0f}")
    print(f"BTC close range: ${df['close'].min():,.0f} – ${df['close'].max():,.0f}")
    missing_fg = df["fg"].isna().sum()
    missing_btc = df["close"].isna().sum()
    print(f"Missing values: FG={missing_fg}, BTC={missing_btc}")
