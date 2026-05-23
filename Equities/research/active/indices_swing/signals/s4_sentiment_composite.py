"""
S4 — Sentiment composite signal (Amendment 3: three parallel variants).

Three variants due to data coverage asymmetry:
  s4a_pcr_only    : standardized PCR10 (inverted) — 2006-11-01 to 2019-10-04
  s4b_naaim_only  : standardized NAAIM exposure (inverted) — 2006-07-05 to present
  s4c_composite   : z-score(NAAIM) + z-score(PCR10) on overlap window (2006-2019)

Contrarian direction (all variants):
  HIGH sentiment (bullish crowd) → signal NEGATIVE (expect mean reversion → drawdown)
  LOW  sentiment (bearish crowd) → signal POSITIVE (expect relief rally)
  → signal = -z_score(raw_sentiment)

Temporal alignment (no look-ahead):
  NAAIM: publication lag already applied in fetch_sentiment (Wednesday obs, Thursday ready)
  PCR:   same-day observable at market close (no lag needed)
  AAII:  DEFERRED to Sprint 2 (Akamai-blocked)

z-score window: rolling 252-day (1 year) to avoid distribution shift.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

Z_WINDOW = 252   # rolling z-score lookback


def compute_s4_variants(U: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Compute all three S4 sentiment variants.

    Returns
    -------
    dict with keys: 's4a_pcr_only', 's4b_naaim_only', 's4c_composite'
    Each value is a pd.DataFrame (trading days × [SPY, QQQ, EWQ]).
    """
    sent    = U["sentiment"]
    tickers = [t for t in ["SPY", "QQQ", "EWQ"] if (t, "close") in U["prices"].columns]

    results = {}

    # ── S4a: PCR-only (2006-2019) ─────────────────────────────────────────────
    pcr_col = "pcr_equity_10d"
    if pcr_col in sent.columns and sent[pcr_col].notna().sum() > 100:
        pcr_z  = _rolling_zscore(sent[pcr_col], Z_WINDOW)
        s4a_raw = -pcr_z        # inverted: high PCR (fear) → positive signal (contrarian)
        results["s4a_pcr_only"] = pd.DataFrame(
            {t: s4a_raw for t in tickers}, index=sent.index
        )
        log.info("S4a PCR-only: %d non-NaN obs (coverage: %s → %s)",
                 s4a_raw.notna().sum(),
                 sent[pcr_col].first_valid_index(),
                 sent[pcr_col].last_valid_index())
    else:
        log.warning("S4a: PCR equity 10d not available — variant will be NaN")
        results["s4a_pcr_only"] = pd.DataFrame(
            {t: np.nan for t in tickers}, index=sent.index
        )

    # ── S4b: NAAIM-only (2006-present) ────────────────────────────────────────
    naaim_col = "naaim_exposure"
    if naaim_col in sent.columns and sent[naaim_col].notna().sum() > 100:
        naaim_z  = _rolling_zscore(sent[naaim_col], Z_WINDOW)
        s4b_raw  = -naaim_z     # inverted: high NAAIM (high equity exposure) → bearish
        results["s4b_naaim_only"] = pd.DataFrame(
            {t: s4b_raw for t in tickers}, index=sent.index
        )
        log.info("S4b NAAIM-only: %d non-NaN obs (coverage: %s → %s)",
                 s4b_raw.notna().sum(),
                 sent[naaim_col].first_valid_index(),
                 sent[naaim_col].last_valid_index())
    else:
        log.warning("S4b: NAAIM exposure not available — variant will be NaN")
        results["s4b_naaim_only"] = pd.DataFrame(
            {t: np.nan for t in tickers}, index=sent.index
        )

    # ── S4c: Composite = NAAIM + PCR (overlap window 2006-2019) ──────────────
    if "s4a_pcr_only" in results and "s4b_naaim_only" in results:
        pcr_z_c   = _rolling_zscore(sent.get(pcr_col,  pd.Series(dtype=float)), Z_WINDOW)
        naaim_z_c = _rolling_zscore(sent.get(naaim_col, pd.Series(dtype=float)), Z_WINDOW)
        # Composite = mean of available z-scores, inverted (contrarian)
        composite = -(pcr_z_c + naaim_z_c) / 2.0
        # Restrict to overlap window (non-NaN in both)
        overlap_mask = sent.get(pcr_col, pd.Series(dtype=float)).notna() & \
                       sent.get(naaim_col, pd.Series(dtype=float)).notna()
        composite = composite.where(overlap_mask)
        results["s4c_composite"] = pd.DataFrame(
            {t: composite for t in tickers}, index=sent.index
        )
        log.info("S4c composite: %d non-NaN obs (overlap window)", composite.notna().sum())
    else:
        results["s4c_composite"] = pd.DataFrame(
            {t: np.nan for t in tickers}, index=sent.index
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────

def _rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    """Rolling z-score: (s - rolling_mean) / rolling_std over `window` days."""
    if s is None or s.empty:
        return pd.Series(dtype=float)
    mu  = s.rolling(window, min_periods=window // 2).mean()
    sig = s.rolling(window, min_periods=window // 2).std()
    return (s - mu) / sig.replace(0, np.nan)
