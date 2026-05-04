"""
Binance public REST API fetcher — 36-month hourly OHLCV.

No API key required. Uses /api/v3/klines with 1h interval.
Paginates with startTime cursor (1000 bars per request).
Rate limit: 1200 weight/min; klines = 2 weight → max 600 req/min.
We use 0.12s sleep → ~500 req/min (safe margin).

Usage:
    python -m strategies.pairs_trading.binance_fetcher
    python -m strategies.pairs_trading.binance_fetcher --symbol BTC
"""
from __future__ import annotations

import argparse
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR   = REPO_ROOT / "data" / "pairs_trading" / "binance"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
INTERVAL       = "1h"
LIMIT          = 1000          # max bars per request
SLEEP_S        = 0.12          # ~500 req/min well under 600 limit
MONTHS_BACK    = 36

SYMBOL_MAP: dict[str, str] = {
    "AAVE": "AAVEUSDT",
    "ADA":  "ADAUSDT",
    "ATOM": "ATOMUSDT",
    "AVAX": "AVAXUSDT",
    "BNB":  "BNBUSDT",
    "BTC":  "BTCUSDT",
    "DOGE": "DOGEUSDT",
    "DOT":  "DOTUSDT",
    "ENA":  "ENAUSDT",
    "ETH":  "ETHUSDT",
    "INJ":  "INJUSDT",
    "LDO":  "LDOUSDT",
    "LINK": "LINKUSDT",
    "NEAR": "NEARUSDT",
    "OP":   "OPUSDT",
    "SOL":  "SOLUSDT",
    "TIA":  "TIAUSDT",
}

# Known late-listing symbols; fetch from these dates at earliest
LISTING_FLOORS: dict[str, datetime] = {
    "ENA": datetime(2024, 3, 29, tzinfo=timezone.utc),   # ENA listed ~Apr 2024
    "TIA": datetime(2023, 9, 25, tzinfo=timezone.utc),   # TIA listed ~Oct 2023
    "LDO": datetime(2022, 11,  1, tzinfo=timezone.utc),  # LDO listed ~Nov 2022
}

SHORT_HISTORY_THRESHOLD = 30  # flag if < 30 months of data


# ---------------------------------------------------------------------------
# Core fetch
# ---------------------------------------------------------------------------

