"""
S3 — Turn-of-Month (TOM) signal.

Signal: binary dummy = 1 on trading days in the window [-1, +3] business days
        around the last trading day of each calendar month.
        0 on all other days.

Day offset convention:
  offset = 0  → last trading day of month
  offset = -1 → penultimate trading day of month  (1 BD before)
  offset = +1 → first trading day of next month
  offset = +2 → second trading day of next month
  offset = +3 → third trading day of next month

Mechanism: institutional rebalancing flows and month-end fixings push prices up in
this 5-day window (Ariel 1987, Lakonishok & Smidt 1988).

Amendment 2: compute event-study stats (mean return by day offset, t-stat per offset)
and save to results/s3_tom_event_study.csv.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

TOM_WINDOW = (-1, +3)   # [start_offset, end_offset] inclusive


def compute_s3_tom(U: dict[str, Any]) -> pd.DataFrame:
    """
    Compute TOM binary signal for each asset (same signal value, applied to all tickers).

    Returns
    -------
    pd.DataFrame — Index: trading days, Columns: [SPY, QQQ, EWQ]
    """
    idx     = U["prices"].index
    signal  = _build_tom_signal(idx)
    tickers = [t for t in ["SPY", "QQQ", "EWQ"] if (t, "close") in U["prices"].columns]
    out = pd.DataFrame({t: signal for t in tickers}, index=idx)
    log.info("S3 TOM: %d event days out of %d total (%.1f%%)",
             signal.sum(), len(signal), 100 * signal.mean())
    return out


def compute_s3_event_study(
    U: dict[str, Any],
    ticker: str = "SPY",
    h: int = 1,
) -> pd.DataFrame:
    """
    Event-study statistics for TOM by day offset.

    Parameters
    ----------
    U      : universe dict
    ticker : asset to measure (default SPY)
    h      : forward horizon for return (default 1)

    Returns
    -------
    pd.DataFrame with columns: offset, n_events, mean_ret, std_ret, t_stat
    Saved to results/s3_tom_event_study.csv by run_all_signals.py.
    """
    idx       = U["prices"].index
    fwd       = U["fwd_ret"].get((ticker, h), pd.Series(dtype=float))
    log_close = np.log(U["prices"][(ticker, "close")])
    daily_ret = log_close.diff()

    # Identify month-end dates (last trading day of each calendar month)
    month_ends = _get_month_ends(idx)

    rows = []
    for offset in range(TOM_WINDOW[0], TOM_WINDOW[1] + 1):
        # For each month-end, find the trading day at `offset`
        returns = []
        for me in month_ends:
            pos = idx.get_loc(me)
            target_pos = pos + offset
            if 0 <= target_pos < len(idx):
                r = daily_ret.iloc[target_pos]
                if pd.notna(r):
                    returns.append(r)

        n = len(returns)
        if n < 5:
            rows.append({"offset": offset, "n_events": n,
                         "mean_ret": np.nan, "std_ret": np.nan, "t_stat": np.nan})
            continue

        arr = np.array(returns)
        mean_r = arr.mean()
        std_r  = arr.std(ddof=1)
        t_stat = mean_r / (std_r / np.sqrt(n)) if std_r > 0 else np.nan
        rows.append({
            "offset":    offset,
            "n_events":  n,
            "mean_ret":  round(mean_r, 6),
            "std_ret":   round(std_r, 6),
            "t_stat":    round(t_stat, 3),
        })

    df = pd.DataFrame(rows)
    log.info("S3 event study (%s, h=%d): %d offsets", ticker, h, len(df))
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_month_ends(trading_days: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Return the set of trading days that are the last trading day of their calendar month."""
    is_last = trading_days.to_series().groupby(
        [trading_days.year, trading_days.month]
    ).transform("last") == trading_days.to_series()
    return trading_days[is_last.values]


def _build_tom_signal(trading_days: pd.DatetimeIndex) -> pd.Series:
    """
    Build TOM binary dummy (1 in window, 0 outside).

    No look-ahead: the signal at date T depends only on calendar position,
    which is known at market open on T.
    """
    month_ends = _get_month_ends(trading_days)
    signal     = pd.Series(0, index=trading_days, dtype=float)

    for me in month_ends:
        pos = trading_days.get_loc(me)
        for offset in range(TOM_WINDOW[0], TOM_WINDOW[1] + 1):
            target = pos + offset
            if 0 <= target < len(trading_days):
                signal.iloc[target] = 1.0

    return signal
