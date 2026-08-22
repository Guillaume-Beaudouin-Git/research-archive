"""
Self-contained Dukascopy M5 fetcher, SCOPED to this study's own _cache/ folder.

Rationale: `Forex/data/dukascopy_downloader_m5.py` already implements this exact protocol
(bi5 tick decode -> M5 OHLC) and is the canonical location for it, but its top-level
`CACHE_DIR.mkdir(...)` writes into `Forex/data/cache/dukascopy_m5/` — outside the single
folder this study is allowed to write into (mandate constraint). Importing it would create
that directory as a side effect. So this script reimplements only the small, generic
bi5-fetch primitive (same URL scheme, same parse) and writes exclusively under this
study's own `_cache/`. Index Dukascopy codes are copied read-only from that module's
`SYMBOLS["indices"]` dict (JP225/HK50/AUS200/UK100/FRA40/EU50) — not modified, just cited.

Usage:
    /usr/bin/python3 fetch_new_indices.py --canary --symbol JP225
    /usr/bin/python3 fetch_new_indices.py --symbol JP225 --years 2023 2024 2025
"""
from __future__ import annotations
import argparse, struct, threading, time, warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from lzma import FORMAT_AUTO, LZMADecompressor, LZMAError
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
CACHE = HERE / "_cache" / "dukascopy_m5"
CACHE.mkdir(parents=True, exist_ok=True)

# Codes copied read-only from Forex/data/dukascopy_downloader_m5.py::SYMBOLS["indices"]
CODES = {
    "JP225": "JPNIDXJPY", "HK50": "HKGIDXHKD", "AUS200": "AUSIDXAUD",
    "UK100": "GBRIDXGBP", "FRA40": "FRAIDXEUR", "EU50": "EUSIDXEUR",
}

CET = ZoneInfo("Europe/Paris")
URL = "https://www.dukascopy.com/datafeed/{code}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept": "*/*",
          "Referer": "https://www.dukascopy.com/"}
M5_MS = 300_000


class Tick(NamedTuple):
    utc_ms: int; ask: float; bid: float


def _decompress(data: bytes) -> bytes:
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


def _parse_bi5(day: date, hour: int, raw: bytes) -> list[Tick]:
    if not raw:
        return []
    try:
        buf = _decompress(raw)
    except LZMAError:
        return []
    n = len(buf) // 20
    if n == 0:
        return []
    midnight = datetime(day.year, day.month, day.day, tzinfo=CET)
    base_ms = int(midnight.timestamp() * 1000) + hour * 3_600_000
    ticks = []
    for i in range(n):
        ms_off, ask_raw, bid_raw, _av, _bv = struct.unpack_from("!IIIff", buf, i * 20)
        ticks.append(Tick(base_ms + ms_off, ask_raw / 1e5, bid_raw / 1e5))
    return ticks


def _to_m5(ticks: list[Tick]) -> list[dict]:
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


def _fetch_hour(code, day, hour, sess) -> list[Tick]:
    url = URL.format(code=code, year=day.year, month=day.month - 1, day=day.day, hour=hour)
    for attempt in range(4):
        try:
            r = sess.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            if r.status_code == 200:
                return _parse_bi5(day, hour, r.content)
            if r.status_code == 404:
                return []
            if r.status_code == 429:
                time.sleep(65.0); continue
            time.sleep(2.0 * (2 ** attempt))
        except requests.exceptions.Timeout:
            time.sleep(2.0 * (2 ** attempt))
        except Exception:
            time.sleep(2.0 * (2 ** attempt))
    return []


def _trading_days(start, end):
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            yield cur
        cur += timedelta(days=1)


def download_year(name, code, year, threads=4, month_filter=None, end_dt=None):
    end_dt = end_dt or date.today()
    start, end = date(year, 1, 1), date(year, 12, 31)
    if start > end_dt:
        return False
    if end > end_dt:
        end = end_dt
    tdays = [d for d in _trading_days(start, end) if month_filter is None or d.month in month_filter]
    if not tdays:
        return False
    print(f"  {name} ({code}) {year} [{len(tdays)} days, {threads} thr] ...", flush=True)
    local = threading.local()

    def sess():
        if not hasattr(local, "s"):
            local.s = requests.Session()
        return local.s

    def fetch_day(day):
        s = sess(); tk = []
        for hour in range(24):
            tk.extend(_fetch_hour(code, day, hour, s))
            time.sleep(0.12)
        return _to_m5(tk)

    rows, errors, done = [], [0], [0]
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futs = {pool.submit(fetch_day, d): d for d in tdays}
        for fut in as_completed(futs):
            try:
                r = fut.result()
                with lock:
                    rows.extend(r); done[0] += 1
            except Exception:
                with lock:
                    errors[0] += 1; done[0] += 1
            if done[0] % 20 == 0 or done[0] == len(tdays):
                print(f"\r    {done[0]}/{len(tdays)} rows={len(rows)} err={errors[0]}", end="", flush=True)
    print()
    if not rows:
        print(f"  WARNING: 0 rows for {name} {year} -- code '{code}' likely wrong or no data")
        return False
    df = pd.DataFrame(rows).set_index("time").sort_index()[["open", "high", "low", "close", "tick_count"]]
    pq = CACHE / f"{name}_{year}_M5.parquet"
    df.to_parquet(pq, compression="snappy")
    print(f"  OK {name} {year}: {len(df)} rows {pq.stat().st_size/1e6:.2f}MB")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True, choices=list(CODES))
    ap.add_argument("--years", type=int, nargs="+", default=[2025])
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--canary", action="store_true", help="January only")
    args = ap.parse_args()
    mf = [1] if args.canary else None
    for y in args.years:
        download_year(args.symbol, CODES[args.symbol], y, threads=args.threads, month_filter=mf)
