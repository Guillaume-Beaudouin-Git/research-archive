"""
Forex/data/binance_klines_downloader.py
========================================
Binance Spot klines (1-min OHLCV) for crypto symbols not covered by Dukascopy.

Why this exists: Dukascopy hosts BTC/ETH/LTC/BCH/XRP only. FTMO's expanded
crypto roster (post-2025-07) adds SOL/ADA/DOT/DOGE/AVAX/LINK/BNB/XLM/AAVE/etc.
that we need to research-test. Binance Spot is the cleanest free source.

Output schema (aligned with data/panels/m5_indices/*.csv):
    timestamp_utc, open, high, low, close, tick_volume, spread

    - tick_volume = number_of_trades from Binance kline (proxy for MT5 tick_volume)
    - spread       = 0 (Binance Spot = no broker spread; this column kept for
                     downstream pipelines that expect it)

Output naming convention: our_name (BTCUSDT → BTCUSD), matching MT5/FTMO style.

Usage:
    /usr/bin/python3 binance_klines_downloader.py --symbol SOLUSD --start 2020-01-01
    /usr/bin/python3 binance_klines_downloader.py --all --start 2020-01-01
    /usr/bin/python3 binance_klines_downloader.py --status

Speed: ~4 min/symbol for 5y of 1-min (≈ 2.6k API calls at 100ms throttle).

Note: Binance returns 1000 klines/call max. We paginate by startTime.
Rate limit: 1200 weight/min. klines = 1 weight per call → 100ms sleep is safe.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://api.binance.com/api/v3/klines"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "panels" / "m5_indices"

# our_name (FTMO/MT5-style) → Binance Spot symbol (USDT pair)
SYMBOLS: dict[str, str] = {
    # BTCUSD intentionally omitted from default --all (user has MT5 FTMO version).
    # Use --symbol BTCUSD to download explicitly.
    "ETHUSD":  "ETHUSDT",
    "SOLUSD":  "SOLUSDT",
    "ADAUSD":  "ADAUSDT",
    "DOTUSD":  "DOTUSDT",
    "DOGEUSD": "DOGEUSDT",
    "AVAXUSD": "AVAXUSDT",
    "LINKUSD": "LINKUSDT",
    "BNBUSD":  "BNBUSDT",
    "XLMUSD":  "XLMUSDT",
    "AAVEUSD": "AAVEUSDT",
    "LTCUSD":  "LTCUSDT",
    "BCHUSD":  "BCHUSDT",
    "XRPUSD":  "XRPUSDT",
    "DASHUSD": "DASHUSDT",
    "NEOUSD":  "NEOUSDT",
    "XMRUSD":  "XMRUSDT",   # Binance delisted Feb 2024; will halt at delist date
    "BTCUSD":  "BTCUSDT",   # available via --symbol but skipped from --all
}

INTERVAL = "1m"
LIMIT = 1000
THROTTLE_S = 0.1
MAX_RETRIES = 6
RETRY_BACKOFF_BASE = 2.0  # seconds; doubles each attempt


def _fetch_page(symbol_binance: str, start_ms: int, end_ms: int) -> list[list]:
    params = {
        "symbol": symbol_binance,
        "interval": INTERVAL,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": LIMIT,
    }
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(API, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(60)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            last_err = e
            wait = RETRY_BACKOFF_BASE * (2 ** attempt)
            print(f"\n  [retry {attempt + 1}/{MAX_RETRIES}] {type(e).__name__}: {e} — waiting {wait:.0f}s",
                  flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Binance fetch failed after {MAX_RETRIES} retries: {last_err}")


def download_symbol(our_name: str, start: str, end: str | None, out_dir: Path) -> Path | None:
    symbol_binance = SYMBOLS[our_name]
    out_path = out_dir / f"{our_name}_M1.csv"
    if out_path.exists() and out_path.stat().st_size > 1_000_000:
        print(f"  SKIP {our_name}: {out_path.name} exists ({out_path.stat().st_size / 1e6:.1f} MB)")
        return out_path

    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC") if end else pd.Timestamp.now(tz="UTC")
    cursor_ms = int(start_ts.timestamp() * 1000)
    end_ms = int(end_ts.timestamp() * 1000)

    rows: list[list] = []
    n_calls = 0
    last_flush_n = 0
    tmp_path = out_dir / f".{our_name}_M1.partial.parquet"
    while cursor_ms < end_ms:
        try:
            page = _fetch_page(symbol_binance, cursor_ms, end_ms)
        except RuntimeError as e:
            print(f"\n  ABORT {our_name}: {e}")
            print(f"  Partial data preserved at {tmp_path} ({len(rows)} bars)")
            if rows:
                pd.DataFrame(rows).to_parquet(tmp_path, compression="snappy")
            return None
        n_calls += 1
        if not page:
            break
        rows.extend(page)
        last_close_ms = page[-1][6]
        next_cursor = last_close_ms + 1
        if next_cursor <= cursor_ms:
            break
        cursor_ms = next_cursor
        if n_calls % 50 == 0:
            print(f"\r  {our_name}: {n_calls} calls, {len(rows)} bars, "
                  f"@ {pd.Timestamp(cursor_ms, unit='ms', tz='UTC')}",
                  end="", flush=True)
        if len(rows) - last_flush_n >= 500_000:
            pd.DataFrame(rows).to_parquet(tmp_path, compression="snappy")
            last_flush_n = len(rows)
        time.sleep(THROTTLE_S)
    print()

    if not rows:
        print(f"  WARNING: no data for {our_name} ({symbol_binance})")
        return None

    df = pd.DataFrame(rows, columns=[
        "open_time_ms", "open", "high", "low", "close", "volume",
        "close_time_ms", "quote_volume", "n_trades",
        "taker_buy_base_volume", "taker_buy_quote_volume", "ignore",
    ])
    df["timestamp_utc"] = pd.to_datetime(df["open_time_ms"], unit="ms", utc=True)
    out = pd.DataFrame({
        "timestamp_utc": df["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "open": df["open"].astype(float),
        "high": df["high"].astype(float),
        "low": df["low"].astype(float),
        "close": df["close"].astype(float),
        "tick_volume": df["n_trades"].astype(int),
        "spread": 0,
    }).drop_duplicates(subset="timestamp_utc").sort_values("timestamp_utc")

    out.to_csv(out_path, index=False)
    if tmp_path.exists():
        tmp_path.unlink()
    print(f"  OK {our_name}: {len(out)} bars → {out_path.name}  "
          f"({pd.Timestamp(rows[0][0], unit='ms', tz='UTC')} → "
          f"{pd.Timestamp(rows[-1][0], unit='ms', tz='UTC')})")
    return out_path


def print_status(out_dir: Path) -> None:
    print("\n" + "=" * 78)
    print(f"BINANCE M1 CACHE STATUS — {out_dir}")
    print("=" * 78)
    for name in SYMBOLS:
        p = out_dir / f"{name}_M1.csv"
        if not p.exists():
            print(f"  {name:<10}  -- missing --")
            continue
        df = pd.read_csv(p, usecols=["timestamp_utc"])
        print(f"  {name:<10}  {len(df):>8} bars  "
              f"{df['timestamp_utc'].iloc[0]} → {df['timestamp_utc'].iloc[-1]}  "
              f"{p.stat().st_size / 1e6:.1f} MB")
    print("=" * 78)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default=None,
                    help=f"Single symbol (our_name). Options: {sorted(SYMBOLS)}")
    ap.add_argument("--all", action="store_true", help="Download all symbols")
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.status:
        print_status(out_dir)
        return

    if args.symbol:
        if args.symbol not in SYMBOLS:
            ap.error(f"Unknown --symbol '{args.symbol}'. Options: {sorted(SYMBOLS)}")
        download_symbol(args.symbol, args.start, args.end, out_dir)
    elif args.all:
        for name in SYMBOLS:
            print(f"\n=== {name} ===")
            download_symbol(name, args.start, args.end, out_dir)
    else:
        ap.error("Specify --symbol, --all, or --status")


if __name__ == "__main__":
    main()
