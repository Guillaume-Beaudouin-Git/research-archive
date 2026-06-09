"""
Forex/data/dukascopy_downloader_m5.py
======================================
Dukascopy M5 OHLC downloader — canonical location for the bi5 fetcher
previously archived under strategy_e_fix_flow/.

Asset coverage (defaults below). Dukascopy URL codes for non-FX symbols
are mapped through SYMBOLS — adjust if a 404 wave appears.

Cache (unchanged from prior location):
    Forex/data/cache/dukascopy_m5/<symbol>_<year>_M5.parquet

Usage:
    /usr/bin/python3 dukascopy_downloader_m5.py --status
    /usr/bin/python3 dukascopy_downloader_m5.py --asset fx_majors --year 2024
    /usr/bin/python3 dukascopy_downloader_m5.py --symbol EURUSD --year 2024
    /usr/bin/python3 dukascopy_downloader_m5.py --asset ALL --threads 4

Speed: ~12 min / symbol-year at 4 threads. 30 symbols × 8 years × 12 min ≈ 48h.
       Run --asset by asset, overnight.

NOTE on non-FX Dukascopy codes:
- Metals (XAGUSD, XPTUSD, XPDUSD), crypto majors (BTCUSD, ETHUSD, LTCUSD,
  BCHUSD, XRPUSD), and energies (BRENTCMDUSD, LIGHTCMDUSD, GASCMDUSD) use the
  hourly bi5 endpoint format with their Dukascopy-internal code.
- Indices Dukascopy codes vary; defaults below are best-guess. Run with
  --canary first (1 month) to confirm each index downloads non-empty before
  full pull. The script silently skips 404s (legitimate non-trading hours),
  so a fully-404 symbol implies wrong code.
"""

from __future__ import annotations

import argparse
import json
import struct
import threading
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

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / "Forex" / "data" / "cache" / "dukascopy_m5"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# our_name → dukascopy_url_code  (identical for FX, different for some indices/commos)
SYMBOLS: dict[str, dict[str, str]] = {
    "fx_majors": {
        "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
        "USDCHF": "USDCHF", "AUDUSD": "AUDUSD", "USDCAD": "USDCAD",
        "NZDUSD": "NZDUSD",
    },
    "fx_crosses": {
        "EURJPY": "EURJPY", "GBPJPY": "GBPJPY", "EURGBP": "EURGBP",
        "EURCHF": "EURCHF", "AUDJPY": "AUDJPY", "CADJPY": "CADJPY",
    },
    "metals": {
        "XAUUSD": "XAUUSD", "XAGUSD": "XAGUSD",
        "XPTUSD": "XPTUSD", "XPDUSD": "XPDUSD",
    },
    "energies": {
        # Dukascopy uses these internal codes for spot CFDs:
        "USOIL": "LIGHTCMDUSD",   # WTI Light Crude
        "UKOIL": "BRENTCMDUSD",   # Brent Crude
        "NGAS":  "GASCMDUSD",     # Natural Gas
    },
    "indices": {
        # Best-guess Dukascopy index codes — VERIFY with --canary before full pull.
        # If a code is wrong, the script will silently get 0 rows (all 404).
        "US500":  "USA500IDXUSD",
        "US100":  "USATECHIDXUSD",
        "US30":   "USA30IDXUSD",
        "GER40":  "DEUIDXEUR",
        "UK100":  "GBRIDXGBP",
        "FRA40":  "FRAIDXEUR",
        "EU50":   "EUSIDXEUR",
        "JP225":  "JPNIDXJPY",
        "AUS200": "AUSIDXAUD",
        "HK50":   "HKGIDXHKD",
    },
    "crypto_majors": {
        # Dukascopy-available crypto. SOL/ADA/DOT/DOGE → use Binance fallback.
        "BTCUSD": "BTCUSD", "ETHUSD": "ETHUSD",
        "LTCUSD": "LTCUSD", "BCHUSD": "BCHUSD", "XRPUSD": "XRPUSD",
    },
}


def all_symbols() -> dict[str, str]:
    out: dict[str, str] = {}
    for bucket in SYMBOLS.values():
        out.update(bucket)
    return out


YEARS_DEFAULT = list(range(2018, 2027))   # 2018-2026 inclusive
END_DT_DEFAULT = date.today()
M5_MS = 300_000

CET = ZoneInfo("Europe/Paris")

