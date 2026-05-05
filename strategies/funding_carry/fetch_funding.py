"""
fetch_funding.py — Hyperliquid funding rate fetcher for cross-sectional carry study.

Fetches hourly funding rates for all non-delisted Hyperliquid perps.
Filters to assets with ≥ 180 days of history.
Saves per-asset CSVs to data/funding_carry/ and a combined file.

Usage:
    python -m strategies.funding_carry.fetch_funding
    python -m strategies.funding_carry.fetch_funding --force
"""
from __future__ import annotations

import argparse
import time
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT   = Path(__file__).resolve().parents[2]
OUT_DIR     = REPO_ROOT / "data" / "funding_carry"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MAINNET_URL   = "https://api.hyperliquid.xyz/info"
EPOCH_MS      = 1_600_000_000_000   # 2020-09-13 — go back before any HL listing
MIN_DAYS      = 180
SLEEP_S       = 0.15                # ~6 req/s courtesy cap


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _post(payload: dict, retries: int = 5) -> list | dict:
    for attempt in range(retries):
        try:
            resp = requests.post(MAINNET_URL, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"API call failed after {retries} attempts: {exc}")


def get_universe() -> list[str]:
    """Return names of all non-delisted Hyperliquid perpetuals."""
    meta = _post({"type": "meta"})
    assets = []
    for item in meta.get("universe", []):
        if not item.get("isDelisted", False):
            assets.append(item["name"])
    return sorted(assets)


def fetch_funding_history(coin: str) -> pd.DataFrame:
    """
    Paginate through all hourly funding records for coin.
    Returns DataFrame: timestamp (UTC hourly), asset, funding_rate_1h.
    """
    records  = []
    start_ms = EPOCH_MS

    while True:
        batch = _post({"type": "fundingHistory", "coin": coin, "startTime": start_ms})
        if not batch:
            break
        records.extend(batch)
        if len(batch) < 500:
            break
        start_ms = batch[-1]["time"] + 1
        time.sleep(SLEEP_S)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["timestamp"]      = pd.to_datetime(df["time"], unit="ms", utc=True).dt.floor("h")
    df["funding_rate_1h"] = df["fundingRate"].astype(float)
    df["asset"]           = coin
    df = (df[["timestamp", "asset", "funding_rate_1h"]]
            .drop_duplicates("timestamp")
            .sort_values("timestamp")
            .reset_index(drop=True))
    return df


# ---------------------------------------------------------------------------
# Main fetch
# ---------------------------------------------------------------------------

def fetch_all(assets: list[str] | None = None, force: bool = False) -> pd.DataFrame:
    """
    Fetch funding for all (or given) assets.
    Saves per-asset CSVs; returns summary DataFrame.
    Also writes combined CSV for assets with ≥ MIN_DAYS.
    """
    if assets is None:
        print("Querying Hyperliquid meta ...", flush=True)
        assets = get_universe()
        print(f"  {len(assets)} non-delisted perps found\n")

    summaries = []
    cutoff    = datetime.now(timezone.utc) - timedelta(days=MIN_DAYS)

    for i, coin in enumerate(assets, 1):
        csv_path = OUT_DIR / f"{coin}_funding.csv"

        if csv_path.exists() and not force:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            n_days = (df["timestamp"].max() - df["timestamp"].min()).days
            print(f"  [{i:3d}/{len(assets)}] {coin:<12} cached  {n_days}d  {len(df):>7,} rows")
        else:
            print(f"  [{i:3d}/{len(assets)}] {coin:<12} fetching ...", end=" ", flush=True)
            try:
                df = fetch_funding_history(coin)
            except Exception as exc:
                print(f"FAILED: {exc}")
                summaries.append({"asset": coin, "n_rows": 0, "n_days": 0,
                                   "first_date": None, "last_date": None,
                                   "mean_abs_1h": None, "viable_180d": False})
                continue

            if df.empty:
                print("NO DATA")
                summaries.append({"asset": coin, "n_rows": 0, "n_days": 0,
                                   "first_date": None, "last_date": None,
                                   "mean_abs_1h": None, "viable_180d": False})
                continue

            df.to_csv(csv_path, index=False)
            n_days = (df["timestamp"].max() - df["timestamp"].min()).days
            print(f"{len(df):>7,} rows  {n_days}d")

        t_min = df["timestamp"].min()
        t_max = df["timestamp"].max()
        n_days = (t_max - t_min).days
        mean_abs = float(df["funding_rate_1h"].abs().mean())

        summaries.append({
            "asset":        coin,
            "n_rows":       len(df),
            "n_days":       n_days,
            "first_date":   str(t_min.date()),
            "last_date":    str(t_max.date()),
            "mean_abs_1h":  round(mean_abs, 8),
            "viable_180d":  n_days >= MIN_DAYS,
        })

    summary_df = pd.DataFrame(summaries)
    summary_path = OUT_DIR / "fetch_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    viable = summary_df[summary_df["viable_180d"]]
    print(f"\n{len(viable)}/{len(summary_df)} assets have ≥ {MIN_DAYS} days of data")

    # Build combined CSV from viable assets
    print("Building combined CSV ...", end=" ", flush=True)
    frames = []
    for coin in viable["asset"]:
        csv_path = OUT_DIR / f"{coin}_funding.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        frames.append(df)

    if frames:
        combined = pd.concat(frames, ignore_index=True).sort_values(["asset", "timestamp"])
        combined_path = OUT_DIR / "funding_rates_combined.csv"
        combined.to_csv(combined_path, index=False)
        print(f"{len(combined):,} rows → {combined_path.name}")
    else:
        print("no viable assets")

    return summary_df


def load_combined(min_days: int = MIN_DAYS) -> pd.DataFrame:
    """Load combined funding rates, pivot to wide DataFrame: timestamp × asset."""
    path = OUT_DIR / "funding_rates_combined.csv"
    if not path.exists():
        raise RuntimeError("Combined CSV not found — run fetch_all() first.")
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-fetch even if cached")
    parser.add_argument("--asset", default=None, help="Single asset to fetch")
    args = parser.parse_args()

    assets = [args.asset.upper()] if args.asset else None
    fetch_all(assets, force=args.force)
