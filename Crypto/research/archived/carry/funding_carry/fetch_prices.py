"""
fetch_prices.py — Hyperliquid 8h candle price fetcher for carry walk-forward.

Fetches all non-delisted perps, caches per-asset CSVs to
data/funding_carry/prices/{ASSET}_8h.csv.

Usage:
    python -m strategies.funding_carry.fetch_prices
    python -m strategies.funding_carry.fetch_prices --force
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT  = Path(__file__).resolve().parents[2]
PRICES_DIR = REPO_ROOT / "data" / "funding_carry" / "prices"
PRICES_DIR.mkdir(parents=True, exist_ok=True)

MAINNET_URL = "https://api.hyperliquid.xyz/info"
INTERVAL    = "8h"
EPOCH_MS    = 1_682_000_000_000   # 2023-04-21 (before HL launch)
SLEEP_S     = 0.12


def _post(payload: dict, retries: int = 5) -> list:
    for attempt in range(retries):
        try:
            resp = requests.post(MAINNET_URL, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"      API failed after {retries} attempts: {exc}")
                return []


def fetch_candles(coin: str, start_ms: int = EPOCH_MS,
                  end_ms: int | None = None) -> pd.DataFrame:
    """Fetch 8h OHLCV from Hyperliquid. Returns DataFrame with timestamp, open, close."""
    if end_ms is None:
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    data = _post({
        "type": "candleSnapshot",
        "req": {
            "coin":      coin,
            "interval":  INTERVAL,
            "startTime": start_ms,
            "endTime":   end_ms,
        }
    })

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["t"], unit="ms", utc=True)
    for col, name in [("o", "open"), ("c", "close"), ("h", "high"), ("l", "low")]:
        df[name] = df[col].astype(float)
    df = (df[["timestamp", "open", "high", "low", "close"]]
            .drop_duplicates("timestamp")
            .sort_values("timestamp")
            .reset_index(drop=True))
    return df


def fetch_prices_universe(assets: list[str] | None = None, force: bool = False) -> None:
    """Fetch 8h candles for all assets, skip cached unless --force."""
    if assets is None:
        from strategies.funding_carry.fetch_funding import get_universe
        assets = get_universe()

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    fetched, cached, failed = 0, 0, 0

    for i, coin in enumerate(assets, 1):
        csv_path = PRICES_DIR / f"{coin}_8h.csv"
        if csv_path.exists() and not force:
            cached += 1
            continue

        df = fetch_candles(coin, start_ms=EPOCH_MS, end_ms=now_ms)
        if df.empty:
            print(f"  [{i:3d}/{len(assets)}] {coin:<12} NO DATA")
            failed += 1
        else:
            df.to_csv(csv_path, index=False)
            print(f"  [{i:3d}/{len(assets)}] {coin:<12} {len(df):>6,} bars  "
                  f"({df['timestamp'].min().date()} → {df['timestamp'].max().date()})")
            fetched += 1

        time.sleep(SLEEP_S)

    print(f"\nDone: {fetched} fetched, {cached} cached, {failed} no-data.")


def load_prices_wide(assets: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load cached 8h CSVs for given assets.
    Returns (px_open, px_close): wide DataFrames (timestamp × asset).
    """
    opens, closes = [], []
    for coin in assets:
        csv_path = PRICES_DIR / f"{coin}_8h.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
        opens.append(df[["open"]].rename(columns={"open": coin}))
        closes.append(df[["close"]].rename(columns={"close": coin}))

    if not opens:
        return pd.DataFrame(), pd.DataFrame()

    px_open  = pd.concat(opens,  axis=1).sort_index()
    px_close = pd.concat(closes, axis=1).sort_index()
    return px_open, px_close


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",  action="store_true", help="Re-fetch even if cached")
    parser.add_argument("--asset",  default=None,        help="Single asset to fetch")
    args = parser.parse_args()

    assets = [args.asset.upper()] if args.asset else None
    fetch_prices_universe(assets, force=args.force)
