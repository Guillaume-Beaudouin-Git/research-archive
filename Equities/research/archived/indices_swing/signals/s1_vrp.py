"""
S1 — Variance Risk Premium signal.

Signal: VRP[T] = (IV[T]/100)² - RV21[T]
  where IV  = implied annualized vol (VIX for SPY/QQQ, VSTOXX for EWQ)
        RV21 = sum(daily_log_ret² over 21 days) × (252/21) — annualized realized variance

Temporal alignment (no look-ahead):
  VIX[T] observable at T close (15:15 CT)
  RV21[T] uses daily returns up to and including T close
  No shift applied here — signal is ready at T close

Asset→IV mapping:
  SPY, QQQ → VIX (CBOE, S&P 500 / NASDAQ proxy)
  EWQ       → VSTOXX (required; NaN if vstoxx_close not in U["vix"])

EWQ status (Sprint 1): VSTOXX not available on free platforms (yfinance 404, Stooq API-key
  required). vstoxx_close will be NaN → EWQ VRP returns NaN → excluded from ic_summary.
  Sprint 2: download vstoxx_manual.csv from STOXX.com.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

RV_WINDOW = 21   # trading days for realized variance computation


def compute_s1_vrp(U: dict[str, Any]) -> pd.DataFrame:
    """
    Compute daily VRP for each asset.

    Parameters
    ----------
    U : universe dict from load_universe()

    Returns
    -------
    pd.DataFrame
        Index   : trading-day DatetimeIndex
        Columns : [SPY, QQQ, EWQ]  (EWQ NaN if vstoxx_close unavailable)
    """
    prices  = U["prices"]
    vix_df  = U["vix"]

    vix    = vix_df["vix_close"] / 100.0       # convert to decimal annualized vol
    iv_sq  = vix ** 2                            # annualized implied variance

    vstoxx: pd.Series | None = None
    if "vstoxx_close" in vix_df.columns and vix_df["vstoxx_close"].notna().sum() > 0:
        vstoxx    = vix_df["vstoxx_close"] / 100.0
        vstoxx_sq = vstoxx ** 2
        log.info("S1 VRP: VSTOXX available (%d non-NaN) — EWQ will use VSTOXX",
                 vstoxx.notna().sum())
    else:
        log.warning(
            "S1 VRP: VSTOXX not available — EWQ VRP will be NaN. "
            "Sprint 2: add vstoxx_manual.csv to data/ for EWQ VRP."
        )

    asset_iv = {
        "SPY": iv_sq,
        "QQQ": iv_sq,
        "EWQ": vstoxx_sq if vstoxx is not None else None,
    }

    results: dict[str, pd.Series] = {}
    for ticker, iv_series in asset_iv.items():
        if (ticker, "close") not in prices.columns:
            log.warning("S1 VRP: ticker %s not in prices — skipping", ticker)
            continue

        if iv_series is None:
            results[ticker] = pd.Series(np.nan, index=prices.index, name=ticker)
            continue

        log_ret = prices[(ticker, "log_ret")]
        # Annualized realized variance from trailing 21d window
        # RV21 = mean(daily_ret²) × 252  (= annualized variance estimate)
        rv21 = log_ret.pow(2).rolling(RV_WINDOW, min_periods=RV_WINDOW // 2).mean() * 252

        vrp = iv_series - rv21
        vrp.name = ticker
        results[ticker] = vrp

    out = pd.DataFrame(results)
    out.index.name = None

    non_nan = {t: out[t].notna().sum() for t in out.columns}
    log.info("S1 VRP non-NaN counts: %s", non_nan)
    return out
