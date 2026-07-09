#!/usr/bin/env python3
"""
Build (or refresh) the Strategy A price cache for the feasibility pipeline.

Run this on a host WITH network access (the VPS, ~/venv/). The Anthropic cloud
sandbox where the feasibility routine runs blocks yfinance/Binance (403), so the
pipeline reads the parquet this script produces instead of fetching live.

The script:
  - calls ``load_strategy_a_universe(force_live=True)`` (bypasses cache, fetches
    live, and rewrites the parquet with an embedded ``_cached_at`` timestamp);
  - prints a summary (n_assets, date range, n_rows, cache path, timestamp).

It is idempotent and re-runnable: each run overwrites the cache in place and
stamps a fresh ``_cached_at``. Recommended cron on the VPS (daily, well within
the 14-day freshness window used by the loader):

    0 6 * * *  cd /path/to/Algo_claude && ~/venv/bin/python3 \
        _automation/feasibility/data/build_price_cache.py \
        >> logs/build_price_cache.log 2>&1

Usage:
    python3 build_price_cache.py [--start 2018-01-01] [--end 2026-07-09] \
        [--cache-path <path>]
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

# Make the repo root importable (…/Algo_claude) so absolute imports resolve.
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from _automation.feasibility.data.loaders import (  # noqa: E402
    CACHE_PATH,
    STRATEGY_A_FULL_UNIVERSE,
    _read_cached_at,
    load_strategy_a_universe,
)


def build_cache(
    start: str,
    end: str,
    cache_path: Path | None = None,
) -> int:
    """Fetch the full universe live, rewrite the cache, and print a summary."""
    path = Path(cache_path) if cache_path is not None else CACHE_PATH
    print(f"Building Strategy A price cache → {path}")
    print(f"  universe : {len(STRATEGY_A_FULL_UNIVERSE)} tickers")
    print(f"  window   : {start} → {end}")
    print("  fetching live (force_live=True) …")

    df = load_strategy_a_universe(
        start=start,
        end=end,
        tickers=STRATEGY_A_FULL_UNIVERSE,
        force_live=True,
        cache_path=path,
    )

    if df.empty:
        print("  ✗ live fetch returned no data — cache NOT usable.", file=sys.stderr)
        return 1

    cached_at = _read_cached_at(path)
    print("\n  ✅ cache written")
    print(f"     path       : {path}")
    print(f"     n_assets   : {df.shape[1]}  ({', '.join(map(str, df.columns))})")
    print(f"     n_rows     : {df.shape[0]}")
    print(f"     date range : {df.index.min().date()} → {df.index.max().date()}")
    print(f"     _cached_at : {cached_at}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="2018-01-01", help="ISO start date")
    parser.add_argument(
        "--end", default=str(date.today()), help="ISO end date (default: today)"
    )
    parser.add_argument(
        "--cache-path", default=None, help="override cache location (parquet)"
    )
    args = parser.parse_args()
    return build_cache(
        start=args.start,
        end=args.end,
        cache_path=Path(args.cache_path) if args.cache_path else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
