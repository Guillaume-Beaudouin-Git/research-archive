"""
Forex/backtest/vol_targeting.py
================================
Daily volatility targeting: position size ∝ 1 / realized_vol.

vol_target_weights(weights, returns, target_vol, window_months) -> pd.DataFrame
    Scale a weights DataFrame so that the portfolio targets a specified
    annualised volatility (monthly returns basis).

portfolio_vol(weights, returns, window) -> pd.Series
    Rolling realised portfolio volatility (annualised).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ANN_FACTOR: int = 12   # monthly → annual


def portfolio_vol(
    weights: pd.DataFrame,
    returns: pd.DataFrame,
    window:  int = 3,
) -> pd.Series:
    """
    Rolling realised portfolio volatility, annualised.

    Parameters
    ----------
    weights : (T × N) portfolio weights (lagged by 1 period in caller).
    returns : (T × N) asset returns (same period as weights).
    window  : rolling months for volatility estimation (default 3).

    Returns
    -------
    pd.Series : annualised portfolio volatility (decimal, e.g., 0.10 = 10%).
    """
    port_ret = (weights * returns).sum(axis=1).fillna(0)
    vol = port_ret.rolling(window, min_periods=2).std(ddof=1) * np.sqrt(ANN_FACTOR)
    return vol.rename("port_vol")


def vol_target_weights(
    weights:     pd.DataFrame,
    returns:     pd.DataFrame,
    target_vol:  float = 0.10,
    window:      int   = 3,
    max_leverage: float = 3.0,
) -> pd.DataFrame:
    """
    Scale portfolio weights to target annualised volatility.

    scaler[t] = target_vol / realized_vol[t-1]
    scaled_weights[t] = weights[t] × clamp(scaler[t], 0, max_leverage)

    Parameters
    ----------
    weights     : (T × N) unscaled weights (long + short, dollar-neutral).
    returns     : (T × N) asset returns for vol estimation.
    target_vol  : annualised portfolio vol target (default 10%).
    window      : months for rolling vol estimation.
    max_leverage: cap on vol-scaling factor (default 3×, prevents over-leverage
                  in low-vol regimes like 2014-2019 for FX).

    Returns
    -------
    pd.DataFrame : vol-scaled weights, same shape as input.
    """
    # Estimate vol on unscaled weights (positions proportional to signal)
    pvol = portfolio_vol(weights.shift(1), returns, window)
    scaler = (target_vol / pvol.shift(1)).clip(upper=max_leverage)
    scaler = scaler.fillna(1.0)   # no scaling in first window

    scaled = weights.multiply(scaler, axis=0)
    return scaled
