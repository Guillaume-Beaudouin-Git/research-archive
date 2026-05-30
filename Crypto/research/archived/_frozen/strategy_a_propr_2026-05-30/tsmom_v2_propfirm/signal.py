"""
Signal computation for TSMOM v2 (C1 continuous update, 2026-05).

Signal rule (C1 — Zarattini 2025 continuous t-stat):
    vol_28d(t)  = std(log_returns[t-28 : t-1]) × √365   (annualized)
    t_stat(t)   = cum_log_ret(t) / (vol_28d(t) × √28 + ε)
    signal(t)   = tanh(t_stat(t))                        # continuous (−1, +1)

Long-only modification for Propr live:
    signal_live(t) = clip(signal(t), 0, +∞)             # suppress short leg

Improvement over binary sign():
    OOS Sharpe 1.33 vs 1.22 (+0.11), MaxDD −6.9% vs −12.7%, 3/4 WF folds.
    Continuous signal naturally scales position with trend conviction;
    weak trends → partial position; strong trends → near-full position.

No look-ahead guarantee:
    The .shift(1) in rolling().sum()/.std() ensures the signal at time t
    only incorporates data through t-1. The position taken at t's open uses
    signal computed from t-1's close.
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
    Compute long-only TSMOM signal for a universe of assets (C1 continuous).

    For each asset at each date t:
        cum_return(t) = sum(log_returns[t-lookback : t-1])
        vol_28d(t)    = std(log_returns[t-lookback : t-1]) × √365
        t_stat(t)     = cum_return(t) / (vol_28d(t) × √lookback + ε)
        signal(t)     = tanh(t_stat(t)), clipped to [0, +∞] for long-only

    Implementation detail:
        rolling(lookback).sum()/.std() at index t covers [t-lookback+1 : t].
        After .shift(1): value at t uses data [t-lookback : t-1].
        This is the MOP (2012) definition with a 1-day execution lag.

    Parameters
    ----------
    prices_df : DataFrame of daily close prices (date × asset ticker).
                Missing assets (NaN columns) are handled transparently.
    lookback  : momentum window in calendar days (default: 28).

    Returns
    -------
    pd.DataFrame
        Same shape as prices_df. Values in [0.0, 1.0) (continuous), or NaN.
        NaN indicates insufficient history (first `lookback` rows per asset).
    """
    log_returns = np.log(prices_df / prices_df.shift(1))
    # rolling().sum()/.std() at t covers [t-lookback+1 : t]; shift(1) → [t-lookback : t-1]
    cum_return = log_returns.rolling(lookback).sum().shift(1)

    # C1 continuous signal: tanh(t-stat), clipped to [0, 1] for long-only (Propr)
    # vol = std × √lookback gives a dimensionless t-stat (tested in tsmom_v3/backtest.py)
    vol_L  = log_returns.rolling(lookback).std().shift(1) * np.sqrt(lookback)
    t_stat = cum_return / (vol_L + 1e-8)
    signal = np.tanh(t_stat).clip(lower=0.0)
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