URL_TEMPLATE = (
    "https://www.dukascopy.com/datafeed/{code}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://www.dukascopy.com/",
}
ATTEMPTS = 4
INTER_REQUEST_SLEEP = 0.12
RATE_LIMIT_WAIT = 65.0
ERROR_WAIT_BASE = 2.0


class Tick(NamedTuple):
    utc_ms: int
    ask: float
    bid: float


def _decompress_lzma(data: bytes) -> bytes:
    out = []
    while True:
        dec = LZMADecompressor(FORMAT_AUTO)
        try:
            out.append(dec.decompress(data))
        except LZMAError:
            if out:
                break
            raise
        data = dec.unused_data
        if not data:
            break
    return b"".join(out)


def _parse_bi5(day: date, hour_cet: int, raw: bytes) -> list[Tick]:
    if not raw:
        return []
    try:
        buf = _decompress_lzma(raw)
    except LZMAError:
        return []
    n = len(buf) // 20
    if n == 0:
        return []
    midnight_cet = datetime(day.year, day.month, day.day, tzinfo=CET)
    hour_base_ms = int(midnight_cet.timestamp() * 1000) + hour_cet * 3_600_000
    ticks: list[Tick] = []
    for i in range(n):
        ms_off, ask_raw, bid_raw, _av, _bv = struct.unpack_from("!IIIff", buf, i * 20)
        ticks.append(Tick(hour_base_ms + ms_off, ask_raw / 1e5, bid_raw / 1e5))
    return ticks


def _ticks_to_m5(ticks: list[Tick]) -> list[dict]:
    candles: dict[int, list[float]] = {}
    for t in ticks:
        bar_ms = t.utc_ms - (t.utc_ms % M5_MS)
        candles.setdefault(bar_ms, []).append((t.ask + t.bid) / 2)
    rows = []
    for bar_ms, prices in sorted(candles.items()):
        ts = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=bar_ms)
        rows.append({"time": ts, "open": prices[0], "high": max(prices),
                     "low": min(prices), "close": prices[-1], "tick_count": len(prices)})
    return rows


def _fetch_hour(code: str, day: date, hour: int, session: requests.Session) -> list[Tick]:
    url = URL_TEMPLATE.format(code=code, year=day.year, month=day.month - 1,
                              day=day.day, hour=hour)
    for attempt in range(ATTEMPTS):
        try:
            resp = session.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            if resp.status_code == 200:
                return _parse_bi5(day, hour, resp.content)
            if resp.status_code == 404:
                return []
            if resp.status_code == 429:
                print(f"\n  [429] rate-limited, waiting {RATE_LIMIT_WAIT:.0f}s …", flush=True)
                time.sleep(RATE_LIMIT_WAIT)
                continue
            if resp.status_code in (503, 502, 504):
                time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
                continue
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
        except requests.exceptions.Timeout:
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
        except Exception:
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
    return []


def _trading_days(start: date, end: date, weekends: bool):
    cur = start
    while cur <= end:
        if weekends or cur.weekday() < 5:
            yield cur
        cur += timedelta(days=1)


def download_symbol_year(
    name: str,
    code: str,
    year: int,
    threads: int = 4,
    month_filter: list[int] | None = None,
    end_dt: date | None = None,
    weekends: bool = False,
) -> bool:
    """Crypto-class symbols should pass weekends=True."""
    end_dt = end_dt or END_DT_DEFAULT
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    if start > end_dt:
        return False
    if end > end_dt:
        end = end_dt

    tdays = [d for d in _trading_days(start, end, weekends)
             if month_filter is None or d.month in month_filter]
    if not tdays:
        return False

    print(f"  {name} ({code}) {year}  [{len(tdays)} days, {threads} threads] …", flush=True)

    _local = threading.local()

    def get_session() -> requests.Session:
        if not hasattr(_local, "s"):
            _local.s = requests.Session()
        return _local.s

    all_rows: list[dict] = []
    errors = [0]
    done = [0]
    lock = threading.Lock()

    def fetch_day(day: date) -> list[dict]:
        sess = get_session()
        day_ticks: list[Tick] = []
        for hour in range(24):
            day_ticks.extend(_fetch_hour(code, day, hour, sess))
            time.sleep(INTER_REQUEST_SLEEP)
        return _ticks_to_m5(day_ticks)

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futs = {pool.submit(fetch_day, d): d for d in tdays}
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
                print(f"\r    {done[0]}/{len(tdays)} ({pct:.0f}%)  "
                      f"rows: {len(all_rows)}  err: {errors[0]}   ",
                      end="", flush=True)
    print()
    if not all_rows:
        print(f"  WARNING: no rows for {name} {year} — code '{code}' likely wrong")
        return False

    df = (pd.DataFrame(all_rows)
            .set_index("time").sort_index()
            [["open", "high", "low", "close", "tick_count"]])
    pq = CACHE_DIR / f"{name}_{year}_M5.parquet"
    df.to_parquet(pq, compression="snappy")
    print(f"  OK {name} {year}: {len(df)} rows  {pq.stat().st_size / 1e6:.1f} MB  err={errors[0]}")
    return True


