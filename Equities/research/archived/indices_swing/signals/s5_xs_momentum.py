"""
S5 — Cross-sectional momentum signal.

Universe: 6 ETFs — SPY, QQQ, EWQ, EWG, TLT, GLD
Lookback: 126 trading days (~6 months, Jegadeesh-Titman standard)
Signal:   cross-sectional rank of 6-month log return, scaled to [-1, +1]
          rank ∈ {1..6} → scaled = (rank - 3.5) / 2.5  → approx [-1, +1]

Temporal alignment:
  6m return uses close[T-126 : T] — purely past data, no look-ahead
  Rank computed across all 6 ETFs at each date T

IC test: IC measured for assets IN the test universe (SPY, QQQ, EWQ).
  EWG (Germany), TLT (Bonds), GLD (Gold) improve the cross-section quality
  but are not the primary research targets.

Note: N=6 is small for cross-sectional IC testing; IC will be noisy.
      AMTP not applied at IC scan stage.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

XS_UNIVERSE  = ["SPY", "QQQ", "EWQ", "EWG", "TLT", "GLD"]
MOM_LOOKBACK = 126   # trading days (~6 months)


def compute_s5_xs_momentum(U: dict[str, Any]) -> pd.DataFrame:
    """
    Compute cross-sectional momentum signal.

    Parameters
    ----------
    U : universe dict. Must contain prices for XS_UNIVERSE tickers.
        Missing tickers are fetched via yfinance using data.cache utilities.

    Returns
    -------
    pd.DataFrame — Index: trading days, Columns: [SPY, QQQ, EWQ, EWG, TLT, GLD]
        or subset if some tickers unavailable.
    """
    sys.path.insert(0, str(Path(__file__).parents[4]))

    prices = U["prices"]
    idx    = prices.index

    # Collect close prices for XS universe (fetch missing tickers on the fly)
    closes: dict[str, pd.Series] = {}
    for ticker in XS_UNIVERSE:
        if (ticker, "close") in prices.columns:
            closes[ticker] = prices[(ticker, "close")]
        else:
            # Fetch from yfinance (not in primary universe)
            try:
                from data.cache import get_cached_or_fetch
                start_str = str(idx[0].date())
                end_str   = str(idx[-1].date())
                extra = get_cached_or_fetch(
                    ticker, start_str, end_str, "1d", max_age_days=1
                )
                if not extra.empty:
                    col = (ticker, "close") if (ticker, "close") in extra.columns else "close"
                    s   = extra[col] if col in extra.columns else extra.iloc[:, 3]
                    closes[ticker] = s.reindex(idx).ffill(limit=3)
                    log.info("S5: fetched %s (%d non-NaN)", ticker, closes[ticker].notna().sum())
                else:
                    log.warning("S5: %s returned empty from yfinance — excluded", ticker)
            except Exception as exc:
                log.warning("S5: could not fetch %s: %s — excluded", ticker, exc)

    if len(closes) < 3:
        log.warning("S5: fewer than 3 tickers available — signal will be NaN")
        tickers_out = [t for t in ["SPY", "QQQ", "EWQ"] if t in closes or True]
        return pd.DataFrame({t: np.nan for t in tickers_out}, index=idx)

    close_df = pd.DataFrame(closes).reindex(idx)

    # 6-month log return for each ticker (no look-ahead)
    log_c    = np.log(close_df)
    mom_6m   = log_c - log_c.shift(MOM_LOOKBACK)    # log(P[T] / P[T-126])

    # Cross-sectional rank at each date (1 = lowest, N = highest)
    # Scale to approximately [-1, +1]
    n_assets  = len(closes)
    rank_df   = mom_6m.rank(axis=1, ascending=True)
    mid_rank  = (n_assets + 1) / 2
    scale     = (n_assets - 1) / 2
    signal_df = (rank_df - mid_rank) / scale   # range approx [-1, +1]

    # Return only columns that are either in the primary universe or were found
    out_cols = [t for t in ["SPY", "QQQ", "EWQ"] if t in signal_df.columns]
    # Also keep EWG, TLT, GLD for completeness (IC engine will filter per target)
    return signal_df
