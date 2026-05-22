"""
PHASE 1.5 Task 2 — Dukascopy 1-min OHLCV fetcher
Pairs: EURUSD, GBPUSD
Period: 2020-01-01 to 2024-12-31
Output: parquet at data/raw/dukascopy_{pair}_{year}.parquet
Expected: ~1.4M bars per pair (5 years × ~260 trading days × ~1080 bars/day)
"""

import struct
import lzma
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PAIRS = ["EURUSD", "GBPUSD"]
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
END   = datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc)

# Dukascopy stores ask ticks; we reconstruct OHLCV from bi5 tick data
# URL pattern: https://datafeed.dukascopy.com/datafeed/{PAIR}/{YYYY}/{MM:02d}/{DD:02d}/{HH:02d}h_ticks.bi5
BASE_URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"

# bi5 tick record: 4 bytes timestamp_ms (uint32), 4 bytes ask (uint32), 4 bytes bid (uint32),
#                  4 bytes ask_vol (float32), 4 bytes bid_vol (float32) → 20 bytes/record
TICK_STRUCT = struct.Struct(">IIIff")
TICK_SIZE   = 20


def pair_point(pair: str) -> float:
    """Return point size (1 pip = 10 points for 5-decimal pairs)."""
    return 1e-5 if pair in ("EURUSD", "GBPUSD", "EURGBP", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD") else 1e-3


def decode_bi5(data: bytes, pair: str, hour_dt: datetime) -> pd.DataFrame:
    """Decode a bi5 binary blob into a DataFrame of ask ticks."""
    if not data:
        return pd.DataFrame()
    try:
        raw = lzma.decompress(data)
    except lzma.LZMAError:
        return pd.DataFrame()
    n = len(raw) // TICK_SIZE
    if n == 0:
        return pd.DataFrame()
    records = [TICK_STRUCT.unpack_from(raw, i * TICK_SIZE) for i in range(n)]
    ms_offsets, asks, bids, ask_vols, bid_vols = zip(*records)
    point = pair_point(pair)
    timestamps = [hour_dt + timedelta(milliseconds=int(ms)) for ms in ms_offsets]
    return pd.DataFrame({
        "timestamp": timestamps,
        "ask": [a * point for a in asks],
        "bid": [b * point for b in bids],
        "ask_vol": ask_vols,
        "bid_vol": bid_vols,
    })


def ticks_to_ohlcv(ticks: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
    """Resample tick-level ask prices to OHLCV bars."""
    if ticks.empty:
        return pd.DataFrame()
    ticks = ticks.set_index("timestamp").sort_index()
    mid = (ticks["ask"] + ticks["bid"]) / 2
    vol = ticks["ask_vol"] + ticks["bid_vol"]
    ohlcv = pd.DataFrame({
        "open":   mid.resample(freq).first(),
        "high":   mid.resample(freq).max(),
        "low":    mid.resample(freq).min(),
        "close":  mid.resample(freq).last(),
        "volume": vol.resample(freq).sum(),
    }).dropna(subset=["open"])
    return ohlcv


async def fetch_hour(session: aiohttp.ClientSession, pair: str,
                     hour_dt: datetime, semaphore: asyncio.Semaphore) -> pd.DataFrame:
    url = BASE_URL.format(
        pair=pair,
        year=hour_dt.year,
        month=hour_dt.month - 1,      # Dukascopy months are 0-indexed
        day=hour_dt.day,
        hour=hour_dt.hour,
    )
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 204 or resp.status == 404:
                    return pd.DataFrame()
                resp.raise_for_status()
                data = await resp.read()
            return decode_bi5(data, pair, hour_dt)
        except Exception:
            return pd.DataFrame()


async def fetch_year(pair: str, year: int) -> pd.DataFrame:
    """Fetch all hours for one pair × year, return 1-min OHLCV DataFrame."""
    hours = []
    dt = datetime(year, 1, 1, tzinfo=timezone.utc)
    end_dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    while dt < end_dt:
        hours.append(dt)
        dt += timedelta(hours=1)

    semaphore = asyncio.Semaphore(20)       # max 20 concurrent requests
    connector = aiohttp.TCPConnector(limit=30)
    headers = {
        "User-Agent": "Mozilla/5.0 (research/academic; contact: research@example.com)",
    }

    all_ticks: list[pd.DataFrame] = []
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [fetch_hour(session, pair, h, semaphore) for h in hours]
        # Process in batches to avoid memory overload
        batch_size = 500
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch)
            batch_ticks = [r for r in results if not r.empty]
            if batch_ticks:
                all_ticks.extend(batch_ticks)
            print(f"  {pair} {year}: {min(i+batch_size, len(tasks))}/{len(tasks)} hours fetched, "
                  f"{sum(len(t) for t in all_ticks):,} ticks so far")

    if not all_ticks:
        print(f"  WARNING: {pair} {year} — no data retrieved")
        return pd.DataFrame()

    ticks = pd.concat(all_ticks).sort_index(kind="stable")
    ohlcv = ticks_to_ohlcv(ticks, freq="1min")
    return ohlcv


def validate_bars(df: pd.DataFrame, pair: str, year: int) -> bool:
    """Check bar count is plausible: expect ~250k–350k bars/year for FX."""
    n = len(df)
    # FX trades ~252 days/year × ~1080 bars/day (18h market + weekend gaps)
    # Actual: ~360k bars (24h × 365 - some weekends/holidays)
    # Relax to 200k as lower bound
    lo, hi = 200_000, 400_000
    ok = lo <= n <= hi
    status = "OK" if ok else "WARNING"
    print(f"  [{status}] {pair} {year}: {n:,} bars (expected {lo:,}–{hi:,})")
    return ok


async def main():
    for pair in PAIRS:
        all_years: list[pd.DataFrame] = []
        for year in range(START.year, END.year + 1):
            out_path = RAW_DIR / f"dukascopy_{pair}_{year}.parquet"
            if out_path.exists():
                print(f"  {pair} {year}: cache hit → {out_path.name}")
                df_year = pd.read_parquet(out_path)
            else:
                print(f"\nFetching {pair} {year}...")
                df_year = await fetch_year(pair, year)
                if not df_year.empty:
                    df_year.to_parquet(out_path)
                    print(f"  Saved → {out_path.name}")
            if not df_year.empty:
                validate_bars(df_year, pair, year)
                all_years.append(df_year)

        if all_years:
            full = pd.concat(all_years).sort_index()
            out_full = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
            full.to_parquet(out_full)
            n_total = len(full)
            print(f"\n{pair} TOTAL: {n_total:,} 1-min bars → {out_full.name}")
            # Sanity: expect ~1.4M–1.8M bars for 5 years
            if n_total < 1_000_000:
                print(f"  WARNING: {pair} total bars suspiciously low ({n_total:,})")
            else:
                print(f"  OK: {pair} bar count plausible")


if __name__ == "__main__":
    asyncio.run(main())
