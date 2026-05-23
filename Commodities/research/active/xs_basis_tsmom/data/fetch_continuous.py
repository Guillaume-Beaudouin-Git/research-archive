"""
fetch_continuous.py — Daily OHLCV for 24 commodity futures continuous contracts.

Data source: yfinance `=F` tickers (continuous front-month, price-spliced at roll).
Stooq was the spec-preferred source but now requires a paid API key (HTTP returns
empty body). yfinance =F contracts are methodologically equivalent: both provide
continuous front-month futures at unadjusted (spliced) prices, so roll-date price
gaps remain visible for basis-proxy construction.

Returned DataFrame uses (ticker_code, field) MultiIndex columns where:
  ticker_code ∈ COMMODITY_CODES  (e.g. "CL", "GC")
  field        ∈ {close, open, high, low, volume}
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[5]   # Algo_claude/
sys.path.insert(0, str(ROOT))

log = logging.getLogger(__name__)

# ── Universe definition ───────────────────────────────────────────────────────
# code → yfinance ticker (continuous front-month)
COMMODITY_UNIVERSE: dict[str, str] = {
    # Energy
    "CL": "CL=F",   # WTI Crude Oil   (NYMEX, from 2005)
    "BZ": "BZ=F",   # Brent Crude     (ICE, from 2007-07)
    "NG": "NG=F",   # Natural Gas      (NYMEX, from 2005)
    "HO": "HO=F",   # Heating Oil #2   (NYMEX, from 2005)
    "RB": "RB=F",   # RBOB Gasoline    (NYMEX, from 2005)
    # Precious metals
    "GC": "GC=F",   # Gold             (COMEX, from 2005)
    "SI": "SI=F",   # Silver           (COMEX, from 2005)
    "PL": "PL=F",   # Platinum         (NYMEX, from 2005)
    "PA": "PA=F",   # Palladium        (NYMEX, from 2005)
    # Industrial
    "HG": "HG=F",   # Copper (High Grade) (COMEX, from 2005)
    # Grains
    "ZC": "ZC=F",   # Corn             (CBOT, from 2005)
    "ZS": "ZS=F",   # Soybeans         (CBOT, from 2005)
    "ZW": "ZW=F",   # Wheat (CBOT)     (CBOT, from 2005)
    "ZM": "ZM=F",   # Soybean Meal     (CBOT, from 2005)
    "ZL": "ZL=F",   # Soybean Oil      (CBOT, from 2005)
    "ZO": "ZO=F",   # Oats             (CBOT, from 2005)
    # Softs
    "KC": "KC=F",   # Coffee C         (ICE, from 2005)
    "SB": "SB=F",   # Sugar #11        (ICE, from 2005)
    "CC": "CC=F",   # Cocoa            (ICE, from 2005)
    "CT": "CT=F",   # Cotton #2        (ICE, from 2005)
    "OJ": "OJ=F",   # Orange Juice     (ICE, from 2005)
    # Livestock
    "LE": "LE=F",   # Live Cattle      (CME, from 2005)
    "HE": "HE=F",   # Lean Hogs        (CME, from 2005)
    "GF": "GF=F",   # Feeder Cattle    (CME, from 2005)
}

COMMODITY_CODES: list[str] = list(COMMODITY_UNIVERSE.keys())


def fetch_all_continuous(
    codes:        Sequence[str] | None = None,
    start:        str   = "2005-01-01",
    end:          str | None = None,
    max_age_days: int   = 3,
) -> pd.DataFrame:
    """
    Fetch daily OHLCV for all (or selected) commodity futures.

    Returns
    -------
    pd.DataFrame
        MultiIndex columns: (code, field) where field ∈ {close, open, high, low, volume}
        Index: DatetimeIndex (daily, tz-naive, NYSE-aligned trading days)
        NaN where a contract has no data for that period.
    """
    from data.cache import get_cached_or_fetch

    codes  = list(codes) if codes else COMMODITY_CODES
    end    = end or pd.Timestamp.today().strftime("%Y-%m-%d")

    frames: list[pd.Series] = []
    missing: list[str] = []

    for code in codes:
        yf_ticker = COMMODITY_UNIVERSE.get(code)
        if yf_ticker is None:
            log.warning("Unknown commodity code: %s — skipping", code)
            continue

        try:
            raw = get_cached_or_fetch(yf_ticker, start, end, interval="1d", max_age_days=max_age_days)
        except Exception as exc:
            log.warning("fetch_continuous: %s (%s) failed: %s", code, yf_ticker, exc)
            missing.append(code)
            continue

        if raw.empty:
            log.warning("fetch_continuous: %s (%s) returned empty DataFrame", code, yf_ticker)
            missing.append(code)
            continue

        # Normalize column names (yfinance returns lower-case via get_cached_or_fetch)
        raw_cols = {c[1].lower() if isinstance(c, tuple) else c.lower(): c for c in raw.columns}
        for field in ("close", "open", "high", "low", "volume"):
            src_col = raw_cols.get(field) or raw_cols.get(f"{yf_ticker.lower()}_{field}")
            # Try the MultiIndex (ticker, field) pattern from get_cached_or_fetch
            mi_key = (yf_ticker, field)
            if mi_key in raw.columns:
                s = raw[mi_key].copy()
            elif src_col is not None:
                s = raw[src_col].copy()
            else:
                s = pd.Series(np.nan, index=raw.index, name=(code, field))
            s.name = (code, field)
            frames.append(s)

        n_obs = (raw[mi_key] if mi_key in raw.columns else raw.iloc[:, 0]).notna().sum()
        log.info("  %-4s (%s): %d non-NaN obs", code, yf_ticker, n_obs)

    if missing:
        log.warning("fetch_continuous: %d tickers failed: %s", len(missing), missing)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, axis=1)
    out.columns = pd.MultiIndex.from_tuples(out.columns)
    out.index   = pd.to_datetime(out.index).tz_localize(None).normalize()
    return out.sort_index()
