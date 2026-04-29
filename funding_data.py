"""
funding_data.py

Fetch historical funding rates from Hyperliquid mainnet for 10 symbols,
enrich with 2-year hourly price data from yfinance, and save to
data/funding_rates.csv.

IMPORTANT NOTE: Hyperliquid charges funding HOURLY (not 8-hourly like Binance).
  Annualisation factor: rate × 24 × 365 = 8760 × rate
  The task description assumed 8h funding (× 3 × 365) — corrected here.

API:
  POST https://api.hyperliquid.xyz/info
  Funding history:
    {"type": "fundingHistory", "coin": "BTC", "startTime": <epoch_ms>}
    Returns ≤ 500 records per call; paginate by advancing startTime.
    Fields per record: coin, fundingRate, premium, time
    NOTE: mark/oracle prices are NOT in historical funding endpoint.

  Historical candle API only provides ~208 days of data (5001-candle limit),
  so prices are sourced from yfinance (730 days of 1h data).
  oracle_price is derived as: mark_price / (1 + premium)
  where premium = (mark - oracle) / oracle from the funding record.

Output columns:
  timestamp    - UTC, hourly-floored
  symbol       - Hyperliquid coin name (e.g. BTC)
  funding_rate - raw per-hour rate as decimal (e.g. 0.0001 = 0.01%/hr)
  mark_price   - from yfinance close price (NaN outside 730-day window)
  oracle_price - derived from mark_price and premium (NaN without mark_price)
"""

import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# ── Configuration ──────────────────────────────────────────────────────────────
MAINNET_URL = "https://api.hyperliquid.xyz/info"
SYMBOLS     = ["BTC", "ETH", "SOL", "AVAX", "LINK", "DOGE", "ARB", "OP", "SUI", "WIF"]

# Yahoo Finance tickers (SUI uses numeric ID as plain SUI-USD is delisted there)
YF_TICKERS = {
    "BTC":  "BTC-USD",
    "ETH":  "ETH-USD",
    "SOL":  "SOL-USD",
    "AVAX": "AVAX-USD",
    "LINK": "LINK-USD",
    "DOGE": "DOGE-USD",
    "ARB":  "ARB-USD",
    "OP":   "OP-USD",
    "SUI":  "SUI20947-USD",
    "WIF":  "WIF-USD",
}

# Annualisation for hourly funding: 24 h/day × 365 days = 8760
ANNUALIZE  = 24 * 365

OUTPUT_DIR  = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "funding_rates.csv")

# Go back further than any available HL data
EPOCH_MS = 1_600_000_000_000  # 2020-09-13 UTC


# ── API helpers ────────────────────────────────────────────────────────────────
def _post(payload: dict, retries: int = 3) -> list:
    """POST to Hyperliquid /info endpoint with exponential-backoff retry."""
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


def fetch_funding_history(coin: str) -> pd.DataFrame:
    """
    Paginate through all hourly funding records for *coin*.

    Returns DataFrame with columns: timestamp (UTC, floored to hour),
    symbol, funding_rate, premium.
    """
    records  = []
    start_ms = EPOCH_MS

    while True:
        batch = _post({"type": "fundingHistory", "coin": coin, "startTime": start_ms})
        if not batch:
            break
        records.extend(batch)
        if len(batch) < 500:
            break                           # last page
        start_ms = batch[-1]["time"] + 1   # advance past last record
        time.sleep(0.15)                    # ~6 req/s courtesy cap

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["timestamp"]    = pd.to_datetime(df["time"], unit="ms", utc=True).dt.floor("h")
    df["funding_rate"] = df["fundingRate"].astype(float)
    df["premium"]      = df["premium"].astype(float)
    df["symbol"]       = coin
    return (df[["timestamp", "symbol", "funding_rate", "premium"]]
              .drop_duplicates("timestamp")
              .reset_index(drop=True))


