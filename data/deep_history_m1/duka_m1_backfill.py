"""
duka_m1_backfill.py
===================
Deep-history M1 OHLCV(+spread) downloader from Dukascopy per-day M1-candle bi5
endpoint. One pass per day fetches BID + ASK candle files → bid OHLC, ask close,
volume. Output cached per (symbol, year) as parquet in TRUE UTC. Splicing,
EET timestamp conversion, spread calibration and schema formatting happen in
``assemble.py`` (kept separate so re-running is cheap).

Endpoint:
  https://datafeed.dukascopy.com/datafeed/{CODE}/{YYYY}/{MM-1:02d}/{DD:02d}/{BID|ASK}_candles_min_1.bi5
Record (LZMA-compressed): 24 bytes ">iiiiif" =
  (seconds_from_UTC_midnight, open, high, low, close as int/decimalFactor, volume f32)

Usage:
  /usr/bin/python3 duka_m1_backfill.py --plan
  /usr/bin/python3 duka_m1_backfill.py --symbol EURUSD --years 2007-2017 --threads 8
  /usr/bin/python3 duka_m1_backfill.py --group P1 --threads 8          # all P1 backfill+fwd+cal
  /usr/bin/python3 duka_m1_backfill.py --status
"""
from __future__ import annotations

import argparse
import json
import struct
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from lzma import FORMAT_AUTO, LZMADecompressor, LZMAError
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent
CACHE = BASE / "_cache_duka"
CACHE.mkdir(parents=True, exist_ok=True)
URL = "https://datafeed.dukascopy.com/datafeed/{code}/{y}/{m0:02d}/{d:02d}/{side}_candles_min_1.bi5"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
           "Accept": "*/*", "Referer": "https://www.dukascopy.com/"}
REC = struct.Struct(">iiiiif")
TARGET_START = date(2007, 1, 1)   # FX/metals deep target (depth ≥2003); indices clamp to instr_start
CAL_YEAR = 2024                    # full year inside every instrument's existing range
TODAY = date.today()

_TL = threading.local()


