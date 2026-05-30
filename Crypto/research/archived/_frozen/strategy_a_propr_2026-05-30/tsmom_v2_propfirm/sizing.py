"""
Position sizing for TSMOM v2 with prop-firm guardrails.

Sizing pipeline (per asset, per rebalance):
    1. Realized vol  = std(log_returns[t-20 : t-1]) × √365  (annualized)
    2. Vol scalar    = clip(vol_target / realized_vol, 0.1, 2.0)
    3. Raw position  = signal × vol_scalar  (long-only: ≥ 0)
    4. Guardrail     = zero-out all positions if daily or total DD is breached

Equal-weight interpretation:
    Each long asset independently targets `vol_target` annualized vol.
    This is consistent with v1 (where portfolio return = mean of per-asset
    returns, each independently vol-targeted). Portfolio vol is lower than
    per-asset target thanks to diversification:
        port_vol ≈ vol_target × √(n_long × avg_pair_corr)

No look-ahead:
    The vol scalar uses .shift(1) on the rolling std, so at time t only
    data through t-1 is used — identical to v1's guarantee.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.tsmom_v2_propfirm.config import (
    MAX_DAILY_DRAWDOWN,
    MAX_TOTAL_DRAWDOWN,
    STOP_LOSS_VOL_MULT,
    TRADING_DAYS_PER_YEAR,
    VOL_LOOKBACK_DAYS,
    VOL_SCALAR_MAX,
    VOL_SCALAR_MIN,
)


def compute_vol_scalars(
    log_returns_df: pd.DataFrame,
    vol_target: float,
    vol_lookback: int = VOL_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """
    Compute per-asset volatility scaling factors with no look-ahead bias.

    vol_scalar(t, asset) = clip(
        vol_target / (std(log_returns[t-vol_lookback : t-1]) × √365),
        VOL_SCALAR_MIN,
        VOL_SCALAR_MAX,
    )

    The .shift(1) ensures the scalar at time t is computed from data
    available at the close of t-1 — no information from today is used.

    Parameters
    ----------
    log_returns_df : DataFrame of daily log returns (date × asset).
    vol_target     : annualized volatility target (e.g. 0.15 for 15%).
    vol_lookback   : rolling window for vol estimation in days (default 20).

    Returns
    -------
    pd.DataFrame
        Scaling factors clipped to [VOL_SCALAR_MIN, VOL_SCALAR_MAX].
        NaN where fewer than `vol_lookback` days of history exist.
    """
    ann_vol = (
        log_returns_df.rolling(vol_lookback).std()
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )
    scalars = (vol_target / ann_vol).shift(1)
    return scalars.clip(VOL_SCALAR_MIN, VOL_SCALAR_MAX)


def compute_positions(
    signals: pd.DataFrame,
    vol_scalars: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute raw (pre-guardrail) position sizes for each asset.

    position(t, asset) = signal(t, asset) × vol_scalar(t, asset)

    Because signals are long-only ({0, 1}), positions are non-negative.
    A position of 1.0 corresponds exactly to the vol-target leverage;
    values above 1.0 occur when realized vol is below the target.

    Parameters
    ----------
    signals     : DataFrame of {0.0, 1.0, NaN} (date × asset).
    vol_scalars : DataFrame of scaling factors  (date × asset).

    Returns
    -------
    pd.DataFrame
        Position sizes ∈ [0, VOL_SCALAR_MAX] per cell; NaN where signal
        or vol_scalar is NaN (insufficient history).
    """
    return signals * vol_scalars


def check_guardrails(
    current_equity: float,
    day_start_equity: float,
    peak_equity: float,
) -> tuple[bool, str]:
    """
    Check whether any prop-firm drawdown guardrail has been breached.

    Evaluated before every order submission in live trading.

    Parameters
    ----------
    current_equity    : current account equity (NAV).
    day_start_equity  : equity at 00:00 UTC today (for daily DD check).
    peak_equity       : highest equity reached since challenge start.

    Returns
    -------
    (kill_switch, reason)
        kill_switch : True if positions must be flattened immediately.
        reason      : human-readable explanation (empty string if no breach).
    """
    daily_dd = (current_equity - day_start_equity) / day_start_equity
    total_dd = (current_equity - peak_equity) / peak_equity

    if daily_dd <= -MAX_DAILY_DRAWDOWN:
        return True, (
            f"Daily DD breached: {daily_dd:.2%} ≤ −{MAX_DAILY_DRAWDOWN:.1%}. "
            "Flattening all positions."
        )
    if total_dd <= -MAX_TOTAL_DRAWDOWN:
        return True, (
            f"Total DD breached: {total_dd:.2%} ≤ −{MAX_TOTAL_DRAWDOWN:.1%}. "
            "Flattening all positions."
        )
    return False, ""


def apply_guardrails(
    positions: pd.DataFrame,
    equity_curve: pd.Series,
    daily_start_equity: float,
    peak_equity: float,
) -> tuple[pd.DataFrame, bool]:
    """
    Apply prop-firm guardrails to a position DataFrame (vectorized, for backtest).

    Uses the last value in `equity_curve` as the current equity snapshot.
    In live trading, call check_guardrails() directly instead.

    Parameters
    ----------
    positions          : DataFrame of position sizes to potentially zero out.
    equity_curve       : Series of equity values (last entry = current equity).
    daily_start_equity : equity at the start of today.
    peak_equity        : peak equity since challenge start.

    Returns
    -------
    (adjusted_positions, kill_switch_triggered)
    """
    current_equity = float(equity_curve.iloc[-1])
    kill, _ = check_guardrails(current_equity, daily_start_equity, peak_equity)
    if kill:
        return pd.DataFrame(0.0, index=positions.index, columns=positions.columns), True
    return positions, False


def compute_stop_price(
    entry_price: float,
    daily_vol: float,
    direction: int = 1,
    vol_mult: float = STOP_LOSS_VOL_MULT,
) -> float:
    """
    Compute the hard stop-loss price to place on the exchange at order fill.

    Per HyroTrader requirements and sound risk management:
        long stop  = entry_price × (1 − vol_mult × daily_vol)
        short stop = entry_price × (1 + vol_mult × daily_vol)

    Parameters
    ----------
    entry_price : execution price of the trade (fill price).
    daily_vol   : realized daily volatility as a fraction (e.g. 0.03 = 3%).
                  Typically computed as ann_vol / √365.
    direction   : +1 for long position, −1 for short (future use).
    vol_mult    : multiplier on daily vol (default 2.0 per config).

    Returns
    -------
    float
        Stop-loss price to submit as a stop-market order.

    Example
    -------
    >>> compute_stop_price(entry_price=50_000, daily_vol=0.03)
    47000.0
    """
    offset = vol_mult * daily_vol
    if direction == 1:
        return entry_price * (1.0 - offset)
    return entry_price * (1.0 + offset)
