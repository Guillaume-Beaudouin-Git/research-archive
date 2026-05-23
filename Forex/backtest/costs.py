"""
Forex/backtest/costs.py
=======================
FX transaction cost model: spreads, swap costs, triple-Wednesday roll.

All costs in annualised % terms when computing Sharpe impact.

Public API
----------
spread_cost_monthly(weights, ccy_class_map) -> pd.Series
    Monthly cost from portfolio turnover × half-spread per currency.

swap_cost_monthly(weights, rates, rf_rate, short_leg_multiplier) -> pd.Series
    Monthly financing cost on short leg (retail swap = interbank × multiplier).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# Spread model: round-trip pips by currency class, converted to % of notional
# EUR/USD pip ≈ 0.0001; for 1.08 spot, 0.5 pip RT = 0.0005/1.08 ≈ 0.046 bps
_SPREAD_PIPS_RT: dict[str, float] = {
    "EUR": 0.5, "GBP": 0.5, "AUD": 0.5, "NZD": 0.5,   # majors
    "JPY": 1.0, "CHF": 1.0, "CAD": 1.0,                  # minor G10
    "NOK": 1.0, "SEK": 1.0,
    "BRL": 15.0, "MXN": 8.0, "ZAR": 12.0, "INR": 20.0, "TRY": 30.0,
}

_APPROX_SPOT: dict[str, float] = {
    "EUR": 1.08, "GBP": 1.26, "JPY": 155.0, "CHF": 0.90,
    "AUD": 0.66, "CAD": 1.37, "NZD": 0.61, "NOK": 10.6,
    "SEK": 10.5, "BRL": 5.0, "MXN": 17.0, "ZAR": 18.5,
    "INR": 83.0, "TRY": 32.0,
}

# JPY pip = 0.01; others = 0.0001
_PIP_SIZE: dict[str, float] = {ccy: (0.01 if ccy == "JPY" else 0.0001)
                                 for ccy in _SPREAD_PIPS_RT}


def spread_pct_rt(ccy: str) -> float:
    """Round-trip spread cost as % of notional for a single currency."""
    pips  = _SPREAD_PIPS_RT.get(ccy, 2.0)
    pip   = _PIP_SIZE.get(ccy, 0.0001)
    spot  = _APPROX_SPOT.get(ccy, 1.0)
    # For XXXUSD: cost = pips × pip_size × 1/spot × 100 (as %)
    # But for XXXUSD prices, 1 pip on EURUSD = 0.0001 USD per EUR
    # cost% = pips × pip_size / spot × 100 = cost / notional_USD × 100
    return float(pips * pip / spot * 100)


def spread_cost_monthly(
    weights: pd.DataFrame,
    *,
    min_trade_threshold: float = 0.01,
) -> pd.Series:
    """
    Monthly transaction cost from portfolio turnover.

    Cost = sum(|Δweight| × spread_pct_rt / 2) per month.
    Half spread (buy side); the other half is paid on exit.

    Parameters
    ----------
    weights                : (T × N) portfolio weights DataFrame.
    min_trade_threshold    : ignore position changes below this fraction.

    Returns
    -------
    pd.Series : monthly cost in decimal returns (e.g., 0.0005 = 0.05%).
    """
    turnover = (weights - weights.shift(1)).abs()
    turnover[turnover < min_trade_threshold] = 0.0

    cost_per_unit = pd.Series({ccy: spread_pct_rt(ccy) / 100 / 2
                                for ccy in weights.columns})
    monthly_cost = (turnover * cost_per_unit).sum(axis=1)
    return monthly_cost.rename("spread_cost")


def swap_cost_monthly(
    weights:              pd.DataFrame,
    rates:                pd.DataFrame,
    rf_rate:              pd.Series,
    short_leg_multiplier: float = 1.5,
) -> pd.Series:
    """
    Monthly financing cost on short leg (retail swap).

    For short positions, broker charges: interbank_rate × multiplier.
    For long positions, broker pays: interbank_rate × (1 / multiplier).

    Parameters
    ----------
    weights              : (T × N) portfolio weights (-1 to +1).
    rates                : (T × N) 3M interbank rates, % p.a.
    rf_rate              : (T,) US 3M rate, % p.a.
    short_leg_multiplier : retail spread on short leg (default 1.5×).

    Returns
    -------
    pd.Series : monthly financing cost in decimal (e.g., −0.001 = −0.1%/month).
    """
    # Convert annual % to monthly decimal
    r_monthly = rates.div(1200)
    rf_monthly = rf_rate.div(1200)

    short_mask = weights < 0
    long_mask  = weights > 0

    # Short position cost: pay rate × multiplier
    short_cost = (short_mask * weights.abs() * r_monthly * short_leg_multiplier)
    # Long position benefit: receive rate / multiplier (funding rebate)
    long_rebate = (long_mask * weights.abs() * r_monthly / short_leg_multiplier)

    net = (short_cost - long_rebate).sum(axis=1)
    return net.rename("swap_cost")
