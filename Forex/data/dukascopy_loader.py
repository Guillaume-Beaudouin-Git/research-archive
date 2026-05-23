"""
Forex/data/dukascopy_loader.py
==============================
Spot FX D1/H1 OHLCV — primary via yfinance CME futures, optional Dukascopy.

For MONTHLY strategy research (Strategy D), yfinance daily FX data is sufficient.
Dukascopy 1-min data is only needed for intraday strategies (e.g., London ORB).

Public API
----------
load_fx_monthly(ccys, start, end) -> pd.DataFrame
    Monthly OHLCV close for G10 currencies vs USD.
    All prices in XXXUSD convention (USD per 1 foreign currency unit).

load_fx_returns(ccys, start, end) -> pd.DataFrame
    Monthly log returns (or pct_change) for G10, aligned to month-end.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# yfinance FX spot tickers; invert_spot=True means yfinance gives USDXXX → need 1/px
_FX_TICKERS: dict[str, tuple[str, bool]] = {
    "EUR": ("EURUSD=X",  False),
    "GBP": ("GBPUSD=X",  False),
    "JPY": ("JPY=X",     True),    # yfinance: USDJPY → invert to JPYUSD
    "CHF": ("CHF=X",     True),    # USDCHF → invert
    "AUD": ("AUDUSD=X",  False),
    "CAD": ("CAD=X",     True),    # USDCAD → invert
    "NZD": ("NZDUSD=X",  False),
    "NOK": ("NOK=X",     True),    # USDNOK → invert
    "SEK": ("SEK=X",     True),    # USDSEK → invert
    "BRL": ("BRL=X",     True),
    "MXN": ("MXN=X",     True),
    "ZAR": ("ZAR=X",     True),
    "INR": ("INR=X",     True),
    "TRY": ("TRY=X",     True),
}


def _fetch_one(ccy: str, start: str, end: str) -> pd.Series | None:
    ticker, invert = _FX_TICKERS.get(ccy, (None, False))
    if ticker is None:
        log.warning("No yfinance ticker for %s", ccy)
        return None
    try:
        import yfinance as yf
        df = yf.download(ticker, start=start, end=end, interval="1d",
                         auto_adjust=True, progress=False)
        if df.empty:
            log.warning("yfinance returned empty for %s (%s)", ccy, ticker)
            return None
        # Handle MultiIndex columns (yfinance >= 0.2)
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[:, 0]
        else:
            close = df["Close"]
        close = close.dropna()
        if invert:
            close = 1.0 / close
        return close.rename(ccy)
    except Exception as exc:
        log.warning("yfinance failed for %s: %s", ccy, exc)
        return None


def load_fx_monthly(
    ccys: list[str] | None = None,
    start: str = "2005-01-01",
    end:   str = "2026-05-01",
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Monthly OHLCV close for G10 currencies vs USD (XXXUSD convention).

    Parameters
    ----------
    ccys          : currency list (default: G10 excl. USD).
    start, end    : ISO date strings.
    max_age_days  : cache TTL.

    Returns
    -------
    pd.DataFrame
        Index  : DatetimeIndex, month-end.
        Columns: currency codes.
        Values : XXXUSD price (USD per 1 foreign unit).
    """
    if ccys is None:
        ccys = ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "NOK", "SEK"]

    pq   = _CACHE_DIR / "fx_monthly_close.parquet"
    meta = _CACHE_DIR / "fx_monthly_close.json"

    import json
    from datetime import datetime, timezone

    if pq.exists() and meta.exists():
        with open(meta) as fh:
            m = json.load(fh)
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(m["created_at"])).total_seconds() / 86400
        if age <= max_age_days:
            df = pd.read_parquet(pq)
            available = [c for c in ccys if c in df.columns]
            if len(available) == len(ccys):
                log.info("FX monthly cache hit (%.1f days old)", age)
                return df[available].loc[start:end]

    log.info("Fetching daily FX for %d currencies → resample to monthly", len(ccys))
    series: list[pd.Series] = []
    for ccy in ccys:
        s = _fetch_one(ccy, start, end)
        if s is not None:
            series.append(s)

    if not series:
        raise RuntimeError("All yfinance FX fetches failed.")

    daily = pd.concat(series, axis=1)
    monthly = daily.resample("M").last()

    monthly.index.name = "date"
    monthly.to_parquet(pq)
    with open(meta, "w") as fh:
        json.dump({"created_at": datetime.now(timezone.utc).isoformat(),
                   "start": start, "end": end}, fh)

    return monthly.loc[start:end]


def load_fx_returns(
    ccys: list[str] | None = None,
    start: str = "2005-01-01",
    end:   str = "2026-05-01",
    log_returns: bool = True,
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Monthly FX returns in XXXUSD convention.

    Parameters
    ----------
    log_returns : if True, use log returns (default). False = simple pct_change.

    Returns
    -------
    pd.DataFrame
        Same structure as load_fx_monthly(), values are returns.
    """
    px = load_fx_monthly(ccys, start, end, max_age_days)
    if log_returns:
        return np.log(px).diff().dropna(how="all")
    else:
        return px.pct_change().dropna(how="all")