def fetch_prices(coin: str) -> pd.DataFrame:
    """
    Fetch 2 years of hourly closing prices from yfinance.

    Returns DataFrame with columns: timestamp (UTC, floored to hour),
    mark_price.
    """
    import yfinance as yf

    ticker = YF_TICKERS[coin]
    raw    = yf.download(ticker, period="730d", interval="1h",
                          auto_adjust=True, progress=False)

    if raw.empty:
        return pd.DataFrame(columns=["timestamp", "mark_price"])

    # yfinance ≥1.0 returns multi-level columns: ('Close', '<ticker>')
    close = raw["Close"].iloc[:, 0]
    reset = close.reset_index()
    reset.columns = ["timestamp", "mark_price"]
    reset["timestamp"] = pd.to_datetime(reset["timestamp"], utc=True).dt.floor("h")
    return reset[["timestamp", "mark_price"]].dropna().reset_index(drop=True)


# ── Build CSV ──────────────────────────────────────────────────────────────────
def build_csv() -> pd.DataFrame:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_dfs = []

    for coin in SYMBOLS:
        print(f"  {coin}: fetching funding rates ...", end=" ", flush=True)
        try:
            fund_df = fetch_funding_history(coin)
            if fund_df.empty:
                print("NO DATA — skipping")
                continue

            n_fund = len(fund_df)
            print(f"{n_fund:,} records | fetching prices ...", end=" ", flush=True)

            price_df = fetch_prices(coin)
            n_price  = len(price_df)

            # Left-join: all funding rows kept, prices filled where available
            merged = fund_df.merge(price_df, on="timestamp", how="left")

            # Derive oracle_price: premium ≈ (mark - oracle)/oracle
            # → oracle = mark / (1 + premium)
            merged["oracle_price"] = np.where(
                merged["mark_price"].notna(),
                merged["mark_price"] / (1 + merged["premium"]),
                np.nan,
            )

            final = merged[["timestamp", "symbol", "funding_rate",
                             "mark_price", "oracle_price"]]
            all_dfs.append(final)

            n_with_price = merged["mark_price"].notna().sum()
            print(f"done — {n_with_price:,}/{n_fund:,} rows have price data")

        except Exception as exc:
            print(f"ERROR: {exc}")

        time.sleep(0.3)

    if not all_dfs:
        raise RuntimeError("No data fetched for any symbol — aborting.")

    df = pd.concat(all_dfs, ignore_index=True)
    df = df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved {len(df):,} total rows → {OUTPUT_FILE}")
    return df


# ── Summary statistics (Task 1d) ───────────────────────────────────────────────
def print_summary(df: pd.DataFrame) -> None:
    bar = "═" * 80
    print(f"\n{bar}")
    print("TASK 1d — FUNDING RATE SUMMARY STATISTICS")
    print("Note: Hyperliquid funding is HOURLY (task assumed 8h Binance default)")
    print(f"      Annualisation = rate × {ANNUALIZE:,}   |   Binance equiv. = rate × 1095")
    print(bar)

    for coin in SYMBOLS:
        s = df[df["symbol"] == coin].copy()
        if s.empty:
            print(f"\n  {coin}: NO DATA")
            continue

        s = s.sort_values("timestamp")
        rate = s["funding_rate"]
        n         = len(s)
        date_from = s["timestamp"].min().strftime("%Y-%m-%d")
        date_to   = s["timestamp"].max().strftime("%Y-%m-%d")
        mean_ann  = rate.mean() * ANNUALIZE * 100
        std       = rate.std()
        pct_ext   = (rate.abs() > 0.0001).mean() * 100   # |rate| > 0.01%/hr
        r_max     = rate.max()
        r_min     = rate.min()

        print(f"\n  {coin}")
        print(f"    Data points        : {n:>8,}")
        print(f"    Date range         : {date_from} → {date_to}")
        print(f"    Mean ann. rate     : {mean_ann:>+8.2f} %/yr")
        print(f"    Std dev            : {std:.6f}  ({std * 100:.5f} %/hr)")
        print(f"    % |rate| > 0.01%   : {pct_ext:>5.1f}%")
        print(f"    Max rate           : {r_max:>+.6f}  ({r_max * 100:>+.4f} %/hr)")
        print(f"    Min rate           : {r_min:>+.6f}  ({r_min * 100:>+.4f} %/hr)")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("HYPERLIQUID FUNDING RATE DATA PIPELINE")
    print("=" * 60)
    df = build_csv()
    print_summary(df)
    print("\nDone. Run funding_eda.py for exploratory analysis.\n")