def cache_status() -> dict:
    status: dict = {}
    for name in all_symbols():
        info: dict = {"years": {}}
        for year in YEARS_DEFAULT:
            pq = CACHE_DIR / f"{name}_{year}_M5.parquet"
            if pq.exists():
                df = pd.read_parquet(pq)
                info["years"][year] = {
                    "rows": len(df),
                    "start": str(df.index.min()),
                    "end": str(df.index.max()),
                    "size_mb": round(pq.stat().st_size / 1e6, 2),
                }
        info["years_cached"] = len(info["years"])
        info["years_total"] = len(YEARS_DEFAULT)
        status[name] = info
    return status


def print_status(status: dict) -> None:
    print("\n" + "=" * 78)
    print("DUKASCOPY M5 CACHE STATUS")
    print("=" * 78)
    total_rows = 0
    for name, info in status.items():
        yc, yt = info["years_cached"], info["years_total"]
        if yc == 0:
            continue
        bar = "#" * yc + "." * (yt - yc)
        print(f"\n{name}  [{bar}]  {yc}/{yt} years")
        for year, yi in sorted(info["years"].items()):
            total_rows += yi["rows"]
            print(f"  {year}: {yi['rows']:>7}  {yi['size_mb']:.1f} MB  {yi['start'][:16]} → {yi['end'][:16]}")
    not_cached = [n for n, i in status.items() if i["years_cached"] == 0]
    print(f"\nTotal rows: {total_rows:,}")
    if not_cached:
        print(f"Symbols with NO cache: {', '.join(not_cached)}")
    print("=" * 78)


CRYPTO_BUCKETS = {"crypto_majors"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", choices=list(SYMBOLS.keys()) + ["ALL"], default=None,
                    help="Bucket to download.")
    ap.add_argument("--symbol", default=None,
                    help="Single symbol (overrides --asset). Use our_name (e.g. USOIL).")
    ap.add_argument("--year", type=int, default=0, help="0 = all YEARS_DEFAULT")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--canary", action="store_true",
                    help="Download January only to validate symbol code")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        print_status(cache_status())
        return

    if args.symbol:
        all_map = all_symbols()
        if args.symbol not in all_map:
            print(f"Unknown symbol '{args.symbol}'. Known: {sorted(all_map.keys())}")
            return
        targets = {args.symbol: all_map[args.symbol]}
        is_crypto = any(args.symbol in SYMBOLS[b] for b in CRYPTO_BUCKETS)
    elif args.asset:
        if args.asset == "ALL":
            targets = all_symbols()
            is_crypto = False  # mixed; handled per-symbol below
        else:
            targets = dict(SYMBOLS[args.asset])
            is_crypto = args.asset in CRYPTO_BUCKETS
    else:
        ap.error("Specify --symbol, --asset, or --status")

    years = YEARS_DEFAULT if args.year == 0 else [args.year]
    month_filter = [1] if args.canary else None

    already = failed = 0
    for name, code in targets.items():
        symbol_is_crypto = any(name in SYMBOLS[b] for b in CRYPTO_BUCKETS)
        for year in years:
            pq = CACHE_DIR / f"{name}_{year}_M5.parquet"
            if pq.exists() and not args.canary:
                already += 1
                continue
            ok = download_symbol_year(name, code, year, threads=args.threads,
                                      month_filter=month_filter,
                                      weekends=symbol_is_crypto)
            if not ok:
                failed += 1

    print(f"\nDone.  Cached already: {already}  Failed/empty: {failed}")
    with open(CACHE_DIR / "status.json", "w") as f:
        json.dump(cache_status(), f, indent=2, default=str)


if __name__ == "__main__":
    main()
