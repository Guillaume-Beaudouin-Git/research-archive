"""Fetch Deribit DVOL daily index for BTC or ETH, save to data/vrp/cache/<CCY>_dvol_1d.parquet.

Schema mirrors existing BTC_dvol_1d.parquet:
    DatetimeIndex name='timestamp', tz=UTC, daily 00:00 UTC
    single column 'dvol' float64
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

API = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
CACHE_DIR = Path(__file__).resolve().parents[1] / "cache"
DAY_MS = 86_400_000
CHUNK_DAYS = 365  # API caps result rows; pull a year at a time


def _fetch_chunk(currency: str, start_ms: int, end_ms: int) -> list[list[float]]:
    params = {
        "currency": currency,
        "start_timestamp": start_ms,
        "end_timestamp": end_ms,
        "resolution": "86400",
    }
    r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    if "result" not in payload:
        raise RuntimeError(f"Deribit error payload: {payload}")
    return payload["result"]["data"]


def fetch_dvol(currency: str, start: str = "2021-03-01", end: str | None = None) -> pd.DataFrame:
    start_dt = pd.Timestamp(start, tz="UTC")
    end_dt = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    rows: list[list[float]] = []
    cursor = start_ms
    while cursor < end_ms:
        chunk_end = min(cursor + CHUNK_DAYS * DAY_MS, end_ms)
        chunk = _fetch_chunk(currency, cursor, chunk_end)
        if not chunk:
            cursor = chunk_end
            continue
        rows.extend(chunk)
        last_ts = chunk[-1][0]
        cursor = last_ts + DAY_MS
        time.sleep(0.1)  # be polite

    if not rows:
        raise RuntimeError(f"No data returned for {currency} between {start} and {end}")

    df = pd.DataFrame(rows, columns=["ts_ms", "open", "high", "low", "close"])
    df = df.drop_duplicates(subset="ts_ms").sort_values("ts_ms")
    df["timestamp"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    out = df.set_index("timestamp")[["close"]].rename(columns={"close": "dvol"})
    out["dvol"] = out["dvol"].astype("float64") / 100.0  # API returns vol points (e.g. 65.4) → 0.654
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--currency", choices=["BTC", "ETH"], required=True)
    ap.add_argument("--start", default="2021-03-01")
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    df = fetch_dvol(args.currency, args.start, args.end)
    out_path = CACHE_DIR / f"{args.currency}_dvol_1d.parquet"
    df.to_parquet(out_path)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"Range: {df.index.min()} → {df.index.max()}")
    print(f"Head:\n{df.head(3)}")
    print(f"Tail:\n{df.tail(3)}")


if __name__ == "__main__":
    main()
