"""
Unified data loaders for the feasibility pipeline.
Wraps cached parquet (crypto 8h OHLCV + funding), Binance klines, and NQ 1-min CSV
via the project's existing data/cache.py infrastructure.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

# Minimum listing dates to discard pre-launch garbage from yfinance
# (same as strategies/tsmom_v2_propfirm/config.py MIN_LISTING_DATES)
_MIN_LISTING_DATES: dict[str, str] = {
    "SOL-USD": "2020-04-10",
    "AVAX-USD": "2020-07-13",
    "DOT-USD": "2020-08-19",
    "UNI-USD": "2020-09-17",
    "MATIC-USD": "2019-04-01",
    "OP-USD": "2022-05-31",
    "ARB-USD": "2023-03-23",
}

# Full Strategy A universe (from config.py)
STRATEGY_A_FULL_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD",
    "AVAX-USD", "LINK-USD", "DOGE-USD", "ADA-USD",
    "DOT-USD", "UNI-USD", "LTC-USD", "BCH-USD",
    "MATIC-USD", "OP-USD", "ARB-USD",
]

STRATEGY_A_CORE: list[str] = ["BTC-USD", "ETH-USD", "SOL-USD"]

STRATEGY_A_ADJACENT: list[str] = [
    "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD"
]


def load_strategy_a_universe(
    start: str = "2020-01-01",
    end: str = "2025-12-31",
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """
    Load Strategy A universe prices via yfinance.

    Parameters
    ----------
    start : str
        Start date in ISO format (default '2020-01-01').
    end : str
        End date in ISO format (default '2025-12-31').
    tickers : list[str] or None
        Explicit list of yfinance tickers. If None, loads the minimal core
        universe [BTC-USD, ETH-USD, SOL-USD].

    Returns
    -------
    pd.DataFrame
        date × ticker DataFrame of daily Close prices, sorted by date.
        Columns with > 50% NaN in the leading rows are dropped (asset listed late).
        Rows with all-NaN are dropped.
    """
    import yfinance as yf

    if tickers is None:
        tickers = STRATEGY_A_CORE

    prices: dict[str, pd.Series] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for ticker in tickers:
            try:
                raw = yf.download(
                    ticker,
                    start=start,
                    end=end,
                    interval="1d",
                    auto_adjust=True,
                    progress=False,
                )
                if raw is None or raw.empty:
                    continue
                # Apply minimum listing date filter
                if ticker in _MIN_LISTING_DATES:
                    raw = raw.loc[raw.index >= pd.Timestamp(_MIN_LISTING_DATES[ticker])]
                if len(raw) < 30:
                    continue
                # Extract Close; yfinance may return MultiIndex columns
                if isinstance(raw.columns, pd.MultiIndex):
                    px = raw["Close"][ticker].squeeze()
                else:
                    px = raw["Close"].squeeze()
                px = px.dropna()
                if len(px) < 30:
                    continue
                # Clip extreme log-returns at ±1.0 (yfinance data quality)
                log_r = np.log(px / px.shift(1))
                extreme = int((log_r.abs() > 1.0).sum())
                if extreme > 0:
                    # Reconstruct price series from clipped log-returns
                    log_r_clipped = log_r.clip(-1.0, 1.0)
                    px = pd.Series(
                        np.exp(np.log(px.iloc[0]) + log_r_clipped.fillna(0).cumsum()),
                        index=px.index,
                    )
                prices[ticker] = px
            except Exception:
                continue

    if not prices:
        raise ValueError(f"No data loaded for tickers {tickers} ({start} → {end})")

    df = pd.DataFrame(prices).sort_index()

    # Drop columns where > 50% of the FIRST n rows are NaN (late-listed assets)
    n_first = min(len(df) // 4, 90)  # inspect first quarter up to 90 rows
    late_listed = df.iloc[:n_first].isna().mean() > 0.5
    df = df.loc[:, ~late_listed]

    return df.dropna(how="all")


def split_universe(
    prices: pd.DataFrame,
    main_tickers: list[str],
    adjacent_tickers: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split a prices DataFrame into main and adjacent universes.

    Parameters
    ----------
    prices : pd.DataFrame
        Full date × ticker price DataFrame.
    main_tickers : list[str]
        Tickers that form the primary universe (must be present in prices.columns).
    adjacent_tickers : list[str] or None
        Tickers for the adjacent universe. If None, uses all columns not in main_tickers.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        (prices_main, prices_adjacent) — columns filtered and NaN-trimmed.
    """
    available = set(prices.columns)
    main_cols = [t for t in main_tickers if t in available]
    if not main_cols:
        raise ValueError(f"None of main_tickers {main_tickers} found in prices columns.")

    if adjacent_tickers is None:
        adj_cols = [c for c in prices.columns if c not in main_cols]
    else:
        adj_cols = [t for t in adjacent_tickers if t in available]

    prices_main = prices[main_cols].dropna(how="all")
    prices_adjacent = prices[adj_cols].dropna(how="all") if adj_cols else pd.DataFrame()

    return prices_main, prices_adjacent
