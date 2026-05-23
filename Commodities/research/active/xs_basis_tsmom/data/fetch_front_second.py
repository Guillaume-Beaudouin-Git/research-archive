"""
fetch_front_second.py — Basis (term structure) proxy for commodity futures.

Since front+second-month individual contracts are not available on free platforms
without an API key, we use the Roll-Gap Proxy approach (Approach C):

  At each roll date the continuous =F price jumps from P_near (expiring front)
  to P_far (new front = previous second month):

    roll_ret = log(P_after_roll) - log(P_before_roll) = log(F_far / F_near)
    basis_proxy = -roll_ret × 12  (annualized; positive = backwardation)

  This matches the academic basis definition:
    basis_actual = (P_front - P_second) / P_front × 12  →  positive in backwardation

Roll dates are identified from detect_roll_artifacts() with threshold_sigma=3.0
(lower than the 5σ validation threshold to catch smaller rolls).

The output is a monthly-sampled basis series: at each month-end, the most recent
roll-gap basis estimate is used (or NaN if no roll detected in the preceding 3m).

Basis sign convention (S_BASIS from README):
  signal[t, i] = -basis_proxy[t-1, i]    ← already inverted here
  → Positive signal when basis_proxy < 0 (backwardation) = bullish expectation
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .roll_validation import detect_roll_artifacts

log = logging.getLogger(__name__)

ROLL_SIGMA_BASIS  = 3.0   # lower threshold for basis detection (catches small rolls)
MAX_STALENESS_M   = 3     # maximum months between rolls before basis marked NaN
MONTHS_TO_EXPIRY  = 1.0   # approximate months between front and second month (annualize ×12)


def build_basis_monthly(
    close_df:     pd.DataFrame,
    threshold_sigma: float = ROLL_SIGMA_BASIS,
) -> pd.DataFrame:
    """
    Build monthly basis proxy for all tickers via roll-gap detection.

    Parameters
    ----------
    close_df : pd.DataFrame with (ticker, 'close') MultiIndex columns

    Returns
    -------
    pd.DataFrame
        Index: month-end DatetimeIndex
        Columns: ticker codes
        Values: annualized basis proxy (positive = backwardation)
    """
    if isinstance(close_df.columns, pd.MultiIndex):
        level1 = close_df.columns.get_level_values(1)
        if "close" in level1:
            close = close_df.xs("close", axis=1, level=1)
        else:
            close = close_df.iloc[:, ::5]
    else:
        close = close_df

    roll_df = detect_roll_artifacts(close, threshold_sigma=threshold_sigma)
    roll_df = roll_df[roll_df["is_roll_artifact"]].copy()

    tickers = close.columns.tolist()
    # Build month-end index (shared across tickers)
    date_range    = pd.date_range(close.index.min(), close.index.max(), freq="ME")
    basis_monthly = pd.DataFrame(index=date_range, columns=tickers, dtype=float)

    for ticker in tickers:
        tdf = roll_df[roll_df["ticker"] == ticker].set_index("date")

        if tdf.empty:
            log.warning(
                "basis: no roll artifacts detected for %s — basis will be NaN",
                ticker,
            )
            continue

        # For each month-end: find the most recent roll in the preceding MAX_STALENESS_M months
        basis_series = tdf["basis_proxy_annualized"]

        for month_end in date_range:
            lookback_start = month_end - pd.DateOffset(months=MAX_STALENESS_M)
            window         = basis_series[
                (basis_series.index > lookback_start) & (basis_series.index <= month_end)
            ]
            if not window.empty:
                # Use the most recent roll gap as the basis estimate
                basis_monthly.loc[month_end, ticker] = window.iloc[-1]
            # else: remains NaN (no recent roll → basis unknown)

    # Coverage report
    n_total   = len(date_range) * len(tickers)
    n_valid   = basis_monthly.notna().sum().sum()
    log.info(
        "build_basis_monthly: %.1f%% coverage (%d/%d ticker-months)",
        100 * n_valid / n_total if n_total > 0 else 0,
        n_valid, n_total,
    )

    return basis_monthly.sort_index()
