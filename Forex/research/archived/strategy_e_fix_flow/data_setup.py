"""
Forex/research/active/strategy_e_fix_flow/data_setup.py
=========================================================
Download Dukascopy M5 OHLC data for 6 major FX pairs, 2016-2026.
Cache as per-pair parquet in Forex/data/cache/dukascopy_m5/.

Implementation notes:
  - Custom HTTP fetcher (duka library gets 403 without browser headers)
  - Sequential hour-fetching per day (avoids Dukascopy rate-limit)
  - 4 day-level parallel threads MAX (prevents IP rate-limiting)
  - 120ms inter-request sleep + exponential backoff on 429/503/timeout
  - Correct timezone: Dukascopy bi5 ms_off is from midnight CET/CEST
    (Europe/Paris). We use zoneinfo to convert to UTC timestamps.

Usage:
    /usr/bin/python3 data_setup.py [--pair EURUSD] [--year 2016] [--threads 4]
    /usr/bin/python3 data_setup.py --status

Speed: ~12 min/pair-year at 4 threads (24 hours × 120ms sleep + ~1s fetch each).
Full run (6 pairs × 10 years = 60 pair-years): ~12 hours. Run overnight.
Canary test: download_pair_year('EURUSD', 2024, month_filter=[1]) → ~20 min.
"""

from __future__ import annotations

import argparse
import json
import struct
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from lzma import FORMAT_AUTO, LZMADecompressor, LZMAError
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

warnings.filterwarnings("ignore")

# ── constants ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[4]
CACHE_DIR = REPO_ROOT / "Forex" / "data" / "cache" / "dukascopy_m5"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PAIRS   = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF"]
YEARS   = list(range(2016, 2026))   # 2016-2025 inclusive
END_DT  = date(2026, 5, 1)
M5_MS   = 300_000                   # 5 minutes in milliseconds

CET  = ZoneInfo("Europe/Paris")     # Dukascopy server timezone = CET/CEST

URL_TEMPLATE = (
    "https://www.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":  "*/*",
    "Referer": "https://www.dukascopy.com/",
}
ATTEMPTS = 4
INTER_REQUEST_SLEEP = 0.12   # seconds between successful hour fetches (politeness)
RATE_LIMIT_WAIT    = 65.0    # seconds to wait on HTTP 429 before retry
ERROR_WAIT_BASE    = 2.0     # base seconds for exponential backoff on errors


# ── bi5 decoder ────────────────────────────────────────────────────────────────

class Tick(NamedTuple):
    utc_ms: int    # milliseconds since Unix epoch (UTC)
    ask: float
    bid: float


def _decompress_lzma(data: bytes) -> bytes:
    results = []
    while True:
        dec = LZMADecompressor(FORMAT_AUTO)
        try:
            res = dec.decompress(data)
        except LZMAError:
            if results:
                break
            raise
        results.append(res)
        data = dec.unused_data
        if not data:
            break
    return b"".join(results)


def _parse_bi5(day: date, hour_cet: int, raw: bytes) -> list[Tick]:
    """
    Decode one hour's bi5 file into Ticks.

    The ms_off field is milliseconds from the START OF THAT CET HOUR (0..3,599,999).
    We convert to UTC epoch by anchoring to midnight CET + hour offset.
    """
    if not raw:
        return []
    try:
        buf = _decompress_lzma(raw)
    except LZMAError:
        return []

    token_size = 20
    n = len(buf) // token_size
    if n == 0:
        return []

    # Midnight CET on this day → UTC epoch ms, then add the hour offset
    midnight_cet   = datetime(day.year, day.month, day.day, tzinfo=CET)
    hour_base_utc_ms = int(midnight_cet.timestamp() * 1000) + hour_cet * 3_600_000

    ticks = []
    for i in range(n):
        ms_off, ask_raw, bid_raw, _av, _bv = struct.unpack_from("!IIIff", buf, i * token_size)
        ticks.append(Tick(hour_base_utc_ms + ms_off, ask_raw / 1e5, bid_raw / 1e5))
    return ticks


def _ticks_to_m5(ticks: list[Tick]) -> list[dict]:
    """Aggregate ticks to M5 candles on UTC epoch grid."""
    candles: dict[int, list[float]] = {}
    for t in ticks:
        bar_ms = t.utc_ms - (t.utc_ms % M5_MS)
        mid = (t.ask + t.bid) / 2
        candles.setdefault(bar_ms, []).append(mid)

    rows = []
    for bar_ms, prices in sorted(candles.items()):
        ts = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=bar_ms)
        rows.append({
            "time":  ts,
            "open":  prices[0],
            "high":  max(prices),
            "low":   min(prices),
            "close": prices[-1],
        })
    return rows


# ── HTTP fetcher ───────────────────────────────────────────────────────────────

def _fetch_hour(pair: str, day: date, hour: int, session: requests.Session) -> list[Tick]:
    url = URL_TEMPLATE.format(
        pair=pair, year=day.year, month=day.month - 1, day=day.day, hour=hour
    )
    for attempt in range(ATTEMPTS):
        try:
            resp = session.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            if resp.status_code == 200:
                return _parse_bi5(day, hour, resp.content)
            if resp.status_code == 404:
                return []   # legitimate empty hour (weekend / session closed)
            if resp.status_code == 429:
                # Hard rate-limit: wait RATE_LIMIT_WAIT before any retry
                print(f"\n  [429] rate-limited, waiting {RATE_LIMIT_WAIT:.0f}s …", flush=True)
                time.sleep(RATE_LIMIT_WAIT)
                continue
            if resp.status_code in (503, 502, 504):
                wait = ERROR_WAIT_BASE * (2 ** attempt)
                time.sleep(wait)
                continue
            # Any other unexpected status: exponential backoff
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
        except requests.exceptions.Timeout:
            wait = ERROR_WAIT_BASE * (2 ** attempt)
            time.sleep(wait)
        except Exception:
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
    return []


