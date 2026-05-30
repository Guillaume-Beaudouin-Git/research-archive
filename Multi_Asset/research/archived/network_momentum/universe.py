"""
universe.py — Cross-asset universe for Network Momentum (Strategy E)
=====================================================================
34-asset universe across FX, Equities, Bonds, Commodities, Sectors, Crypto.
Returns daily log-excess returns (over DTB3 T-bill) indexed by date.

Usage:
    from Multi_Asset.research.active.network_momentum.universe import load_universe
    returns, meta = load_universe(start="2015-01-01", end="2026-05-21")

Returns:
    returns  — pd.DataFrame, shape (T, N), log excess returns (annualized conventions preserved)
    meta     — dict with asset_class mapping, first_date per asset, drop log

Minimum history: 5 years (1260 trading days). Assets with less are dropped.
FX: expressed as USD per 1 unit of foreign currency (positive = foreign currency strengthening).
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

_REPO = Path(__file__).parent.parent.parent.parent.parent  # Algo_claude/
sys.path.insert(0, str(_REPO))
from data.cache import get_cached_or_fetch

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Universe definition
# ─────────────────────────────────────────────────────────────────────────────

# FX: yfinance tickers, flag 'invert' means 1/price to get USD per foreign unit
FX_ASSETS: List[Tuple[str, str, bool]] = [
    # (yfinance_ticker, clean_name, invert)
    ("EURUSD=X", "EUR",  False),  # EUR/USD already = USD per EUR
    ("GBPUSD=X", "GBP",  False),  # GBP/USD
    ("AUDUSD=X", "AUD",  False),  # AUD/USD
    ("NZDUSD=X", "NZD",  False),  # NZD/USD (replace JPY — more reliable yf feed)
    ("USDJPY=X", "JPY",  True),   # 1/USDJPY = USD per JPY
    ("USDCAD=X", "CAD",  True),   # 1/USDCAD = USD per CAD
    ("USDCHF=X", "CHF",  True),   # 1/USDCHF = USD per CHF
    ("USDNOK=X", "NOK",  True),   # 1/USDNOK = USD per NOK
    ("USDSEK=X", "SEK",  True),   # 1/USDSEK = USD per SEK
]

EQUITY_ASSETS = ["SPY", "QQQ", "EFA", "EEM", "IWM"]
BOND_ASSETS   = ["TLT", "IEF", "SHY"]
COMM_ASSETS   = ["GLD", "SLV", "USO", "UNG", "DBA", "DBB", "CPER"]
SECTOR_ASSETS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLB"]
CRYPTO_ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]

ASSET_CLASS_MAP: Dict[str, str] = {}
for _, name, _ in FX_ASSETS:
    ASSET_CLASS_MAP[name] = "FX"
for t in EQUITY_ASSETS:
    ASSET_CLASS_MAP[t] = "Equity"
for t in BOND_ASSETS:
    ASSET_CLASS_MAP[t] = "Bond"
for t in COMM_ASSETS:
    ASSET_CLASS_MAP[t] = "Commodity"
for t in SECTOR_ASSETS:
    ASSET_CLASS_MAP[t] = "Sector"
for t in CRYPTO_ASSETS:
    ASSET_CLASS_MAP[t] = "Crypto"

MIN_HISTORY_DAYS = 1260  # 5 years of trading days


# ─────────────────────────────────────────────────────────────────────────────
# Risk-free rate (DTB3 daily T-bill from FRED)
# ─────────────────────────────────────────────────────────────────────────────

def _load_rf(start: str, end: str) -> pd.Series:
    """DTB3 3-month T-bill discount rate from FRED, resampled to daily fraction."""
    try:
        import pandas_datareader.data as web
        dtb3 = web.DataReader("DTB3", "fred", start, end)["DTB3"]
        dtb3 = dtb3.dropna().reindex(
            pd.date_range(start, end, freq="B"), method="ffill"
        )
        # Convert annualized % → daily fraction
        rf_daily = dtb3 / 100 / 252
        rf_daily.name = "rf"
        return rf_daily
    except Exception as exc:
        log.warning(f"FRED DTB3 fetch failed ({exc}) — using rf=0")
        idx = pd.date_range(start, end, freq="B")
        return pd.Series(0.0, index=idx, name="rf")


# ─────────────────────────────────────────────────────────────────────────────
# Price loading helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_close(ticker: str, start: str, end: str) -> pd.Series:
    df = get_cached_or_fetch(ticker, start=start, end=end, interval="1d",
                             max_age_days=1.0)
    if df.empty:
        return pd.Series(dtype=float, name=ticker)
    col = "close" if "close" in df.columns else df.columns[0]
    s = df[col].dropna()
    s.index = pd.to_datetime(s.index).normalize()
    s.name = ticker
    return s


def _load_all_prices(start: str, end: str) -> pd.DataFrame:
    """Fetch close prices for all assets. Returns DataFrame indexed by date."""
    prices: Dict[str, pd.Series] = {}

    # FX
    for ticker, name, invert in FX_ASSETS:
        s = _fetch_close(ticker, start, end)
        if s.empty:
            log.warning(f"FX {ticker} ({name}): empty — skipping")
            continue
        if invert:
            s = 1.0 / s
        s.name = name
        prices[name] = s
        log.info(f"  FX {name}: {len(s)} days [{s.index[0].date()} → {s.index[-1].date()}]")

    # All other ETF/crypto assets
    plain_assets = (
        EQUITY_ASSETS + BOND_ASSETS + COMM_ASSETS + SECTOR_ASSETS + CRYPTO_ASSETS
    )
    for ticker in plain_assets:
        s = _fetch_close(ticker, start, end)
        if s.empty:
            log.warning(f"{ticker}: empty — skipping")
            continue
        prices[ticker] = s
        log.info(f"  {ticker}: {len(s)} days [{s.index[0].date()} → {s.index[-1].date()}]")

    df = pd.DataFrame(prices).sort_index()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Quality filtering
# ─────────────────────────────────────────────────────────────────────────────

def _filter_assets(
    prices: pd.DataFrame,
    min_history: int,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Drop assets with fewer than min_history non-NaN observations.
    Returns (filtered_df, dropped_list).
    """
    dropped = []
    keep = []
    for col in prices.columns:
        n_valid = prices[col].dropna().shape[0]
        if n_valid < min_history:
            dropped.append(f"{col} (only {n_valid} days)")
            log.info(f"  DROP {col}: {n_valid} < {min_history} days")
        else:
            keep.append(col)
    return prices[keep], dropped


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def load_universe(
    start: str = "2015-01-01",
    end:   str = "2026-05-21",
    min_history_days: int = MIN_HISTORY_DAYS,
) -> Tuple[pd.DataFrame, dict]:
    """
    Load cross-asset universe and return daily log excess returns.

    Parameters
    ----------
    start, end : date strings
    min_history_days : minimum non-NaN observations to keep an asset (default 1260)

    Returns
    -------
    returns : pd.DataFrame (T × N), log excess returns per asset per day
    meta    : dict with keys:
              - asset_class     : {asset_name: class_str}
              - first_date      : {asset_name: first_valid_date}
              - dropped_assets  : list of (name, reason) strings
              - rf              : pd.Series of daily risk-free rate
    """
    log.info(f"Loading universe: {start} → {end}")

    # 1. Raw prices
    prices = _load_all_prices(start, end)

    # 2. Quality filter before computing returns
    prices, dropped = _filter_assets(prices, min_history_days)
    if len(prices.columns) < 20:
        raise ValueError(
            f"Universe too small after quality filter: {len(prices.columns)} assets < 20 minimum. "
            f"Dropped: {dropped}"
        )

    # 3. Log returns (daily)
    log_ret = np.log(prices / prices.shift(1))

    # 4. Risk-free excess
    rf = _load_rf(start, end)
    rf = rf.reindex(log_ret.index, method="ffill").fillna(0.0)

    # Subtract daily rf from each column
    excess = log_ret.sub(rf, axis=0)

    # 5. Drop first row (NaN from shift) and any rows with ALL NaN
    excess = excess.iloc[1:]
    excess = excess[~excess.isna().all(axis=1)]

    # 6. Restrict to business days (Mon-Fri) — standard for multi-asset daily strategy.
    #    Crypto trades on weekends but all other assets don't; keeping mixed-calendar
    #    creates NaN rows that distort EWMA features. Weekend crypto returns aggregate
    #    into the Friday-Monday change when we reindex to business days.
    bdays = pd.bdate_range(start=excess.index.min(), end=excess.index.max())
    excess = excess.reindex(bdays).ffill(limit=3)
    # Recompute as log-return over business-day index
    prices_bd = prices.reindex(bdays).ffill(limit=3)
    log_ret_bd = np.log(prices_bd / prices_bd.shift(1))
    rf_bd = rf.reindex(bdays, method="ffill").fillna(0.0)
    excess = log_ret_bd.sub(rf_bd, axis=0).iloc[1:]
    excess = excess[~excess.isna().all(axis=1)]
    # Update meta prices to business-day aligned
    meta_prices_bd = prices_bd

    # 6. Metadata
    first_dates = {col: prices[col].first_valid_index() for col in prices.columns}
    ac_map = {k: ASSET_CLASS_MAP.get(k, "Unknown") for k in prices.columns}

    meta = {
        "asset_class":    ac_map,
        "first_date":     first_dates,
        "dropped_assets": dropped,
        "rf":             rf,
        "prices":         meta_prices_bd,
    }

    # Per-class summary
    from collections import Counter
    class_counts = Counter(ac_map.values())
    log.info(
        f"Universe: {len(prices.columns)} assets | "
        + ", ".join(f"{k}={v}" for k, v in sorted(class_counts.items()))
    )
    log.info(f"Returns: {len(excess)} trading days [{excess.index[0].date()} → {excess.index[-1].date()}]")

    return excess, meta


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    import os
    os.chdir(_REPO)
    ret, meta = load_universe()
    print(f"\nReturns shape: {ret.shape}")
    print(f"Assets ({len(ret.columns)}): {list(ret.columns)}")
    print(f"\nPer-class:")
    from collections import Counter
    cc = Counter(meta["asset_class"].values())
    for k, v in sorted(cc.items()):
        print(f"  {k}: {v}")
    print(f"\nDropped: {meta['dropped_assets']}")
    print(f"\nSample (last 3 rows, first 5 cols):")
    print(ret.iloc[-3:, :5].to_string())
