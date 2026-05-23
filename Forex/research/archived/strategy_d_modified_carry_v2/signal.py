"""
strategy_d_modified_carry/signal.py
=====================================
Signal construction for Strategy D: Modified FX Carry.

build_signal(rates, fx_px, reer, cpi, ca_gdp, weights) -> pd.DataFrame
    Pre-registered composite signal (hypothesis.md §3).
    Returns monthly cross-sectional signal aligned to trading calendar.

Note: All data inputs must be T-1 shifted BEFORE calling this function
(i.e., signal at T-1 for trade at T). Shifting is done in the caller.

STATUS: STUB — used in full backtest.py, NOT in ic_feasibility.py.
       ic_feasibility.py builds its own inline signal for testing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# Pre-registered initial weights (hypothesis.md §3.3)
DEFAULT_WEIGHTS = {
    "carry":     0.50,
    "reer":      0.20,
    "ca_gdp":    0.15,
    "inflation": 0.15,
}

G10_CCYS = ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD", "NOK", "SEK"]


def _cs_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional z-score: standardise each row across currencies."""
    return df.sub(df.mean(axis=1), axis=0).div(df.std(axis=1, ddof=1), axis=0)


def build_carry(rates: pd.DataFrame, usd_rate: pd.Series) -> pd.DataFrame:
    """
    Raw carry = r_foreign - r_USD (all in % p.a.).

    Parameters
    ----------
    rates    : (T × N) monthly 3M rates for G10 currencies.
    usd_rate : (T,) monthly US 3M rate.

    Returns
    -------
    pd.DataFrame : (T × N) carry in % p.a.
    """
    carry = rates.sub(usd_rate, axis=0)
    return carry


def build_reer_signal(reer: pd.DataFrame, window_years: int = 10) -> pd.DataFrame:
    """
    REER valuation signal: negative z-score of REER deviation.
    Overvalued (high REER) → negative signal (reduce carry weight).

    Parameters
    ----------
    reer         : BIS REER levels (2020=100), publication lag already applied.
    window_years : lookback for z-score computation.

    Returns
    -------
    pd.DataFrame : (T × N) signal, positive = undervalued (support carry).
    """
    from Forex.data.bis_reer_loader import compute_reer_zscore
    z = compute_reer_zscore(reer, window_years)
    return -z   # overvalued = positive z → negative signal


def build_inflation_signal(cpi: pd.DataFrame, usd_cpi: pd.Series,
                            smooth_months: int = 12) -> pd.DataFrame:
    """
    Inflation differential signal: low foreign inflation vs USD = positive.
    High inflation → currency likely to depreciate → negative carry signal.

    Parameters
    ----------
    cpi         : (T × N) foreign CPI y/y %.
    usd_cpi     : (T,) US CPI y/y %.
    smooth_months : Gaussian smoothing window.
    """
    infl_diff = cpi.sub(usd_cpi, axis=0)
    # Gaussian smoothing (approximate with rolling mean)
    smoothed = infl_diff.rolling(smooth_months, min_periods=6).mean()
    return -smoothed   # high inflation differential → negative signal


def build_signal(
    rates:    pd.DataFrame,
    reer:     pd.DataFrame,
    cpi:      pd.DataFrame | None = None,
    ca_gdp:   pd.DataFrame | None = None,
    ccys:     list[str] | None    = None,
    weights:  dict | None         = None,
) -> pd.DataFrame:
    """
    Composite modified carry signal (pre-registered weights).

    Each factor is cross-sectionally z-scored before combining.
    Signal at T-1: caller is responsible for applying .shift(1) to all inputs.

    Parameters
    ----------
    rates   : (T × N+1) monthly 3M rates, includes 'USD' column.
    reer    : (T × N) BIS REER levels, pub-lag applied, for G10 currencies.
    cpi     : (T × N+1) CPI y/y %, optional (skip if None).
    ca_gdp  : (T × N) CA/GDP quarterly forward-filled, optional.
    ccys    : currency list (default G10).
    weights : factor weights (default hypothesis.md §3.3).

    Returns
    -------
    pd.DataFrame : (T × N) composite signal, higher = more attractive carry.
    """
    if ccys is None:
        ccys = G10_CCYS
    if weights is None:
        weights = DEFAULT_WEIGHTS

    usd_rate = rates["USD"]
    ccy_rates = rates[[c for c in ccys if c in rates.columns]]
    carry_raw = build_carry(ccy_rates, usd_rate)

    # Cross-sectional z-scores
    z_carry = _cs_zscore(carry_raw)
    signal = weights["carry"] * z_carry

    if reer is not None and not reer.empty:
        reer_sig = build_reer_signal(reer[[c for c in ccys if c in reer.columns]])
        z_reer   = _cs_zscore(reer_sig)
        # Align
        common_idx = z_carry.index.intersection(z_reer.index)
        signal.loc[common_idx] += weights["reer"] * z_reer.reindex(common_idx)

    if cpi is not None and not cpi.empty and "USD" in cpi.columns:
        infl_sig = build_inflation_signal(
            cpi[[c for c in ccys if c in cpi.columns]],
            cpi["USD"])
        z_infl = _cs_zscore(infl_sig)
        common_idx = z_carry.index.intersection(z_infl.index)
        signal.loc[common_idx] += weights["inflation"] * z_infl.reindex(common_idx)

    if ca_gdp is not None and not ca_gdp.empty:
        z_ca = _cs_zscore(ca_gdp[[c for c in ccys if c in ca_gdp.columns]])
        common_idx = z_carry.index.intersection(z_ca.index)
        signal.loc[common_idx] += weights["ca_gdp"] * z_ca.reindex(common_idx)

    return signal
