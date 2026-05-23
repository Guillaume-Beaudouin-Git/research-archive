"""
Fetch macroeconomic series from FRED via pandas_datareader.

No API key required — uses the public FRED data endpoint.

Series fetched
--------------
hy_oas    BAMLH0A0HYM2   ICE BofA US High Yield OAS (basis points)
t10y2y    T10Y2Y         10Y minus 2Y Treasury spread (percentage points)
t10y3m    T10Y3M         10Y minus 3M Treasury spread (percentage points)
dxy       DTWEXBGS       Broad nominal USD index (goods & services, Mar 1973=100)
dgs3mo    DGS3MO         3-Month T-Bill secondary market rate (% p.a., ACT/360)

Temporal alignment
------------------
All FRED series report on the date the observation covers.
For daily series, this is the business day itself (observable at that day's close).
Weekend/holiday gaps are left as NaN in the raw output; callers forward-fill to
trading-day calendar with limit=3.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

FRED_SERIES: dict[str, str] = {
    "hy_oas": "BAMLH0A0HYM2",    # ICE BofA HY OAS — restricted on FRED public CDN, only ~3y history
    "t10y2y": "T10Y2Y",
    "t10y3m": "T10Y3M",
    "dxy":    "DTWEXBGS",
    "dgs3mo": "DGS3MO",
}

# HYG (iShares iBoxx HY Corporate ETF) as proxy for credit spread regime.
# Used by S6 when hy_oas history < 2010. Inverted sign: rising HYG = tightening spreads.
_HYG_TICKER = "HYG"

DEFAULT_START = "2003-01-01"


def fetch_macro(
    start:        str       = DEFAULT_START,
    end:          str | None = None,
    max_age_days: float      = 1.0,
) -> pd.DataFrame:
    """
    Fetch and cache FRED macro series.

    Parameters
    ----------
    start, end    : date range 'YYYY-MM-DD'.
    max_age_days  : cache TTL.

    Returns
    -------
    pd.DataFrame
        Index   : DatetimeIndex (tz-naive), calendar days (FRED native cadence).
                  Gaps (weekends / holidays) contain NaN — forward-fill downstream.
        Columns : hy_oas, t10y2y, t10y3m, dxy, dgs3mo (all float).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))
    from data.cache import get_cached_or_fetch_fred

    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))
    from data.cache import get_cached_or_fetch

    end_str = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    fred_df = get_cached_or_fetch_fred(
        series=list(FRED_SERIES.values()),
        start=start,
        end=end_str,
        max_age_days=max_age_days,
    )
    # Rename to friendly column names
    reverse = {v.lower(): k for k, v in FRED_SERIES.items()}
    fred_df = fred_df.rename(columns=reverse)
    fred_df = fred_df[[c for c in FRED_SERIES if c in fred_df.columns]]

    # ── HYG proxy for credit spread regime ───────────────────────────────────
    # HY OAS from FRED has restricted history (only ~3y). HYG provides full
    # history from 2007. S6 signal uses hyg_close (inversely correlated to OAS).
    hyg_raw = get_cached_or_fetch(
        ticker=_HYG_TICKER, start=start, end=end_str,
        interval="1d", source="yfinance", max_age_days=max_age_days,
    )
    if not hyg_raw.empty:
        hyg_raw.index = pd.to_datetime(hyg_raw.index).tz_localize(None)
        fred_df = fred_df.join(
            hyg_raw[["close"]].rename(columns={"close": "hyg_close"}),
            how="outer",
        )

    hy_cov = int(fred_df["hy_oas"].notna().sum())
    hyg_cov = int(fred_df.get("hyg_close", pd.Series(dtype=float)).notna().sum()) if "hyg_close" in fred_df else 0
    if hy_cov < 500:
        log.warning(
            "hy_oas (FRED BAMLH0A0HYM2) has only %d obs — restricted licensing. "
            "S6 will use hyg_close proxy (%d obs). Add FRED_API_KEY to .env for full series.",
            hy_cov, hyg_cov,
        )

    log.info(
        "fetch_macro: %d rows, %s → %s, obs_counts: %s",
        len(fred_df),
        fred_df.index[0].date() if len(fred_df) else "?",
        fred_df.index[-1].date() if len(fred_df) else "?",
        {c: int(fred_df[c].notna().sum()) for c in fred_df.columns},
    )
    return fred_df