def _session() -> requests.Session:
    """One requests.Session PER WORKER THREAD (thread-local). A single shared Session
    caps concurrency at its HTTPAdapter pool_maxsize (~10) and silently serializes the
    pool — so N threads must each own a session to open N concurrent connections."""
    s = getattr(_TL, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        _TL.s = s
    return s


# code, decimalFactor, MT5 point (for spread int), round dp, existing start/end, instrument depth start, group
INSTR: dict[str, dict] = {
    # ---- P1 crosses ----
    "GBPUSD": dict(code="GBPUSD", df=100000, point=1e-5, dp=5, es="2021-12-14", ee="2025-06-03", istart="2003-05-04", grp="P1"),
    "EURGBP": dict(code="EURGBP", df=100000, point=1e-5, dp=5, es="2021-12-15", ee="2025-06-03", istart="2003-08-03", grp="P1"),
    "NZDUSD": dict(code="NZDUSD", df=100000, point=1e-5, dp=5, es="2021-12-14", ee="2025-06-03", istart="2003-08-03", grp="P1"),
    "USDCHF": dict(code="USDCHF", df=100000, point=1e-5, dp=5, es="2021-12-14", ee="2025-05-30", istart="2003-05-04", grp="P1"),
    "AUDJPY": dict(code="AUDJPY", df=1000,   point=1e-3, dp=3, es="2022-04-06", ee="2025-06-26", istart="2003-11-30", grp="P1"),
    "EURJPY": dict(code="EURJPY", df=1000,   point=1e-3, dp=3, es="2022-04-06", ee="2025-06-03", istart="2003-08-03", grp="P1"),
    # ---- P2 FX / metals ----
    "EURUSD": dict(code="EURUSD", df=100000, point=1e-5, dp=5, es="2018-01-02", ee="2026-05-29", istart="2003-05-04", grp="P2fx"),
    "AUDUSD": dict(code="AUDUSD", df=100000, point=1e-5, dp=5, es="2018-01-02", ee="2025-06-03", istart="2003-08-03", grp="P2fx"),
    "USDCAD": dict(code="USDCAD", df=100000, point=1e-5, dp=5, es="2018-01-02", ee="2025-06-03", istart="2003-08-03", grp="P2fx"),
    "USDJPY": dict(code="USDJPY", df=1000,   point=1e-3, dp=3, es="2018-01-02", ee="2025-05-30", istart="2003-05-04", grp="P2fx"),
    "XAUUSD": dict(code="XAUUSD", df=1000,   point=1e-2, dp=2, es="2018-01-02", ee="2026-05-29", istart="2003-05-05", grp="P2fx"),
    # ---- P2 indices ----
    # es = DENSE MT5 start (bar-density audit 2026-06-10): the raw first MT5 bar for
    # US500/US100 (2018-01-02) and GER40 (2018-01-01) is a stray-bar artifact; true M1
    # depth starts 2021-09-14 (US500/US100) and 2021-12-29 (GER40). Used by plan_years.
    "US500": dict(code="USA500IDXUSD",  df=1000, point=1e-2, dp=2, es="2021-09-14", ee="2026-05-29", istart="2012-01-16", grp="P2idx"),
    "US100": dict(code="USATECHIDXUSD", df=1000, point=1e-2, dp=2, es="2021-09-14", ee="2026-05-29", istart="2013-01-01", grp="P2idx"),
    "US30":  dict(code="USA30IDXUSD",   df=1000, point=1e-2, dp=2, es="2019-02-08", ee="2026-05-29", istart="2013-01-01", grp="P2idx"),
    "GER40": dict(code="DEUIDXEUR",     df=1000, point=1e-2, dp=2, es="2021-12-29", ee="2026-05-29", istart="2013-01-01", grp="P2idx"),
    # US2000 intentionally absent: USSC2000IDXUSD depth 2018-08-08 > existing 2018-01-23 → cannot backfill (see manifest).
}


def _decompress(data: bytes) -> bytes:
    out: list[bytes] = []
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


def _fetch(session: requests.Session, url: str, attempts: int = 8) -> bytes | None:
    """Return bytes (200), None (404 = legitimately no file for that day), or RAISE after
    exhausting retries. Raising (never silently returning None on failure) means a dropped
    day surfaces as an `err` in download_year instead of becoming a SILENT data hole — the
    503-retry-exhaustion bug that corrupted the early high-concurrency runs."""
    for a in range(attempts):
        try:
            r = session.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(min(45.0, 5.0 + 1.5 * (2 ** a)))
                continue
            time.sleep(min(30.0, 1.5 * (2 ** a)))            # 503/5xx: capped backoff
        except requests.RequestException:
            time.sleep(min(30.0, 1.5 * (2 ** a)))
    raise RuntimeError(f"fetch failed after {attempts} attempts (not 404): {url}")


def _decode(raw: bytes | None, df: float) -> list[tuple]:
    """Return list of (sec, open, high, low, close, vol). Empty if no data."""
    if not raw:
        return []
    try:
        buf = _decompress(raw)
    except LZMAError:
        return []
    n = len(buf) // REC.size
    rows = []
    for i in range(n):
        # Dukascopy candle byte order is O,C,L,H (NOT OHLC) — verified 0/1440 mismatch
        # vs dukascopy-node ground truth incl. down-bars where close != high.
        sec, o, c, l, h, v = REC.unpack_from(buf, i * REC.size)
        rows.append((sec, o / df, h / df, l / df, c / df, v))
    return rows


def fetch_day(code: str, day: date, df: float) -> list[dict]:
    session = _session()                 # thread-local: created in THIS worker thread
    base = dict(code=code, y=day.year, m0=day.month - 1, d=day.day)
    bid = _decode(_fetch(session, URL.format(side="BID", **base)), df)
    if not bid:
        return []
    ask = _decode(_fetch(session, URL.format(side="ASK", **base)), df)
    ask_close = {r[0]: r[4] for r in ask}
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    out = []
    for sec, o, h, l, c, v in bid:
        if v <= 0 and h <= l:            # drop only truly-flat no-volume minutes. INDEX candles
            continue                     # report volume=0 even on real bars, so keep any bar with
        #                                  a price range (h>l); for FX/metals v>0 iff ticked → no-op.
        ts = midnight + timedelta(seconds=sec)
        out.append(dict(ts_utc=ts.replace(tzinfo=None), open=o, high=h, low=l,
                        close=c, volume=v, ask_close=ask_close.get(sec, c)))
    return out


def download_year(sym: str, year: int, threads: int = 8, force: bool = False) -> dict:
    cfg = INSTR[sym]
    out_pq = CACHE / f"{sym}_{year}.parquet"
    if out_pq.exists() and not force:
        df = pd.read_parquet(out_pq)
        return dict(sym=sym, year=year, status="cached", rows=len(df))

    istart = datetime.strptime(cfg["istart"], "%Y-%m-%d").date()
    start = max(date(year, 1, 1), istart, TARGET_START)
    end = min(date(year, 12, 31), TODAY)
    if start > end:
        return dict(sym=sym, year=year, status="out_of_range", rows=0)

    days = []
    cur = start
    while cur <= end:
        if cur.weekday() != 5:           # skip Saturday; keep Sun (FX evening) + Mon-Fri
            days.append(cur)
        cur += timedelta(days=1)

    rows: list[dict] = []
    done = err = 0
    print(f"  {sym} {year}: {len(days)} days, {threads}t [{cfg['code']}] …", flush=True)
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futs = {pool.submit(fetch_day, cfg["code"], d, cfg["df"]): d for d in days}
        for fut in as_completed(futs):
            try:
                rows.extend(fut.result())
            except Exception:
                err += 1
            done += 1
            if done % 40 == 0 or done == len(days):
                print(f"\r    {done}/{len(days)} days  rows={len(rows)} err={err}   ", end="", flush=True)
    print()
    if err:                              # any fetch/decode failure -> do NOT cache a holey year
        print(f"   !! {sym} {year}: {err} fetch/decode failures — NOT cached (re-run to retry)", flush=True)
        return dict(sym=sym, year=year, status="fetch_err", rows=len(rows), errors=err)
    if not rows:
        return dict(sym=sym, year=year, status="empty", rows=0)
    out = (pd.DataFrame(rows).drop_duplicates("ts_utc").sort_values("ts_utc")
           .reset_index(drop=True))
    # ---- loud OHLC-validity guard (complete: high is the max, low is the min) ----
    # A byte-order decode bug (OHLC instead of OCLH) yields ~50% violations; real-data
    # noise is far below 0.1%. FAIL (do not cache) the year if viol_frac > 0.1%.
    o, h, l, c = out["open"], out["high"], out["low"], out["close"]
    eps = 1e-9
    bad = ((h < o - eps) | (h < c - eps) | (h < l - eps) |
           (l > o + eps) | (l > c + eps) |
           (out[["open", "high", "low", "close"]] <= 0).any(axis=1))
    viol = int(bad.sum())
    viol_frac = viol / len(out) if len(out) else 0.0
    if viol_frac > 0.001:
        fdir = CACHE / "_failed"; fdir.mkdir(exist_ok=True)
        out.to_parquet(fdir / f"{sym}_{year}.parquet", compression="snappy")  # inspect, NOT cached
        print(f"   !! OHLC GUARD FAIL {sym} {year}: {viol}/{len(out)} "
              f"({viol_frac:.3%}) > 0.1% — NOT cached (saved to _failed/)", flush=True)
        return dict(sym=sym, year=year, status="ohlc_fail", rows=len(out),
                    ohlc_viol=viol, ohlc_viol_frac=round(viol_frac, 6),
                    start=str(out.ts_utc.min()), end=str(out.ts_utc.max()))
    out.to_parquet(out_pq, compression="snappy")
    r = dict(sym=sym, year=year, status="ok", rows=len(out), ohlc_viol=viol,
             ohlc_viol_frac=round(viol_frac, 6),
             start=str(out.ts_utc.min()), end=str(out.ts_utc.max()))
    if viol:
        print(f"   !! WARNING {sym} {year}: {viol} OHLC violations ({viol_frac:.4%})", flush=True)
    return r


def plan_years(sym: str) -> list[int]:
    """Years to download: backfill (target→existing start) + forward gap (existing end→today) + CAL_YEAR."""
    cfg = INSTR[sym]
    es = datetime.strptime(cfg["es"], "%Y-%m-%d").date()
    ee = datetime.strptime(cfg["ee"], "%Y-%m-%d").date()
    istart = datetime.strptime(cfg["istart"], "%Y-%m-%d").date()
    lo = max(TARGET_START, istart)
    years = set()
    years.update(range(lo.year, es.year + 1))           # backfill (incl. existing-start year, trimmed at assembly)
    years.update(range(ee.year, TODAY.year + 1))        # forward gap
    years.add(CAL_YEAR)                                 # calibration/validation overlap
    return sorted(y for y in years if y >= lo.year)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol")
    ap.add_argument("--group", choices=["P1", "P2fx", "P2idx", "ALL"])
    ap.add_argument("--years", help="e.g. 2007-2017 or 2024")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if a.status:
        tot = 0
        for pq in sorted(CACHE.glob("*.parquet")):
            n = pd.read_parquet(pq, columns=["ts_utc"]).shape[0]
            tot += n
            print(f"  {pq.stem:16} {n:>8} rows")
        print(f"TOTAL cached rows: {tot:,}")
        return

    if a.plan:
        gtot = 0
        for sym, cfg in INSTR.items():
            ys = plan_years(sym)
            gtot += len(ys)
            print(f"  {sym:7} [{cfg['grp']:5}] {len(ys):2}y: {ys[0]}–{ys[-1]} "
                  f"(backfill from {max(TARGET_START.year, datetime.strptime(cfg['istart'],'%Y-%m-%d').year)} "
                  f"to existing {cfg['es']}; fwd to {cfg['ee']})")
        print(f"\nUS2000: SKIP (Dukascopy USSC2000IDXUSD starts 2018-08-08 > existing 2018-01-23)")
        print(f"TOTAL symbol-years to fetch (incl. {CAL_YEAR} cal): {gtot}")
        return

    if a.symbol:
        syms = [a.symbol]
    elif a.group:
        syms = [s for s, c in INSTR.items() if a.group == "ALL" or c["grp"] == a.group]
    else:
        ap.error("need --symbol / --group / --plan / --status")

    results = []
    for sym in syms:
        if a.years and "-" in a.years:
            y0, y1 = (int(x) for x in a.years.split("-"))
            yrs = list(range(y0, y1 + 1))
        elif a.years:
            yrs = [int(a.years)]
        else:
            yrs = plan_years(sym)
        for y in yrs:
            r = download_year(sym, y, threads=a.threads, force=a.force)
            results.append(r)
            print(f"   -> {r}", flush=True)
    (BASE / "reports").mkdir(exist_ok=True)
    with open(BASE / "reports" / "download_status.json", "w") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
