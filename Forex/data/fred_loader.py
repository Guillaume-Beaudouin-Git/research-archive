"""
Forex/data/fred_loader.py
=========================
Fetch G10 short-term interest rates and CPI data from FRED.

Public API
----------
load_g10_rates(start, end) -> pd.DataFrame
    Monthly 3M interbank rates for USD + 9 G10 currencies, in % per annum.

load_g10_cpi(start, end) -> pd.DataFrame
    Monthly CPI year-on-year % change for USD + 9 G10 currencies.
    Returns NaN where FRED series unavailable.

load_rf_monthly(start, end) -> pd.Series
    US 3M T-bill rate (DTB3), resampled to monthly last, in % per annum.

All series are resampled to month-end (MS or M) and forward-filled within
each month only (max ffill = 3 months to prevent stale data contamination).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_MAX_FFILL_MONTHS: int = 3

# ─────────────────────────────────────────────────────────────────────────────
# FRED series IDs
# ─────────────────────────────────────────────────────────────────────────────

_RATES_3M: dict[str, str] = {
    "USD": "DTB3",                  # US 3M T-Bill (daily → resample)
    "EUR": "IR3TIB01EZM156N",       # 3M Euribor
    "GBP": "IR3TIB01GBM156N",       # 3M GBP LIBOR
    "JPY": "IR3TIB01JPM156N",       # 3M JPY TIBOR
    "CHF": "IR3TIB01CHM156N",       # 3M CHF LIBOR
    "AUD": "IR3TIB01AUM156N",       # 3M AUD BBSW
    "CAD": "IR3TIB01CAM156N",       # 3M CAD CDOR
    "NZD": "IR3TIB01NZM156N",       # 3M NZD NZIBOR
    "NOK": "IR3TIB01NOM156N",       # 3M NOK NIBOR
    "SEK": "IR3TIB01SEM156N",       # 3M SEK STIBOR
}

_CPI_YOY: dict[str, str] = {
    "USD": "CPALTT01USM659N",
    "EUR": "CPALTT01EZM659N",
    "GBP": "CPALTT01GBM659N",
    "JPY": "CPALTT01JPM659N",
    "CHF": "CPALTT01CHM659N",
    "AUD": "CPALTT01AUM659N",
    "CAD": "CPALTT01CAM659N",
    "NZD": "CPALTT01NZM659N",
    "NOK": "CPALTT01NOM659N",
    "SEK": "CPALTT01SEM659N",
}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_fred_series(code: str, start: str, end: str) -> pd.Series:
    """Download one FRED series via pandas_datareader. Returns monthly last."""
    from pandas_datareader.data import DataReader
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s = DataReader(code, "fred", start, end).iloc[:, 0]
    s.name = code
    return s


def _to_monthly_last(s: pd.Series, max_ffill: int = _MAX_FFILL_MONTHS) -> pd.Series:
    """Resample to month-end (last), then forward-fill up to max_ffill months."""
    monthly = s.resample("M").last()
    return monthly.ffill(limit=max_ffill)


def _cache_path(name: str) -> Path:
    return _CACHE_DIR / f"{name}.parquet"


def _load_or_fetch(
    name: str,
    series_map: dict[str, str],
    start: str,
    end: str,
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Load from parquet cache if fresh; otherwise fetch all series from FRED
    and write cache.
    """
    import json, os
    from datetime import datetime, timezone

    pq = _cache_path(name)
    meta_path = _CACHE_DIR / f"{name}.json"

    if pq.exists() and meta_path.exists():
        with open(meta_path) as fh:
            meta = json.load(fh)
        age_d = (
            datetime.now(timezone.utc)
            - datetime.fromisoformat(meta["created_at"])
        ).total_seconds() / 86400
        if age_d <= max_age_days:
            log.info("Cache hit → %s (%.1f days old)", pq.name, age_d)
            return pd.read_parquet(pq)

    log.info("Fetching %d FRED series for %s [%s → %s]", len(series_map), name, start, end)
    columns: dict[str, pd.Series] = {}
    for ccy, code in series_map.items():
        try:
            raw = _fetch_fred_series(code, start, end)
            columns[ccy] = _to_monthly_last(raw)
            log.info("  %-4s %-28s %4d obs  %s → %s",
                     ccy, code, columns[ccy].notna().sum(),
                     columns[ccy].first_valid_index().date() if columns[ccy].notna().any() else "n/a",
                     columns[ccy].last_valid_index().date()  if columns[ccy].notna().any() else "n/a")
        except Exception as exc:
            log.warning("  %-4s FAILED: %s", ccy, exc)

    if not columns:
        raise RuntimeError(f"All FRED fetches failed for {name}.")

    df = pd.DataFrame(columns)
    df.index.name = "date"
    df.to_parquet(pq)

    import json
    from datetime import datetime, timezone
    with open(meta_path, "w") as fh:
        json.dump({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "start": start, "end": end,
            "series_map": series_map,
        }, fh)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_g10_rates(
    start: str = "2005-01-01",
    end:   str = "2026-05-01",
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Monthly 3M interbank rates for USD + 9 G10 currencies.

    Parameters
    ----------
    start, end : ISO date strings.
    max_age_days : cache TTL.

    Returns
    -------
    pd.DataFrame
        Index  : DatetimeIndex, month-end frequency.
        Columns: ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD', 'NOK', 'SEK']
        Values : % per annum (e.g., 5.0 = 5% p.a.).
        NaN    : where FRED series unavailable or stale (> 3M gap).
    """
    return _load_or_fetch("g10_rates_3m", _RATES_3M, start, end, max_age_days)


def load_g10_cpi(
    start: str = "2005-01-01",
    end:   str = "2026-05-01",
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Monthly CPI y/y % change for USD + 9 G10 currencies.

    Returns NaN where the FRED series is unavailable.
    Smoothing (12M Gaussian) should be applied downstream in signal.py.

    Returns
    -------
    pd.DataFrame
        Index  : DatetimeIndex, month-end.
        Columns: ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NZD', 'NOK', 'SEK']
        Values : % y/y (e.g., 2.5 = 2.5% inflation).
    """
    df = _load_or_fetch("g10_cpi", _CPI_YOY, start, end, max_age_days)
    nan_frac = df.isna().mean().round(2)
    for ccy in df.columns:
        if nan_frac[ccy] > 0.2:
            log.warning("CPI %s: %.0f%% NaN — series may be unavailable on FRED", ccy, nan_frac[ccy] * 100)
    return df


def load_rf_monthly(
    start: str = "2005-01-01",
    end:   str = "2026-05-01",
    max_age_days: float = 1.0,
) -> pd.Series:
    """
    US 3M T-bill rate (DTB3), monthly last, in % per annum.

    Used to compute excess returns: excess_ret = spot_ret − (DTB3/12/100).
    """
    df = load_g10_rates(start, end, max_age_days)
    return df["USD"].rename("rf_usd_pct")


# ─────────────────────────────────────────────────────────────────────────────
# Sanity check (run with: python -m Forex.data.fred_loader)
# ─────────────────────────────────────────────────────────────────────────────

def _sanity() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("=" * 68)
    print("FRED G10 Rates Sanity Check")
    print("=" * 68)

    rates = load_g10_rates()
    print(f"\nShape: {rates.shape}")
    print(f"Date range: {rates.index[0].date()} → {rates.index[-1].date()}")
    print("\nNaN counts per currency:")
    print(rates.isna().sum().to_string())
    print("\nHead (2005-01 to 2005-03):")
    print(rates.loc["2005-01":"2005-03"].to_string())
    print("\nTail (last 3 months):")
    print(rates.tail(3).to_string())
    print("\nKey stats (mean % p.a., 2005-2026):")
    print(rates.mean().round(2).to_string())

    print("\n" + "=" * 68)
    print("CPI Sanity Check")
    print("=" * 68)
    cpi = load_g10_cpi()
    print(f"Shape: {cpi.shape}")
    print(f"NaN fraction per currency:")
    print((cpi.isna().mean() * 100).round(1).astype(str).add(" %").to_string())
    print("\nTail (last 3 months):")
    print(cpi.tail(3).to_string())


if __name__ == "__main__":
    _sanity()
