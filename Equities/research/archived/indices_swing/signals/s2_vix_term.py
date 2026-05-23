"""
S2 — VIX term structure signal.

Primary: VX1/VX2 ratio — front-month vs 2nd-month VIX futures (Sprint 2 only).
Fallback (Sprint 1): VIX9D / VIX ratio — 9-day vs 30-day expected vol.

Signal direction:
  Contango  (VIX9D < VIX, ratio < 1): normal regime, vol sellers earn carry → bullish
  Backwardation (VIX9D > VIX, ratio > 1): front-end elevated, stress → bearish

Signal = -(VIX9D/VIX)  so that contango (ratio < 1) → positive signal → bullish
OR equivalently: signal = 1 - VIX9D/VIX  (positive in contango)

Applied uniformly to SPY, QQQ, EWQ (VIX/VIX9D are US measures — EWQ is a proxy
application; European equivalent would require VSTOXX9D, unavailable on free platforms).

VIX9D availability: 2011-01-03 onwards (yfinance ^VIX9D). Pre-2011 rows are NaN.
VX fallback: if vx_ratio available in U["vix"], use -(vx_ratio) as primary.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def compute_s2_vix_term(U: dict[str, Any]) -> pd.DataFrame:
    """
    Compute VIX term structure signal for each asset.

    Returns
    -------
    pd.DataFrame — Index: trading days, Columns: [SPY, QQQ, EWQ]
    """
    vix_df = U["vix"]
    tickers = [t for t in ["SPY", "QQQ", "EWQ"] if (t, "close") in U["prices"].columns]

    # Primary: VX1/VX2 from manual CSV
    if "vx_ratio" in vix_df.columns and vix_df["vx_ratio"].notna().sum() > 50:
        raw_signal = -vix_df["vx_ratio"]
        source = "VX1/VX2 (futures)"
    # Fallback: VIX9D/VIX (2011+)
    elif "vix9d_close" in vix_df.columns and vix_df["vix9d_close"].notna().sum() > 50:
        raw_signal = 1.0 - (vix_df["vix9d_close"] / vix_df["vix_close"])
        source = "VIX9D/VIX (2011+)"
    else:
        log.warning("S2: neither VX futures nor VIX9D available — signal will be NaN")
        raw_signal = pd.Series(np.nan, index=vix_df.index)
        source = "UNAVAILABLE"

    log.info("S2 VIX term: using %s (%d non-NaN obs)", source, raw_signal.notna().sum())

    out = pd.DataFrame({t: raw_signal for t in tickers}, index=vix_df.index)
    return out
