"""
fetch_data.py — WAV H3 Wikipedia Attention Velocity data pipeline
==================================================================

Fetches:
  1. Wikipedia daily pageviews per token (Wikimedia REST API, no key)
  2. Altcoin daily close prices (yfinance primary, Binance fallback)

Applies universe filters:
  - 404 / redirect broken → exclude
  - Wikipedia history < MIN_WIKI_DAYS (730) → exclude
  - Avg pageviews < MIN_AVG_VIEWS (50/day) → exclude
  - Price history < MIN_PRICE_DAYS (365) → exclude

Outputs:
  data/wiki/{TOKEN}.parquet   — DatetimeIndex, column 'views' (int64)
  data/prices/{TOKEN}.parquet — DatetimeIndex, column 'close' (float64)
  data/universe.json          — validated universe with exclusion reasons

Usage:
  /usr/bin/python3 fetch_data.py
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

# ─── Config ──────────────────────────────────────────────────────────────────

BACKTEST_START = date(2018, 1, 1)
BACKTEST_END   = date(2026, 5, 23)

MIN_WIKI_DAYS  = 730    # FIX 1: require ≥ 2 years of Wikipedia data
MIN_AVG_VIEWS  = 50     # minimum avg daily pageviews (noise floor)
MIN_PRICE_DAYS = 365    # minimum price history days

WIKI_CHUNK_DAYS = 700   # Wikimedia API max ~2 years per request (stay under limit)
WIKI_RATE_SLEEP = 0.05  # 50ms between requests (~20 req/s, well under 200/s limit)

DATA_DIR   = Path(__file__).parent / "data"
WIKI_DIR   = DATA_DIR / "wiki"
PRICES_DIR = DATA_DIR / "prices"

# ─── Pre-registered token → Wikipedia article mapping ────────────────────────
# SAND and GRT pre-excluded (FIX 2).

UNIVERSE: dict[str, str] = {
    "SOL":   "Solana_(blockchain_platform)",
    "BNB":   "BNB_(cryptocurrency)",              # runtime-test: may 404
    "XRP":   "XRP_(cryptocurrency)",              # runtime-test: renamed from Ripple
    "ADA":   "Cardano_(blockchain_platform)",
    "AVAX":  "Avalanche_(blockchain_platform)",
    "DOGE":  "Dogecoin",
    "DOT":   "Polkadot_(cryptocurrency)",
    "MATIC": "Polygon_(blockchain)",
    "TRX":   "TRON_(cryptocurrency)",
    "LINK":  "Chainlink_(blockchain)",
    "LTC":   "Litecoin",
    "ETC":   "Ethereum_Classic",
    "BCH":   "Bitcoin_Cash",
    "XLM":   "Stellar_(payment_network)",
    "ATOM":  "Cosmos_(blockchain)",
    "SUI":   "Sui_(cryptocurrency)",              # expected to fail min_wiki_days
    "APT":   "Aptos_(blockchain)",                # expected to fail min_wiki_days
    "NEAR":  "NEAR_Protocol",
    "FIL":   "Filecoin",
    "ICP":   "Internet_Computer",
    "VET":   "VeChain",
    "ALGO":  "Algorand",
    "EOS":   "EOS.IO",
    "ZEC":   "Zcash",
    "XMR":   "Monero",
    "DASH":  "Dash_(cryptocurrency)",
    "AXS":   "Axie_Infinity",
    "MANA":  "Decentraland",
    "WLD":   "Worldcoin",                         # expected to fail min_wiki_days
    "BAT":   "Basic_Attention_Token",
    "COMP":  "Compound_(DeFi_protocol)",
    "EGLD":  "MultiversX",
    "INJ":   "Injective_Protocol",               # stub risk + short history
    "CRO":   "Cronos_(blockchain)",              # existence uncertain
    "ZIL":   "Zilliqa",
    "WAVES": "Waves_(cryptocurrency)",
    "ONT":   "Ontology_(blockchain)",
    "ICX":   "ICON_(cryptocurrency)",
}

WIKI_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents"


# ─── Wikimedia API ────────────────────────────────────────────────────────────

def _fetch_wiki_chunk(article: str, start: date, end: date) -> Optional[pd.Series]:
    """Fetch daily pageviews for one article, one date chunk. Returns None on 404."""
    article_enc = urllib.parse.quote(article, safe="")
    url = f"{WIKI_BASE}/{article_enc}/daily/{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WAV-research/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    items = data.get("items", [])
    if not items:
        return pd.Series(dtype="int64")
    dates  = pd.to_datetime([it["timestamp"][:8] for it in items], format="%Y%m%d")
    views  = [int(it["views"]) for it in items]
    return pd.Series(views, index=dates, dtype="int64")


def fetch_wiki(token: str, article: str) -> tuple[Optional[pd.Series], str]:
    """
    Fetch complete Wikipedia pageview history for one token.

    Returns (series_or_None, exclusion_reason).
    series is None if the article doesn't exist.
    """
    chunks: list[pd.Series] = []
    current = BACKTEST_START
    while current <= BACKTEST_END:
        chunk_end = min(current + timedelta(days=WIKI_CHUNK_DAYS - 1), BACKTEST_END)
        time.sleep(WIKI_RATE_SLEEP)
        chunk = _fetch_wiki_chunk(article, current, chunk_end)
        if chunk is None:
            return None, f"404 on article '{article}'"
        chunks.append(chunk)
        current = chunk_end + timedelta(days=1)

    if not chunks:
        return None, "empty response"

    series = pd.concat(chunks).sort_index()
    series = series[~series.index.duplicated(keep="first")]
    series.name = "views"

    # Apply filters
    n_days   = len(series)
    avg_views = series.mean()

    if n_days < MIN_WIKI_DAYS:
        return None, f"history {n_days}d < {MIN_WIKI_DAYS}d minimum"
    if avg_views < MIN_AVG_VIEWS:
        return None, f"avg views {avg_views:.1f}/day < {MIN_AVG_VIEWS} minimum"

    return series, "OK"


# ─── Price data ───────────────────────────────────────────────────────────────

def _fetch_binance_daily(symbol_usdt: str) -> Optional[pd.Series]:
    """Fetch daily close from Binance REST API. Returns None on failure."""
    start_ms = int(pd.Timestamp(BACKTEST_START).timestamp() * 1000)
    end_ms   = int(pd.Timestamp(BACKTEST_END).timestamp() * 1000)

    all_rows: list[list] = []
    limit    = 1000
    current_ms = start_ms

    while current_ms < end_ms:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol_usdt}&interval=1d"
            f"&startTime={current_ms}&endTime={end_ms}&limit={limit}"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WAV-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = json.loads(resp.read())
        except Exception:
            return None

        if not rows:
            break
        all_rows.extend(rows)
        last_open_ms = int(rows[-1][0])
        if last_open_ms <= current_ms:
            break
        current_ms = last_open_ms + 86_400_000  # advance by 1 day
        time.sleep(0.1)

    if not all_rows:
        return None

    dates  = pd.to_datetime([r[0] for r in all_rows], unit="ms", utc=True).tz_convert(None).normalize()
    closes = [float(r[4]) for r in all_rows]
    series = pd.Series(closes, index=dates, dtype="float64", name="close")
    series = series[~series.index.duplicated(keep="first")].sort_index()
    return series


def fetch_price(token: str) -> tuple[Optional[pd.Series], str]:
    """
    Fetch daily close prices. yfinance primary, Binance fallback (FIX 4).

    Returns (series_or_None, source_used_or_exclusion_reason).
    """
    # Path 1: yfinance
    try:
        df = yf.download(
            f"{token}-USD",
            start=BACKTEST_START.strftime("%Y-%m-%d"),
            end=(BACKTEST_END + timedelta(days=1)).strftime("%Y-%m-%d"),
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0].lower() for c in df.columns]
        else:
            df.columns = [c.lower() for c in df.columns]

        if "close" in df.columns and len(df) >= MIN_PRICE_DAYS:
            series = df["close"].dropna().rename("close")
            series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
            return series, "yfinance"
    except Exception:
        pass

    # Path 2: Binance fallback
    series = _fetch_binance_daily(f"{token}USDT")
    if series is not None and len(series) >= MIN_PRICE_DAYS:
        return series, "binance"

    return None, f"price history < {MIN_PRICE_DAYS}d on both yfinance and Binance"


# ─── Universe builder ─────────────────────────────────────────────────────────

def build_universe() -> dict[str, dict]:
    """
    Validate and fetch data for all pre-registered tokens.

    Returns dict: token → {"status": "OK"/"EXCLUDED", "reason": str,
                            "wiki_days": int, "avg_views": float,
                            "price_days": int, "price_source": str}
    """
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    PRICES_DIR.mkdir(parents=True, exist_ok=True)

    universe_report: dict[str, dict] = {}
    valid_tokens: list[str] = []

    for token, article in UNIVERSE.items():
        print(f"\n[{token}] Wikipedia: {article}")
        wiki_pq = WIKI_DIR / f"{token}.parquet"

        # --- Wikipedia ---
        if wiki_pq.exists():
            wiki_series = pd.read_parquet(wiki_pq)["views"]
            wiki_reason = "cached"
        else:
            wiki_series_raw, wiki_reason = fetch_wiki(token, article)
            if wiki_series_raw is None:
                print(f"  EXCLUDED wiki: {wiki_reason}")
                universe_report[token] = {
                    "status": "EXCLUDED", "reason": wiki_reason,
                    "wiki_days": 0, "avg_views": 0.0,
                    "price_days": 0, "price_source": "N/A",
                }
                continue
            wiki_series = wiki_series_raw
            pd.DataFrame({"views": wiki_series}).to_parquet(wiki_pq, engine="pyarrow")

        wiki_days  = len(wiki_series)
        avg_views  = float(wiki_series.mean())
        print(f"  wiki: {wiki_days}d, avg {avg_views:.0f} views/day  [{wiki_reason}]")

        # --- Price ---
        price_pq = PRICES_DIR / f"{token}.parquet"
        if price_pq.exists():
            price_series = pd.read_parquet(price_pq)["close"]
            price_src    = "cached"
        else:
            price_series_raw, price_src = fetch_price(token)
            if price_series_raw is None:
                print(f"  EXCLUDED price: {price_src}")
                universe_report[token] = {
                    "status": "EXCLUDED", "reason": price_src,
                    "wiki_days": wiki_days, "avg_views": avg_views,
                    "price_days": 0, "price_source": "N/A",
                }
                continue
            price_series = price_series_raw
            pd.DataFrame({"close": price_series}).to_parquet(price_pq, engine="pyarrow")

        price_days = len(price_series)
        print(f"  price: {price_days}d [{price_src}]")

        universe_report[token] = {
            "status": "OK", "reason": "passed all filters",
            "wiki_days": wiki_days, "avg_views": round(avg_views, 1),
            "price_days": price_days, "price_source": price_src,
        }
        valid_tokens.append(token)

    universe_report["_meta"] = {
        "total_candidates": len(UNIVERSE),
        "valid_count": len(valid_tokens),
        "valid_tokens": valid_tokens,
        "backtest_start": str(BACKTEST_START),
        "backtest_end": str(BACKTEST_END),
        "min_wiki_days": MIN_WIKI_DAYS,
        "min_avg_views": MIN_AVG_VIEWS,
        "min_price_days": MIN_PRICE_DAYS,
    }

    out_path = DATA_DIR / "universe.json"
    with open(out_path, "w") as fh:
        json.dump(universe_report, fh, indent=2)
    print(f"\nUniverse saved: {len(valid_tokens)}/{len(UNIVERSE)} tokens → {out_path}")
    return universe_report


# ─── BTC price for TSMOM orthogonality ───────────────────────────────────────

def fetch_btc_for_tsmom() -> pd.Series:
    """Load BTC daily close — reuse FGVD cache if available, else yfinance."""
    fgvd_cache = Path(__file__).parent.parent.parent.parent / (
        "archived/other/fgvd_h1/data/btc_price_raw.parquet"
    )
    if fgvd_cache.exists():
        df = pd.read_parquet(fgvd_cache)
        col = [c for c in df.columns if "close" in c.lower()]
        if col:
            series = df[col[0]].dropna()
            series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
            return series.rename("close")

    df = yf.download("BTC-USD", start="2017-01-01", auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    series = df["close"].dropna()
    series.index = pd.to_datetime(series.index).tz_localize(None).normalize()
    btc_pq = PRICES_DIR / "BTC.parquet"
    PRICES_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"close": series}).to_parquet(btc_pq, engine="pyarrow")
    return series.rename("close")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("WAV H3 — fetch_data.py")
    print(f"Backtest window: {BACKTEST_START} → {BACKTEST_END}")
    print(f"Filters: wiki ≥ {MIN_WIKI_DAYS}d, avg ≥ {MIN_AVG_VIEWS} views/d, price ≥ {MIN_PRICE_DAYS}d")
    print("=" * 60)

    report = build_universe()

    meta = report.get("_meta", {})
    valid = meta.get("valid_count", 0)
    total = meta.get("total_candidates", 0)

    print("\n" + "=" * 60)
    print(f"UNIVERSE: {valid}/{total} tokens passed all filters")
    excluded = [(t, v) for t, v in report.items()
                if t != "_meta" and v["status"] == "EXCLUDED"]
    if excluded:
        print("\nExcluded:")
        for tok, info in excluded:
            print(f"  {tok:6s}: {info['reason']}")

    print("\nValid tokens:")
    for tok in meta.get("valid_tokens", []):
        info = report[tok]
        print(f"  {tok:6s}: {info['wiki_days']}d wiki, {info['avg_views']:.0f} views/d, "
              f"{info['price_days']}d price [{info['price_source']}]")

    if valid < 20:
        print(f"\nGATE 0 FAIL: only {valid} tokens (need ≥ 20)")
    else:
        print(f"\nGATE 0 PASS: {valid} tokens ≥ 20 minimum")

    print("\nFetching BTC price for TSMOM orthogonality...")
    btc = fetch_btc_for_tsmom()
    print(f"BTC: {len(btc)} days, {btc.index[0].date()} → {btc.index[-1].date()}")
    print("\nDone.")
