"""
Fetch daily adjusted-close OHLCV for tradable equity index ETFs.

Tickers
-------
SPY  — SPDR S&P 500 ETF  (US, tracks ^GSPC)
QQQ  — Invesco Nasdaq-100 ETF  (US, tracks ^NDX)
EWQ  — iShares MSCI France ETF  (US-listed, tracks large-cap French equities ≈ CAC tradable proxy)

^FCHI / C40.PA are the raw CAC indices; we use EWQ because:
 - traded on US exchanges → clean yfinance data
 - avoids timezone/holiday misalignment with US sentiment data
 - confirms strategy is executable from a US-based account
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

TICKERS:       list[str] = ["SPY", "QQQ", "EWQ"]
DEFAULT_START: str       = "2003-01-01"


def fetch_prices(
    tickers:      list[str] = TICKERS,
    start:        str       = DEFAULT_START,
    end:          str | None = None,
    max_age_days: float      = 1.0,
) -> pd.DataFrame:
    """
    Return daily OHLCV for the given tickers as a MultiIndex DataFrame.

    Parameters
    ----------
    tickers      : list of yfinance-compatible tickers.
    start        : start date 'YYYY-MM-DD'.
    end          : end date 'YYYY-MM-DD', defaults to today.
    max_age_days : cache TTL.

    Returns
    -------
    pd.DataFrame
        Index   : DatetimeIndex, tz-naive daily (trading days only from yfinance).
        Columns : MultiIndex [(ticker, field)] where
                  field ∈ {close, open, high, low, volume}
                  close is split- and dividend-adjusted (auto_adjust=True).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))   # project root
    from data.cache import get_cached_or_fetch

    end_str = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        df = get_cached_or_fetch(
            ticker=ticker,
            start=start,
            end=end_str,
            interval="1d",
            source="yfinance",
            max_age_days=max_age_days,
        )
        if df.empty:
            log.warning("No data for %s — skipping", ticker)
            continue

        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.columns = pd.MultiIndex.from_product([[ticker], df.columns])
        frames.append(df)

    if not frames:
        raise RuntimeError("fetch_prices: all tickers returned empty data.")

    out = pd.concat(frames, axis=1).sort_index()
    log.info(
        "fetch_prices: %d tickers, %d rows, %s → %s",
        len(tickers), len(out),
        out.index[0].date(), out.index[-1].date(),
    )
    return out
