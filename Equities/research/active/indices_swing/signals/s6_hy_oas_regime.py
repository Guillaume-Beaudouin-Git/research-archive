"""
S6 — HY OAS regime signal.

Mechanism: widening HY credit spreads predict equity drawdowns (credit → equity lead-lag).
Signal: 5-day change in HY OAS (sign inverted → widening = bearish = negative signal).

signal[T] = -(OAS[T] - OAS[T-5])   so:
  Spread widening  (OAS↑) → signal negative → bearish equity
  Spread tightening (OAS↓) → signal positive → bullish equity

Data sources (in priority order):
  1. BAMLH0A0HYM2 from macro — ICE licensing, only ~3y available (~2023+)
  2. HYG close price (yfinance) — available 2007+; spread proxy via inverted price change
     Signal from HYG: 5d log-return of HYG (price↑ = spreads tighter = bullish = positive)

Temporal alignment:
  OAS/HYG at T observable at market close T — no shift needed
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

DELTA_WINDOW = 5   # trading days for OAS change


def compute_s6_hy_oas(U: dict[str, Any]) -> pd.DataFrame:
    """
    Compute HY OAS regime signal for each asset (same signal applied to all tickers).

    Returns
    -------
    pd.DataFrame — Index: trading days, Columns: [SPY, QQQ, EWQ]
    """
    macro   = U["macro"]
    tickers = [t for t in ["SPY", "QQQ", "EWQ"] if (t, "close") in U["prices"].columns]

    # Primary: HYG price proxy (2007+, ~4800 obs) — longer history for IC power.
    # BAMLH0A0HYM2 (direct OAS) only has ~3y due to ICE licensing restriction on FRED;
    # too short for reliable IC testing (n≈780 → t-stat underpowered). Used as supplemental only.
    if "hyg_close" in macro.columns and macro["hyg_close"].notna().sum() > 500:
        hyg        = macro["hyg_close"]
        log_hyg    = np.log(hyg)
        signal_raw = log_hyg - log_hyg.shift(DELTA_WINDOW)   # 5d log-return of HYG
        source     = "HYG proxy (5d log-return, 2007+)"
        n_obs      = signal_raw.notna().sum()
    elif "hy_oas" in macro.columns and macro["hy_oas"].notna().sum() > 200:
        # Fallback to BAMLH0A0HYM2 if HYG not available
        oas_series = macro["hy_oas"]
        delta_oas  = oas_series.diff(DELTA_WINDOW)
        signal_raw = -delta_oas      # widening (positive Δ) → negative signal
        source     = "BAMLH0A0HYM2 (direct OAS, ~3y)"
        n_obs      = signal_raw.notna().sum()
    else:
        log.warning("S6: neither HYG nor BAMLH0A0HYM2 available — signal will be NaN")
        signal_raw = pd.Series(np.nan, index=macro.index)
        source     = "UNAVAILABLE"
        n_obs      = 0

    log.info("S6 HY OAS: using %s (%d non-NaN obs)", source, n_obs)

    out = pd.DataFrame({t: signal_raw for t in tickers}, index=macro.index)
    return out
