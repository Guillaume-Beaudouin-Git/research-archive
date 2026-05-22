"""
PHASE 1.5 Task 2 — Dukascopy 1-min OHLCV fetcher (requests + ThreadPoolExecutor)
Pairs: EURUSD, GBPUSD
Period: 2020-01-01 to 2024-12-31
Output: parquet at data/raw/dukascopy_{pair}_{year}.parquet
Expected: ~250k-350k bars per pair per year (FX 24h × ~260 days × 60 bars/h)

Note: aiohttp caused sparse results (~10% fill) due to LibreSSL/SSL mismatch.
      This version uses requests + ThreadPoolExecutor with rate control.
"""

import struct
import lzma
import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

PAIRS = ["EURUSD", "GBPUSD"]
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
END   = datetime(2024, 12, 31, 23, 59, tzinfo=timezone.utc)

BASE_URL = "https://datafeed.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"

TICK_STRUCT = struct.Struct(">IIIff")
TICK_SIZE   = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

MAX_WORKERS = 5          # conservative: 5 threads, no rate-limiting issues
REQUEST_DELAY = 0.05     # 50ms between requests per thread


def pair_point(pair: str) -> float:
    return 1e-5 if pair in ("EURUSD", "GBPUSD", "EURGBP", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD") else 1e-3


def decode_bi5(data: bytes, pair: str, hour_dt: datetime) -> pd.DataFrame:
    """Decode bi5 tick blob → DataFrame with timestamp index."""
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


def fetch_hour_sync(pair: str, hour_dt: datetime, session: requests.Session) -> pd.DataFrame:
    """Fetch one hour of bi5 data synchronously."""
    url = BASE_URL.format(
        pair=pair,
        year=hour_dt.year,
        month=hour_dt.month - 1,
        day=hour_dt.day,
        hour=hour_dt.hour,
    )
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code in (204, 404) or not resp.content:
            return pd.DataFrame()
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return decode_bi5(resp.content, pair, hour_dt)
    except Exception:
        return pd.DataFrame()


def all_hours(year: int):
    """Yield every UTC hour in the year, skipping weekends (Sat/Sun)."""
    dt = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    while dt < end:
        # weekday(): 0=Mon, 5=Sat, 6=Sun
        if dt.weekday() < 5:
            yield dt
        dt += timedelta(hours=1)


def ticks_to_ohlcv(ticks: pd.DataFrame, freq: str = "1min") -> pd.DataFrame:
    """Resample tick-level mid prices to OHLCV bars."""
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


def fetch_year(pair: str, year: int) -> pd.DataFrame:
    hours = list(all_hours(year))
    n_total = len(hours)
    print(f"  {pair} {year}: {n_total} hours to fetch (weekdays only)...")

    session = requests.Session()
    session.headers.update(HEADERS)

    all_ticks: list[pd.DataFrame] = []
    n_done = 0
    n_nonempty = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        future_to_hour = {exe.submit(fetch_hour_sync, pair, h, session): h for h in hours}
        for future in as_completed(future_to_hour):
            result = future.result()
            n_done += 1
            if not result.empty:
                all_ticks.append(result)
                n_nonempty += 1
            if n_done % 500 == 0 or n_done == n_total:
                fill_pct = n_nonempty / n_done * 100
                print(f"    {n_done}/{n_total} hours | {n_nonempty} non-empty ({fill_pct:.1f}% fill)")

    if not all_ticks:
        print(f"  WARNING: {pair} {year} — zero data retrieved")
        return pd.DataFrame()

    ticks = pd.concat(all_ticks, ignore_index=True)
    ohlcv = ticks_to_ohlcv(ticks, freq="1min")
    return ohlcv


def validate_bars(df: pd.DataFrame, pair: str, year: int) -> bool:
    n = len(df)
    lo, hi = 180_000, 420_000
    ok = lo <= n <= hi
    status = "OK" if ok else "WARNING"
    print(f"  [{status}] {pair} {year}: {n:,} 1-min bars (expected {lo:,}–{hi:,})")
    return ok


def main():
    for pair in PAIRS:
        all_years: list[pd.DataFrame] = []
        for year in range(START.year, END.year + 1):
            out_path = RAW_DIR / f"dukascopy_{pair}_{year}.parquet"
            if out_path.exists():
                df_year = pd.read_parquet(out_path)
                n = len(df_year)
                # Re-fetch if bar count is suspiciously low (old bad fetch)
                if n < 180_000:
                    print(f"  {pair} {year}: cached but only {n:,} bars — re-fetching")
                    out_path.unlink()
                else:
                    print(f"  {pair} {year}: cache hit ({n:,} bars) → {out_path.name}")
                    all_years.append(df_year)
                    continue
            print(f"\nFetching {pair} {year}...")
            df_year = fetch_year(pair, year)
            if not df_year.empty:
                df_year.to_parquet(out_path)
                validate_bars(df_year, pair, year)
                all_years.append(df_year)

        if all_years:
            full = pd.concat(all_years).sort_index()
            out_full = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
            full.to_parquet(out_full)
            print(f"\n{pair} TOTAL: {len(full):,} 1-min bars → {out_full.name}")


if __name__ == "__main__":
    main()