def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def fetch_symbol(sym: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame | None:
    """
    Fetch hourly OHLCV for one Binance symbol between start_dt and end_dt.
    Handles pagination, 429 back-off, and basic sanity checks.
    """
    binance_sym = SYMBOL_MAP.get(sym)
    if binance_sym is None:
        print(f"  [{sym}] no Binance mapping — skip")
        return None

    records = []
    cursor  = _ms(start_dt)
    end_ms  = _ms(end_dt)

    while cursor < end_ms:
        params = {
            "symbol":    binance_sym,
            "interval":  INTERVAL,
            "startTime": cursor,
            "endTime":   end_ms,
            "limit":     LIMIT,
        }
        for attempt in range(5):
            try:
                resp = requests.get(BINANCE_KLINES, params=params, timeout=20)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 60))
                    print(f"  [{sym}] 429 rate-limit — sleeping {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                batch = resp.json()
                break
            except requests.RequestException as exc:
                if attempt == 4:
                    print(f"  [{sym}] request failed after 5 attempts: {exc}")
                    return None
                time.sleep(2 ** attempt)
        else:
            return None

        if not batch:
            break

        records.extend(batch)
        # Advance cursor past the last returned bar
        cursor = int(batch[-1][0]) + 3_600_000   # +1 hour in ms

        if len(batch) < LIMIT:
            break   # last page

        time.sleep(SLEEP_S)

    if not records:
        print(f"  [{sym}] no data returned")
        return None

    df = pd.DataFrame(records, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "n_trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])

    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(sym: str, df: pd.DataFrame, start_dt: datetime) -> dict:
    """Return a validation summary row."""
    n      = len(df)
    t_min  = df["timestamp"].min()
    t_max  = df["timestamp"].max()

    expected_months = MONTHS_BACK
    if sym in LISTING_FLOORS:
        months_avail = (t_max - LISTING_FLOORS[sym]).days // 30
        expected_months = min(MONTHS_BACK, months_avail)

    # Expected bars from first available date to end
    expected_bars = int((t_max - t_min).total_seconds() / 3600) + 1
    missing_pct   = max(0.0, 1 - n / max(expected_bars, 1)) * 100

    zero_vol  = int((df["volume"] == 0).sum())
    neg_price = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())

    months_available = (t_max - t_min).days / 30.4
    short_flag = months_available < SHORT_HISTORY_THRESHOLD

    return {
        "symbol":      sym,
        "first_date":  str(t_min.date()),
        "last_date":   str(t_max.date()),
        "n_bars":      n,
        "missing_pct": round(missing_pct, 3),
        "zero_vol_bars": zero_vol,
        "neg_price_bars": neg_price,
        "months_available": round(months_available, 1),
        "short_history_flag": short_flag,
        "warn": (missing_pct > 2) or neg_price > 0,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_universe(symbols: list[str] | None = None, force: bool = False) -> pd.DataFrame:
    """
    Fetch all symbols, save per-symbol CSVs, return validation summary DataFrame.
    """
    if symbols is None:
        symbols = list(SYMBOL_MAP.keys())

    now       = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_36m = now - relativedelta(months=MONTHS_BACK)
    print(f"Binance hourly fetch: {start_36m.date()} → {now.date()}")
    print(f"Target symbols: {symbols}\n")

    summaries = []

    for sym in symbols:
        csv_path = OUT_DIR / f"{sym}_1h.csv"

        if csv_path.exists() and not force:
            df = pd.read_csv(csv_path, parse_dates=["timestamp"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            print(f"  [{sym}] loaded from cache ({len(df)} bars)")
        else:
            # Respect listing floor
            start = max(start_36m, LISTING_FLOORS.get(sym, start_36m))
            print(f"  [{sym}] fetching {start.date()} → {now.date()} ...", end=" ", flush=True)
            df = fetch_symbol(sym, start, now)
            if df is None:
                print("FAILED")
                summaries.append({
                    "symbol": sym, "first_date": None, "last_date": None,
                    "n_bars": 0, "missing_pct": 100, "zero_vol_bars": 0,
                    "neg_price_bars": 0, "months_available": 0,
                    "short_history_flag": True, "warn": True,
                })
                continue
            df.to_csv(csv_path, index=False)
            print(f"{len(df)} bars saved")

        v = validate(sym, df, start_36m)
        summaries.append(v)

        if v["warn"]:
            print(f"    ⚠  {sym}: missing={v['missing_pct']:.1f}%  "
                  f"zero_vol={v['zero_vol_bars']}  neg_price={v['neg_price_bars']}")
        if v["short_history_flag"]:
            print(f"    ⚠  {sym}: only {v['months_available']:.1f} months available "
                  f"(< {SHORT_HISTORY_THRESHOLD})")

    summary_df = pd.DataFrame(summaries)
    summary_path = OUT_DIR / "fetch_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\nValidation summary saved to {summary_path}")
    print(summary_df[["symbol", "first_date", "n_bars", "missing_pct",
                       "months_available", "warn"]].to_string(index=False))
    return summary_df


def load_universe_wide(symbols: list[str] | None = None) -> pd.DataFrame:
    """
    Load all per-symbol CSVs and return wide DataFrame: timestamp × symbol → close.
    Drops symbols with > 2% missing bars.
    """
    if symbols is None:
        symbols = list(SYMBOL_MAP.keys())

    frames = []
    for sym in symbols:
        csv_path = OUT_DIR / f"{sym}_1h.csv"
        if not csv_path.exists():
            print(f"  [{sym}] CSV not found — run fetch_universe() first")
            continue
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")[["open", "high", "low", "close", "volume"]]
        df.columns = pd.MultiIndex.from_product([[sym], df.columns])
        frames.append(df)

    if not frames:
        raise RuntimeError("No Binance data found. Run fetch_universe() first.")

    combined = pd.concat(frames, axis=1).sort_index()
    return combined


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=None, help="Single symbol to fetch (default: all)")
    parser.add_argument("--force",  action="store_true", help="Re-download even if cached")
    args = parser.parse_args()

    syms = [args.symbol.upper()] if args.symbol else None
    fetch_universe(syms, force=args.force)