def _trading_days(start: date, end: date):
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            yield cur
        cur += timedelta(days=1)


# ── download ───────────────────────────────────────────────────────────────────

def download_pair_year(
    pair: str,
    year: int,
    threads: int = 4,
    month_filter: list[int] | None = None,
) -> bool:
    """
    Download pair × year. Each thread handles one day fetching all 24 hours
    sequentially with INTER_REQUEST_SLEEP between each, to stay well under
    Dukascopy's rate limit. Max recommended threads = 4.

    Args:
        month_filter: if given, only download these calendar months (e.g. [1] for January).
                      Used for canary tests.
    """
    start = date(year, 1, 1)
    end   = date(year, 12, 31)
    if start > END_DT:
        return False
    if end > END_DT:
        end = END_DT

    tdays = [
        d for d in _trading_days(start, end)
        if month_filter is None or d.month in month_filter
    ]
    if not tdays:
        return False

    label = f"{pair} {year}" + (f" month={month_filter}" if month_filter else "")
    print(f"  {label}  ({len(tdays)} trading days, {threads} threads) …", flush=True)

    # thread-local session
    import threading
    _local = threading.local()

    def get_session() -> requests.Session:
        if not hasattr(_local, "s"):
            _local.s = requests.Session()
        return _local.s

    all_rows: list[dict] = []
    errors = [0]
    done   = [0]
    lock   = threading.Lock()

    def fetch_day_rows(day: date) -> list[dict]:
        sess = get_session()
        day_ticks: list[Tick] = []
        for hour in range(24):
            day_ticks.extend(_fetch_hour(pair, day, hour, sess))
            time.sleep(INTER_REQUEST_SLEEP)   # politeness: 120ms between requests
        return _ticks_to_m5(day_ticks)

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futs = {pool.submit(fetch_day_rows, d): d for d in tdays}
        for fut in as_completed(futs):
            try:
                rows = fut.result()
                with lock:
                    all_rows.extend(rows)
                    done[0] += 1
            except Exception:
                with lock:
                    errors[0] += 1
                    done[0] += 1
            if done[0] % 20 == 0 or done[0] == len(tdays):
                pct = done[0] / len(tdays) * 100
                print(f"\r    {done[0]}/{len(tdays)} ({pct:.0f}%)  rows: {len(all_rows)}  err: {errors[0]}   ",
                      end="", flush=True)

    print()
    if not all_rows:
        print(f"  WARNING: no rows for {pair} {year}")
        return False

    df = pd.DataFrame(all_rows).set_index("time").sort_index()[["open", "high", "low", "close"]]
    pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
    df.to_parquet(pq, compression="snappy")
    mb = pq.stat().st_size / 1e6
    print(f"  ✓ {pair} {year}: {len(df)} rows  {mb:.1f} MB  ({errors[0]} errors)")
    return True


# ── status ─────────────────────────────────────────────────────────────────────

def download_status() -> dict:
    status: dict = {}
    for pair in PAIRS:
        pair_info: dict = {"years": {}}
        for year in YEARS:
            pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
            if pq.exists():
                df = pd.read_parquet(pq)
                nan_count = int(df.isnull().sum().sum())
                pair_info["years"][year] = {
                    "rows":    len(df),
                    "start":   str(df.index.min()),
                    "end":     str(df.index.max()),
                    "size_mb": round(pq.stat().st_size / 1e6, 2),
                    "nan_pct": round(nan_count / max(len(df) * len(df.columns), 1) * 100, 3),
                }
        pair_info["years_cached"] = len(pair_info["years"])
        pair_info["years_total"]  = len(YEARS)
        status[pair] = pair_info
    return status


def print_status_table(status: dict) -> None:
    print("\n" + "=" * 72)
    print("DUKASCOPY M5 CACHE STATUS")
    print("=" * 72)
    total_rows = 0
    for pair, info in status.items():
        yc = info["years_cached"]
        yt = info["years_total"]
        bar = "█" * yc + "░" * (yt - yc)
        print(f"\n{pair}  [{bar}]  {yc}/{yt} years")
        for year, yi in sorted(info["years"].items()):
            total_rows += yi["rows"]
            print(f"  {year}: {yi['rows']:>7} rows  "
                  f"{yi['start'][:16]} → {yi['end'][:16]}  "
                  f"{yi['size_mb']:.1f} MB  NaN {yi['nan_pct']:.2f}%")
    print(f"\nTotal rows: {total_rows:,}")
    print("=" * 72)


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair",    choices=PAIRS + ["ALL"], default="ALL")
    parser.add_argument("--year",    type=int, default=0, help="0 = all years")
    parser.add_argument("--threads", type=int, default=4,
                        help="Day-level parallel threads. Max recommended: 4")
    parser.add_argument("--status",  action="store_true")
    args = parser.parse_args()

    if args.status:
        print_status_table(download_status())
        return

    target_pairs = PAIRS if args.pair == "ALL" else [args.pair]
    target_years = YEARS if args.year == 0 else [args.year]

    already = failed = 0
    for pair in target_pairs:
        for year in target_years:
            pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
            if pq.exists():
                already += 1
                continue
            ok = download_pair_year(pair, year, threads=args.threads)
            if not ok:
                failed += 1

    print(f"\nDone.  Cached already: {already}  Failed: {failed}")
    status = download_status()
    print_status_table(status)
    with open(CACHE_DIR / "status.json", "w") as f:
        json.dump(status, f, indent=2, default=str)


if __name__ == "__main__":
    main()
