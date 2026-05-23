"""
Forex/data/bis_reer_loader.py
==============================
Download and parse BIS monthly broad REER indices (Real Effective Exchange Rates).

Source: https://www.bis.org/statistics/eer/broad.xlsx
Sheet : 'Real'  (CPI-based, Broad Indices, 2020 = 100)
Lag   : 1-month publication lag applied automatically.

Public API
----------
load_bis_reer(start, end, currencies) -> pd.DataFrame
    Monthly REER levels (2020=100) for G10 + EM currencies.
    Publication lag already applied (shift = 1 month).

compute_reer_zscore(reer, window_years) -> pd.DataFrame
    Rolling z-score of REER level over a trailing window.
    Positive = overvalued vs mean. Used as signal: -z_reer in composite signal.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_BIS_URL = "https://www.bis.org/statistics/eer/broad.xlsx"
_SHEET   = "Real"
_BASE_YEAR_NOTE = "2020 = 100"

# BIS 'RBXX' column codes for our universe (from parsing real sheet row 4)
_BIS_CODE_MAP: dict[str, str] = {
    "EUR": "RBXM",   # Euro area (XM)
    "GBP": "RBGB",   # United Kingdom
    "JPY": "RBJP",   # Japan
    "CHF": "RBCH",   # Switzerland
    "AUD": "RBAU",   # Australia
    "CAD": "RBCA",   # Canada
    "NZD": "RBNZ",   # New Zealand
    "NOK": "RBNO",   # Norway
    "SEK": "RBSE",   # Sweden
    "USD": "RBUS",   # United States
    "BRL": "RBBR",   # Brazil
    "MXN": "RBMX",   # Mexico
    "ZAR": "RBZA",   # South Africa
    "INR": "RBIN",   # India
    "TRY": "RBTR",   # Turkey
}

_PUBLICATION_LAG_MONTHS: int = 1


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _download_and_parse() -> pd.DataFrame:
    """
    Download BIS broad REER Excel and return a raw DataFrame.

    Returns
    -------
    pd.DataFrame
        Index  : DatetimeIndex (month-end)
        Columns: BIS code strings (e.g., 'RBXM', 'RBGB', ...)
    """
    import requests
    log.info("Downloading BIS EER Excel from %s", _BIS_URL)
    resp = requests.get(
        _BIS_URL,
        timeout=60,
        headers={"User-Agent": "research/1.0 (academic use)"},
    )
    resp.raise_for_status()
    log.info("Downloaded %d KB", len(resp.content) // 1024)

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
    ws = wb[_SHEET]
    rows = list(ws.iter_rows(values_only=True))

    # Row 3 (index 3): country names starting at index 1
    # Row 4 (index 4): BIS codes starting at index 1; index 0 is None (date col)
    names = list(rows[3])[1:]  # ['Algeria', 'Argentina', ...]
    codes = list(rows[4])[1:]  # ['RBDZ', 'RBAR', 'RBAU', ...]
    col_map = {code: name for code, name in zip(codes, names)}

    # Data rows start at index 5
    data_rows = rows[5:]
    dates, values = [], {c: [] for c in codes}

    for row in data_rows:
        if row[0] is None:
            continue
        dates.append(row[0])
        for i, code in enumerate(codes):
            val = row[i + 1] if i + 1 < len(row) else None
            values[code].append(float(val) if val is not None else np.nan)

    df = pd.DataFrame(values, index=pd.DatetimeIndex(dates))
    df.index = df.index + pd.offsets.MonthEnd(0)   # ensure month-end timestamps
    df.index.name = "date"
    df = df.sort_index()

    log.info("BIS REER parsed: %d months (%s → %s), %d series",
             len(df), df.index[0].date(), df.index[-1].date(), df.shape[1])
    return df


def _cache_path() -> Path:
    return _CACHE_DIR / "bis_reer_broad.parquet"


def _meta_path() -> Path:
    return _CACHE_DIR / "bis_reer_broad.json"


def _load_cached(max_age_days: float) -> pd.DataFrame | None:
    import json
    from datetime import datetime, timezone
    pq   = _cache_path()
    meta = _meta_path()
    if not pq.exists() or not meta.exists():
        return None
    with open(meta) as fh:
        m = json.load(fh)
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(m["created_at"])).total_seconds() / 86400
    if age > max_age_days:
        log.info("BIS REER cache stale (%.1f days)", age)
        return None
    log.info("BIS REER cache hit (%.1f days old)", age)
    return pd.read_parquet(pq)


def _save_cache(df: pd.DataFrame) -> None:
    import json
    from datetime import datetime, timezone
    df.to_parquet(_cache_path())
    with open(_meta_path(), "w") as fh:
        json.dump({"created_at": datetime.now(timezone.utc).isoformat(),
                   "rows": len(df), "columns": list(df.columns)}, fh)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_bis_reer(
    start:        str   = "2005-01-01",
    end:          str   = "2026-05-01",
    currencies:   list[str] | None = None,
    max_age_days: float = 7.0,
    apply_pub_lag: bool = True,
) -> pd.DataFrame:
    """
    Monthly BIS broad REER (CPI-based, 2020=100), publication lag applied.

    Parameters
    ----------
    start, end    : ISO date strings (inclusive).
    currencies    : subset to return (default: G10 + USD).
    max_age_days  : cache TTL. BIS publishes monthly so 7 days is fine.
    apply_pub_lag : if True (default), shift data by 1 month to avoid look-ahead.

    Returns
    -------
    pd.DataFrame
        Index  : DatetimeIndex, month-end.
        Columns: currency codes from ``currencies`` (e.g., 'EUR', 'GBP', ...).
        Values : REER index (2020 = 100).
        NaN    : outside BIS coverage or after applying publication lag.

    Notes
    -----
    Values > 100 indicate the currency is overvalued vs its 2020 level.
    For strategy use, compute rolling z-score vs 10Y mean to identify
    deviation from long-run fair value. See ``compute_reer_zscore()``.
    """
    if currencies is None:
        currencies = ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "NOK", "SEK", "USD"]

    raw = _load_cached(max_age_days)
    if raw is None:
        raw = _download_and_parse()
        _save_cache(raw)

    # Select our currency columns via BIS code map
    selected: dict[str, pd.Series] = {}
    for ccy in currencies:
        bis_code = _BIS_CODE_MAP.get(ccy)
        if bis_code is None:
            log.warning("No BIS code for %s — skipping", ccy)
            continue
        if bis_code not in raw.columns:
            log.warning("BIS code %s not in downloaded data — skipping %s", bis_code, ccy)
            continue
        selected[ccy] = raw[bis_code]

    df = pd.DataFrame(selected)
    df = df.loc[start:end]

    if apply_pub_lag:
        df = df.shift(_PUBLICATION_LAG_MONTHS)
        log.info("Applied %d-month publication lag to BIS REER", _PUBLICATION_LAG_MONTHS)

    missing = [c for c in currencies if c not in df.columns]
    if missing:
        log.warning("Missing BIS REER currencies: %s", missing)

    return df


def compute_reer_zscore(
    reer:         pd.DataFrame,
    window_years: int = 10,
) -> pd.DataFrame:
    """
    Rolling z-score of REER level relative to trailing window mean.

    Positive z-score = overvalued relative to its own history.
    Used in signal construction as: ``signal_reer = -z_score`` (overvalued → short).

    Parameters
    ----------
    reer         : output of load_bis_reer().
    window_years : lookback for mean/std computation (default 10 years = 120 months).

    Returns
    -------
    pd.DataFrame
        Same shape as ``reer``, values in z-score units.
        NaN for the first ``window_years * 12`` months (no full history).
    """
    w = window_years * 12
    mean = reer.rolling(w, min_periods=int(w * 0.8)).mean()
    std  = reer.rolling(w, min_periods=int(w * 0.8)).std(ddof=1)
    z    = (reer - mean) / std.replace(0, np.nan)
    return z


# ─────────────────────────────────────────────────────────────────────────────
# Sanity check
# ─────────────────────────────────────────────────────────────────────────────

def _sanity() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("=" * 68)
    print("BIS REER Sanity Check")
    print("=" * 68)

    reer = load_bis_reer()
    print(f"\nShape: {reer.shape}")
    print(f"Date range: {reer.index[0].date()} → {reer.index[-1].date()}")
    print("\nNaN counts (after pub-lag shift):")
    print(reer.isna().sum().to_string())
    print("\nHead (2005-01 to 2005-03):")
    print(reer.loc["2005-01":"2005-03"].round(2).to_string())
    print("\nTail (last 3 months):")
    print(reer.tail(3).round(2).to_string())
    print("\nMean REER level (2005-2023, 2020=100 base):")
    print(reer.loc["2005":"2023"].mean().round(2).to_string())

    z = compute_reer_zscore(reer)
    print("\nREER z-scores (10Y window) — tail:")
    print(z.tail(3).round(2).to_string())
    print("\nZ-score NaN fraction (first 120 months expected):")
    print((z.isna().mean() * 100).round(1).astype(str).add(" %").to_string())


if __name__ == "__main__":
    _sanity()
