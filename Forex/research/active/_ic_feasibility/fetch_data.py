"""
PHASE 1.5 Task 2 — Dukascopy 1-min OHLCV fetcher
Pairs: EURUSD, GBPUSD
Period: 2020-01-01 to 2024-12-31
Output: parquet at data/raw/dukascopy_{pair}_{year}.parquet

Technical notes:
  v1: aiohttp + Python 3.9/LibreSSL → ~10% fill (SSL issue, silently dropped)
  v2: requests + ThreadPool(5) + OpenSSL → 100% fill but ~20min/year (too slow)
  v3 (current): aiohttp + force_close=True + Python 3.12/OpenSSL → ~2min/year
    - force_close prevents nginx rate-limit on keep-alive connections
    - Python 3.12 venv has OpenSSL 3.4.1 (not LibreSSL)
    - Semaphore 20: proven not to trigger IP-level rate limiting
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

BASE_URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
HEADERS  = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

TICK_STRUCT = struct.Struct(">IIIff")
TICK_SIZE   = 20
CONCURRENCY = 20   # semaphore limit — safe with force_close (new TCP per request)


def pair_point(pair: str) -> float:
    return 1e-5 if pair in ("EURUSD", "GBPUSD", "EURGBP", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD") else 1e-3


def decode_bi5(data: bytes, pair: str, hour_dt: datetime) -> pd.DataFrame:
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


async def fetch_hour(pair: str, hour_dt: datetime, semaphore: asyncio.Semaphore) -> pd.DataFrame:
    url = BASE_URL.format(
        pair=pair,
        year=hour_dt.year,
        month=hour_dt.month - 1,
        day=hour_dt.day,
        hour=hour_dt.hour,
    )
    async with semaphore:
        connector = aiohttp.TCPConnector(force_close=True)  # new TCP per request → bypasses keep-alive rate limit
        try:
            async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status in (204, 404, 503):
                        return pd.DataFrame()
                    if resp.status != 200:
                        return pd.DataFrame()
                    data = await resp.read()
                    return decode_bi5(data, pair, hour_dt)
        except Exception:
            return pd.DataFrame()


def all_hours(year: int):
    dt = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    while dt < end:
        if dt.weekday() < 5:  # skip weekends
            yield dt
        dt += timedelta(hours=1)


def ticks_to_ohlcv(ticks: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
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


async def fetch_year_async(pair: str, year: int) -> pd.DataFrame:
    hours = list(all_hours(year))
    print(f"  {pair} {year}: {len(hours)} weekday hours...", flush=True)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [fetch_hour(pair, h, semaphore) for h in hours]

    all_ticks: list[pd.DataFrame] = []
    n_done = 0
    n_nonempty = 0
    batch_size = 200
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i : i + batch_size]
        results = await asyncio.gather(*batch)
        for r in results:
            n_done += 1
            if not r.empty:
                all_ticks.append(r)
                n_nonempty += 1
        fill_pct = n_nonempty / n_done * 100 if n_done > 0 else 0
        print(f"    {n_done}/{len(hours)} | {n_nonempty} non-empty ({fill_pct:.0f}% fill)", flush=True)

    if not all_ticks:
        print(f"  WARNING: {pair} {year} — zero non-empty hours", flush=True)
        return pd.DataFrame()

    ticks = pd.concat(all_ticks, ignore_index=True)
    return ticks_to_ohlcv(ticks, freq="1min")


def validate_bars(df: pd.DataFrame, pair: str, year: int) -> bool:
    n = len(df)
    lo, hi = 180_000, 450_000
    ok = lo <= n <= hi
    print(f"  {'OK' if ok else 'WARNING'}: {pair} {year}: {n:,} bars (expected {lo:,}–{hi:,})", flush=True)
    return ok


def main():
    for pair in PAIRS:
        all_years: list[pd.DataFrame] = []
        for year in range(START.year, END.year + 1):
            out_path = RAW_DIR / f"dukascopy_{pair}_{year}.parquet"
            if out_path.exists():
                df_year = pd.read_parquet(out_path)
                n = len(df_year)
                if n < 180_000:
                    print(f"  {pair} {year}: cached {n:,} bars — re-fetching (below threshold)", flush=True)
                    out_path.unlink()
                else:
                    print(f"  {pair} {year}: cache hit {n:,} bars", flush=True)
                    all_years.append(df_year)
                    continue

            print(f"\nFetching {pair} {year}...", flush=True)
            df_year = asyncio.run(fetch_year_async(pair, year))
            if not df_year.empty:
                df_year.to_parquet(out_path)
                validate_bars(df_year, pair, year)
                all_years.append(df_year)

        if all_years:
            full = pd.concat(all_years).sort_index()
            out_full = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
            full.to_parquet(out_full)
            print(f"\n{pair} TOTAL: {len(full):,} 1-min bars → {out_full.name}", flush=True)


if __name__ == "__main__":
    main()
