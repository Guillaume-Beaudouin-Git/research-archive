"""
momentum_data.py

Fetch daily OHLCV for 20 Hyperliquid-listed perp symbols from yfinance
(period="max") and save to data/momentum_universe.csv.

Universe: BTC ETH SOL AVAX LINK DOGE ADA DOT MATIC UNI
          AAVE LTC NEAR ARB OP FIL APT SUI SEI TIA

Output columns: date, symbol, open, high, low, close, volume, daily_return
"""

import os
import time
import warnings

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Universe ──────────────────────────────────────────────────────────────────
SYMBOLS = [
    "BTC", "ETH", "SOL", "AVAX", "LINK", "DOGE", "ADA", "DOT", "MATIC", "UNI",
    "AAVE", "LTC", "NEAR", "ARB", "OP", "FIL", "APT", "SUI", "SEI", "TIA",
]

# Verified Yahoo Finance tickers (checked against live data)
YF_TICKERS = {
    "BTC":   "BTC-USD",
    "ETH":   "ETH-USD",
    "SOL":   "SOL-USD",
    "AVAX":  "AVAX-USD",
    "LINK":  "LINK-USD",
    "DOGE":  "DOGE-USD",
    "ADA":   "ADA-USD",
    "DOT":   "DOT-USD",
    "MATIC": "MATIC-USD",
    "UNI":   "UNI7083-USD",
    "AAVE":  "AAVE-USD",
    "LTC":   "LTC-USD",
    "NEAR":  "NEAR-USD",
    "ARB":   "ARB11841-USD",
    "OP":    "OP-USD",
    "FIL":   "FIL-USD",
    "APT":   "APT21794-USD",
    "SUI":   "SUI20947-USD",
    "SEI":   "SEI-USD",
    "TIA":   "TIA22861-USD",
}

MIN_HISTORY_DAYS = 365
OUTPUT_DIR  = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "momentum_universe.csv")


# ── Download ──────────────────────────────────────────────────────────────────

def _extract_col(raw: pd.DataFrame, col: str) -> pd.Series:
    """Handle yfinance >=1.0 multi-level columns."""
    if isinstance(raw.columns, pd.MultiIndex):
        return raw[col].iloc[:, 0]
    return raw[col]


def fetch_symbol(sym: str) -> pd.DataFrame | None:
    """
    Download full daily history for one symbol.

    Returns a clean DataFrame with columns:
        date, symbol, open, high, low, close, volume, daily_return
    or None if insufficient data.
    """
    ticker = YF_TICKERS[sym]
    try:
        raw = yf.download(
            ticker, period="max", interval="1d",
            auto_adjust=True, progress=False,
        )
    except Exception as exc:
        print(f"    ERROR downloading {sym} ({ticker}): {exc}")
        return None

    if raw is None or raw.empty:
        print(f"    {sym}: empty response")
        return None

    close  = _extract_col(raw, "Close")
    open_  = _extract_col(raw, "Open")
    high   = _extract_col(raw, "High")
    low    = _extract_col(raw, "Low")
    volume = _extract_col(raw, "Volume")

    df = pd.DataFrame({
        "date":   close.index,
        "symbol": sym,
        "open":   open_.values,
        "high":   high.values,
        "low":    low.values,
        "close":  close.values,
        "volume": volume.values,
    })

    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.dropna(subset=["close", "open"]).reset_index(drop=True)

    if len(df) < MIN_HISTORY_DAYS:
        print(f"    {sym}: only {len(df)} days — skipped (< {MIN_HISTORY_DAYS})")
        return None

    df["daily_return"] = df["close"].pct_change()
    return df


# ── Build CSV ─────────────────────────────────────────────────────────────────

def build_csv() -> pd.DataFrame:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_dfs = []
    passed, failed = [], []

    for sym in SYMBOLS:
        print(f"  {sym}: downloading ...", end=" ", flush=True)
        df = fetch_symbol(sym)
        if df is None:
            failed.append(sym)
            continue
        all_dfs.append(df)
        passed.append(sym)
        print(f"{len(df):,} days  "
              f"({df['date'].min().date()} → {df['date'].max().date()})")
        time.sleep(0.2)

    if not all_dfs:
        raise RuntimeError("No symbols downloaded successfully.")

    combined = pd.concat(all_dfs, ignore_index=True)
    combined = combined.sort_values(["symbol", "date"]).reset_index(drop=True)
    combined.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Saved {len(combined):,} rows → {OUTPUT_FILE}")
    return combined, passed, failed


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame, passed: list, failed: list) -> None:
    BAR = "═" * 72
    print(f"\n{BAR}")
    print("MOMENTUM UNIVERSE — SUMMARY")
    print(BAR)
    print(f"\n  Symbols downloaded : {len(passed)}/{len(SYMBOLS)}")
    if failed:
        print(f"  Failed / skipped   : {failed}")

    # Per-symbol stats
    print(f"\n  {'Symbol':<6} {'Start':<12} {'End':<12} {'Days':>6}  {'Returns':>8}  Notes")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*6}  {'-'*8}  {'-'*20}")

    for sym in passed:
        s   = df[df["symbol"] == sym]
        n   = len(s)
        t0  = s["date"].min().strftime("%Y-%m-%d")
        t1  = s["date"].max().strftime("%Y-%m-%d")
        ret = s["daily_return"].dropna()
        note = ""
        if n < 500:
            note = "← short history"
        elif n < 730:
            note = "← ~2 yr"
        print(f"  {sym:<6} {t0:<12} {t1:<12} {n:>6,}  "
              f"{ret.mean()*100:>+5.3f}%/d  {note}")

    # Common overlap (all symbols available)
    pivot = df.pivot_table(index="date", columns="symbol", values="close")
    overlap = pivot.dropna(axis=0, how="any")
    if not overlap.empty:
        overlap_start = overlap.index.min().strftime("%Y-%m-%d")
        overlap_end   = overlap.index.max().strftime("%Y-%m-%d")
        overlap_days  = len(overlap)
        print(f"\n  Full-universe overlap  : {overlap_start} → {overlap_end}  "
              f"({overlap_days:,} days)")
    else:
        print("\n  No common date where ALL symbols have data simultaneously.")

    # Partial-universe milestones
    print(f"\n  Universe growth (symbols available):")
    for year in range(2017, 2027):
        start = pd.Timestamp(f"{year}-01-01")
        end   = pd.Timestamp(f"{year}-12-31")
        snap  = pivot[(pivot.index >= start) & (pivot.index <= end)]
        if snap.empty:
            continue
        n_sym = snap.notna().any(axis=0).sum()
        n_full = snap.notna().all(axis=1).sum()
        print(f"    {year}: {n_sym:>2} symbols have some data  |  "
              f"{n_full:>4,} days where all {n_sym} available")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 72)
    print("MOMENTUM UNIVERSE DATA PIPELINE")
    print("=" * 72)
    print()
    df, passed, failed = build_csv()
    print_summary(df, passed, failed)
    print("\nDone. Run momentum_backtest.py for the strategy backtest.\n")
