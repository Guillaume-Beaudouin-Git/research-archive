"""
data_prep.py — H31 CS-FS Delta-Neutral Carry
Build funding_daily.parquet, price_daily.parquet, universe_mask.parquet.
Idempotent: if all three parquets exist, exits early.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
FUNDING_DIR = REPO_ROOT / "data" / "funding_carry"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

BACKTEST_START = pd.Timestamp("2024-01-01", tz="UTC")
BACKTEST_END   = pd.Timestamp("2026-05-05", tz="UTC")
PRICE_FETCH_START = "2023-06-01"  # buffer before backtest start for rolling warm-up
ELIGIBILITY_DAYS = 180

# HL ticker → Binance base (None = no Binance equivalent, skip price)
SYMBOL_MAP: dict[str, str | None] = {
    "kPEPE":  "PEPE",
    "kSHIB":  "SHIB",
    "kBONK":  "BONK",
    "kLUNC":  "LUNC",
    "kFLOKI": "FLOKI",
    "kDOGS":  "DOGS",
    "kNEIRO": "NEIRO",
    "kSHIB": "SHIB",
}


def _binance_symbol(hl_ticker: str) -> str | None:
    if hl_ticker in SYMBOL_MAP:
        return SYMBOL_MAP[hl_ticker]
    return hl_ticker


def _fetch_binance_daily(base: str, start: str, end_ts: pd.Timestamp) -> pd.Series | None:
    """Fetch Binance daily close price for {base}USDT perp, fallback to spot."""
    for market_type, url_base in [
        ("perp", "https://fapi.binance.com/fapi/v1/klines"),
        ("spot", "https://api.binance.com/api/v3/klines"),
    ]:
        symbol = f"{base}USDT" if market_type == "spot" else f"{base}USDT"
        start_ms = int(pd.Timestamp(start).timestamp() * 1000)
        end_ms   = int(end_ts.timestamp() * 1000)
        rows: list[list] = []
        cursor = start_ms
        while cursor < end_ms:
            try:
                r = requests.get(
                    url_base,
                    params={"symbol": symbol, "interval": "1d",
                            "startTime": cursor, "endTime": end_ms, "limit": 1000},
                    timeout=15,
                )
            except Exception:
                break
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            rows.extend(batch)
            cursor = int(batch[-1][0]) + 86_400_000
            time.sleep(0.05)
        if rows:
            ts = pd.to_datetime([x[0] for x in rows], unit="ms", utc=True).normalize()
            closes = pd.Series([float(x[4]) for x in rows], index=ts, name=base)
            return closes.groupby(level=0).last()
    return None


def load_funding() -> pd.DataFrame:
    """Load all funding CSVs → daily sum of 3 × 8h payments (wide: date × asset)."""
    summary = pd.read_csv(FUNDING_DIR / "fetch_summary.csv")
    summary["first_date"] = pd.to_datetime(summary["first_date"])
    assets = summary[summary["n_rows"] > 0]["asset"].tolist()

    frames: list[pd.DataFrame] = []
    for asset in assets:
        csv_path = FUNDING_DIR / f"{asset}_funding.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        # column named funding_rate_1h but contains 8h payment rates
        df = df.rename(columns={"funding_rate_1h": "rate_8h"})
        df["date"] = df["timestamp"].dt.normalize()
        # sum 3 daily 8h payments → daily total funding rate
        daily = df.groupby("date")["rate_8h"].sum().rename(asset)
        frames.append(daily)

    wide = pd.concat(frames, axis=1)
    wide.index = pd.to_datetime(wide.index, utc=True)
    return wide.sort_index()


def build_universe_mask(funding: pd.DataFrame) -> pd.DataFrame:
    """
    Boolean mask: True when asset has ≥ ELIGIBILITY_DAYS of HL history at date t.
    Uses first non-NaN date in funding data as first_date proxy.
    """
    first_dates = funding.apply(lambda col: col.first_valid_index())
    mask = pd.DataFrame(False, index=funding.index, columns=funding.columns)
    for asset in funding.columns:
        fd = first_dates[asset]
        if fd is None:
            continue
        eligible_from = fd + pd.Timedelta(days=ELIGIBILITY_DAYS)
        mask.loc[mask.index >= eligible_from, asset] = True
    return mask


def fetch_prices(assets: list[str], end_ts: pd.Timestamp) -> pd.DataFrame:
    """Fetch Binance daily close for each asset."""
    cache_path = RESULTS_DIR / "price_daily.parquet"
    if cache_path.exists():
        print("  price_daily.parquet already cached — skipping fetch")
        return pd.read_parquet(cache_path)

    frames: dict[str, pd.Series] = {}
    n = len(assets)
    for i, asset in enumerate(assets):
        base = _binance_symbol(asset)
        if base is None:
            print(f"  [{i+1}/{n}] {asset}: no Binance equivalent — skipped")
            continue
        series = _fetch_binance_daily(base, PRICE_FETCH_START, end_ts)
        if series is not None:
            frames[asset] = series
            print(f"  [{i+1}/{n}] {asset} ({base}): {len(series)} rows")
        else:
            print(f"  [{i+1}/{n}] {asset}: not found on Binance — skipped")

    prices = pd.DataFrame(frames)
    prices.index = pd.to_datetime(prices.index, utc=True)
    prices = prices.sort_index()
    prices.to_parquet(cache_path)
    return prices


def main() -> None:
    fp = RESULTS_DIR / "funding_daily.parquet"
    up = RESULTS_DIR / "universe_mask.parquet"
    pp = RESULTS_DIR / "price_daily.parquet"

    # Load / build funding matrix
    if fp.exists() and up.exists():
        print("Loading cached funding_daily.parquet and universe_mask.parquet...")
        funding = pd.read_parquet(fp)
        universe_mask = pd.read_parquet(up)
    else:
        print("Loading funding CSVs...")
        funding = load_funding()
        print(f"  Funding matrix: {funding.shape} ({funding.index[0].date()} → {funding.index[-1].date()})")

        universe_mask = build_universe_mask(funding)
        print(f"  Universe mask built. N per date sample:")
        for d in ["2024-01-01", "2024-07-01", "2025-01-01"]:
            n = universe_mask.loc[d].sum() if d in universe_mask.index else 0
            print(f"    {d}: N={n}")

        # Trim to backtest window (with pre-period for rolling warm-up)
        warm_start = BACKTEST_START - pd.Timedelta(days=90)
        funding = funding.loc[funding.index >= warm_start]
        universe_mask = universe_mask.loc[universe_mask.index >= warm_start]

        funding.to_parquet(fp)
        universe_mask.to_parquet(up)
        print(f"  Saved funding_daily.parquet + universe_mask.parquet")

    # Fetch prices for all ever-eligible assets
    ever_eligible = universe_mask.columns[universe_mask.any()].tolist()
    print(f"\nFetching Binance prices for {len(ever_eligible)} assets...")
    prices = fetch_prices(ever_eligible, BACKTEST_END + pd.Timedelta(days=1))

    # Trim prices to same window as funding
    prices = prices.loc[prices.index >= funding.index[0]]
    prices = prices.loc[prices.index <= BACKTEST_END]
    prices.to_parquet(pp)
    print(f"\nPrice matrix: {prices.shape}")

    # Summary
    print("\n=== DATA PREP COMPLETE ===")
    print(f"Funding: {funding.shape}")
    print(f"Universe mask: {universe_mask.shape}")
    print(f"Prices: {prices.shape}")
    eligible_at_start = universe_mask.loc["2024-01-01"].sum()
    print(f"N eligible at backtest start (2024-01-01): {eligible_at_start}")
    print(f"Missing prices (ever-eligible assets): {set(ever_eligible) - set(prices.columns)}")


if __name__ == "__main__":
    main()
