"""
Signal computation for TSMOM v2.

Signal rule (unchanged from v1):
    signal(t) = sign(sum of log_returns from t-28 to t-1)

Long-only modification:
    signal(t) = 1  if 28-day return > 0
              = 0  otherwise  (flat — no shorting)

v1 backtests showed short crypto TSMOM does not generate positive alpha
after costs; all short signals are suppressed to flat.

No look-ahead guarantee:
    The .shift(1) in rolling().sum() ensures the signal at time t only
    incorporates data through t-1. The position taken at t's open uses
    signal computed from t-1's close — same as v1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.tsmom_v2_propfirm.config import LOOKBACK_DAYS


def compute_signal(
    prices_df: pd.DataFrame,
    lookback: int = LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    Compute long-only TSMOM signal for a universe of assets.

    For each asset at each date t:
        momentum(t) = sum(log_returns[t-lookback : t-1])
        signal(t)   = 1  if momentum(t) > 0
                    = 0  if momentum(t) <= 0  (no shorting)
                    = NaN if fewer than `lookback` days of history

    Implementation detail:
        rolling(lookback).sum() at index t accumulates [t-lookback+1 : t].
        After .shift(1): value at t = sum of [t-lookback : t-1].
        This is the MOP (2012) definition with a 1-day execution lag.

    Parameters
    ----------
    prices_df : DataFrame of daily close prices (date × asset ticker).
                Missing assets (NaN columns) are handled transparently.
    lookback  : momentum window in calendar days (default: 28).

    Returns
    -------
    pd.DataFrame
        Same shape as prices_df. Values in {0.0, 1.0, NaN}.
        NaN indicates insufficient history (first `lookback` rows per asset).
    """
    log_returns = np.log(prices_df / prices_df.shift(1))
    # rolling().sum() at t covers [t-lookback+1 : t]; shift(1) makes it [t-lookback : t-1]
    cum_return = log_returns.rolling(lookback).sum().shift(1)

    # Long-only: 1 if positive momentum, 0 if zero or negative
    signal = (cum_return > 0).astype(float)
    # Preserve NaN for the warm-up period
    signal[cum_return.isna()] = np.nan
    return signal


def apply_weekly_rebalance(
    daily_signals: pd.DataFrame,
    rebalance_weekday: int = 0,
) -> pd.DataFrame:
    """
    Convert daily signals to weekly-rebalanced positions.

    Positions are updated only on the specified weekday (default Monday).
    Between rebalance days, the position from the last Monday is carried
    forward unchanged. This models a once-weekly order submission cycle.

    Parameters
    ----------
    daily_signals    : DataFrame of daily signals (output of compute_signal).
    rebalance_weekday: weekday index to rebalance on (0=Mon … 6=Sun).

    Returns
    -------
    pd.DataFrame
        Same shape as daily_signals. Signal is constant within each week,
        updating only on the specified rebalance day.
    """
    is_rebalance_day = pd.Series(
        daily_signals.index.dayofweek == rebalance_weekday,
        index=daily_signals.index,
        dtype=bool,
    )
    # Keep signal only on rebalance days; NaN on all other days
    rebalance_signals = daily_signals.where(is_rebalance_day)
    # Forward-fill: carry position until next rebalance day
    return rebalance_signals.ffill()
