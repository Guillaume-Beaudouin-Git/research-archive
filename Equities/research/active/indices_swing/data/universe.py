"""
Universe consolidation for Equities/research/active/indices_swing Sprint 1.

─────────────────────────────────────────────────────────────────────────────
OUTPUT CONTRACT  (U = load_universe())
─────────────────────────────────────────────────────────────────────────────

U["prices"]     pd.DataFrame
    Index   : DatetimeIndex (tz-naive NYSE trading days, daily)
    Columns : MultiIndex [(ticker, field)] where
                ticker ∈ {SPY, QQQ, EWQ}
                field  ∈ {close, open, high, low, volume, log_ret}
    Notes   : close is split+dividend adjusted; log_ret = log(close).diff()

U["vix"]        pd.DataFrame
    Index   : same trading-day DatetimeIndex
    Columns : vix_close, vx1, vx2, vx_ratio, vx_backw
    Notes   : vx1/vx2/vx_ratio/vx_backw are NaN until VX CSV provided

U["sentiment"]  pd.DataFrame
    Index   : same trading-day DatetimeIndex
    Columns : aaii_bull_spread, naaim_exposure, pcr_equity, pcr_total,
              pcr_equity_10d, pcr_total_10d
    IMPORTANT: all series already shifted to ready_date (publication lag
               already applied in fetch_sentiment). Signal code MUST NOT
               shift these again.

U["macro"]      pd.DataFrame
    Index   : same trading-day DatetimeIndex
    Columns : hy_oas, t10y2y, t10y3m, dxy, dgs3mo

U["rf"]         pd.Series
    Index   : same trading-day DatetimeIndex
    Values  : annual risk-free rate (DGS3MO / 100, decimal), e.g. 0.05 = 5% p.a.
    Notes   : h-period accrual = rf[T] * h / 252  (applied inside _compute_fwd_ret)
              Signal code using rf directly should apply the same conversion.

U["fwd_ret"]    pd.DataFrame
    Index   : same trading-day DatetimeIndex
    Columns : MultiIndex [(ticker, horizon_d)] where
                ticker     ∈ {SPY, QQQ, EWQ}
                horizon_d  ∈ {1, 3, 5, 10}
    DEFINITION:
        fwd_ret.loc[T, (ticker, h)]
          = ( log(close[T+h]) - log(close[T]) - rf[T] * h/252 )
            / vol63[T]
        where rf[T]    = DGS3MO[T] / 100  (annual decimal, e.g. 0.05)
              rf*h/252  = h-period risk-free accrual
              vol63[T]  = rolling_63day_std(log_ret) at T (trailing, no look-ahead)

    LOOK-AHEAD CONTRACT:
        Row T contains the PREDICTION TARGET for a signal observed at close T.
        Signal functions return a Series indexed by signal_date (= observation date T).
        IC engine aligns signal_series with fwd_ret via shared index.
        No further shifting is needed in signal code IF the signal correctly
        represents information available at close T.

    EXAMPLE:
        On 2024-03-15 (T), you observe signal S=0.8 at market close.
        fwd_ret.loc["2024-03-15", ("SPY", 5)] = vol-scaled excess return
            from 2024-03-15 close → 2024-03-22 close  (5 trading days later)
        You enter at 2024-03-18 open (next day), exit 2024-03-22 close.
        The close-to-close approximation is standard for daily IC testing.

U["meta"]       dict
    Keys: date_start, date_end, tickers, horizons, vol_window, missing_pct,
          sources_loaded, last_updated

─────────────────────────────────────────────────────────────────────────────
LOOK-AHEAD CHECKLIST (implemented in this module)
─────────────────────────────────────────────────────────────────────────────
✓ fwd_ret uses log(close).shift(-h) - log(close)  (future price is at T+h, past is at T)
✓ vol63 uses rolling(63).std() on log_ret (trailing, no future data in window)
✓ rf_h accrual uses rf[T] (same-day, observable at T close)
✓ Sentiment series: publication lag pre-applied in fetch_sentiment()
✓ All data sourced from EOD values (no intraday look-ahead)
✓ fwd_ret terminal rows (last h obs) are NaN — not forward-filled (no fake future data)
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_HERE         = Path(__file__).parent
_PROJ_ROOT    = _HERE.parents[3]          # Algo_claude/
_CACHE_PARQUET = _HERE / "_universe_cache.parquet"
_CACHE_META    = _HERE / "_universe_cache_meta.json"

TICKERS       = ["SPY", "QQQ", "EWQ"]
HORIZONS      = [1, 3, 5, 10]
VOL_WINDOW    = 63      # trailing window for vol normalisation
FFILL_LIMIT   = 3       # max business days to forward-fill gaps
DEFAULT_START = "2003-01-01"


def load_universe(
    start:         str        = DEFAULT_START,
    end:           str | None = None,
    tickers:       list[str]  = TICKERS,
    horizons:      list[int]  = HORIZONS,
    vol_window:    int        = VOL_WINDOW,
    ffill_limit:   int        = FFILL_LIMIT,
    force_refresh: bool       = False,
    vx_csv_path:   Path | None = None,
) -> dict[str, Any]:
    """
    Load and align all data sources into a single universe dictionary.

    Parameters
    ----------
    start, end     : date range (trading days in this range are the index).
    tickers        : equity ETF tickers to include.
    horizons       : forward-return horizons in trading days.
    vol_window     : trailing window (days) for vol-scaling denominator.
    ffill_limit    : max days to forward-fill macro/sentiment gaps.
    force_refresh  : bypass the universe-level parquet cache.
    vx_csv_path    : override path to manually-downloaded VX futures CSV.

    Returns
    -------
    dict — see module docstring for full schema.
    """
    sys.path.insert(0, str(_PROJ_ROOT))

    end_str = end or pd.Timestamp.today().strftime("%Y-%m-%d")

    # ── 1. Build trading-day index (NYSE calendar) ────────────────────────────
    trading_days = pd.bdate_range(start=start, end=end_str, freq="C",
                                  holidays=_get_nyse_holidays(start, end_str))

    # ── 2. Prices ──────────────────────────────────────────────────────────────
    from .fetch_prices import fetch_prices
    prices_raw = fetch_prices(tickers=tickers, start=start, end=end_str)
    prices     = _reindex_to_calendar(prices_raw, trading_days, ffill_limit)
    # Add log returns per ticker
    log_rets: list[pd.Series] = []
    for ticker in tickers:
        if (ticker, "close") in prices.columns:
            lr = np.log(prices[(ticker, "close")]).diff()
            lr.name = (ticker, "log_ret")
            log_rets.append(lr)
    if log_rets:
        lr_df = pd.concat(log_rets, axis=1)
        lr_df.columns = pd.MultiIndex.from_tuples(lr_df.columns)
        prices = pd.concat([prices, lr_df], axis=1).sort_index(axis=1)

    # ── 3. VIX ─────────────────────────────────────────────────────────────────
    from .fetch_vix import fetch_vix
    vix = _reindex_to_calendar(
        fetch_vix(start=start, end=end_str, vx_csv_path=vx_csv_path),
        trading_days, ffill_limit,
    )

    # ── 4. Macro ───────────────────────────────────────────────────────────────
    from .fetch_macro import fetch_macro
    macro = _reindex_to_calendar(
        fetch_macro(start=start, end=end_str),
        trading_days, ffill_limit,
    )

    # ── 5. Risk-free rate (annual decimal) ────────────────────────────────────
    # rf = DGS3MO / 100  (e.g. 5.0 → 0.05 annual rate)
    # h-period accrual computed downstream: rf * h / 252
    # Do NOT divide by 252 here — _compute_fwd_ret already does that.
    if "dgs3mo" in macro.columns:
        rf = macro["dgs3mo"] / 100
    else:
        log.warning("DGS3MO not available — rf set to 0")
        rf = pd.Series(0.0, index=trading_days, name="rf")

    # ── 6. Sentiment ───────────────────────────────────────────────────────────
    from .fetch_sentiment import fetch_sentiment
    sentiment_raw = fetch_sentiment(start=start)
    sentiment = _reindex_to_calendar(sentiment_raw, trading_days, ffill_limit=5)
    # Weekly series (AAII, NAAIM) need more generous ffill than daily (up to ~5BD)

    # ── 7. Forward returns (vol-scaled excess) ─────────────────────────────────
    fwd_ret = _compute_fwd_ret(prices, rf, tickers, horizons, vol_window)

    # ── 8. Meta ────────────────────────────────────────────────────────────────
    def _missing_pct(df: pd.DataFrame) -> dict:
        if isinstance(df, pd.DataFrame):
            return {str(c): round(df[c].isna().mean() * 100, 1) for c in df.columns}
        return {}

    sources_loaded = []
    if not vix.empty:                  sources_loaded.append("vix")
    if not macro.empty:                sources_loaded.append("macro")
    if not sentiment.empty:            sources_loaded.append("sentiment")

    meta: dict[str, Any] = {
        "date_start":     str(trading_days[0].date()),
        "date_end":       str(trading_days[-1].date()),
        "n_trading_days": len(trading_days),
        "tickers":        tickers,
        "horizons":       horizons,
        "vol_window":     vol_window,
        "sources_loaded": sources_loaded,
        "missing_pct":    {
            "macro":     _missing_pct(macro),
            "sentiment": _missing_pct(sentiment),
            "vix":       _missing_pct(vix),
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    log.info(
        "Universe loaded: %d trading days, %d tickers, horizons=%s",
        len(trading_days), len(tickers), horizons,
    )

    return {
        "prices":    prices,
        "vix":       vix,
        "sentiment": sentiment,
        "macro":     macro,
        "rf":        rf,
        "fwd_ret":   fwd_ret,
        "meta":      meta,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_nyse_holidays(start: str, end: str) -> pd.DatetimeIndex:
    """Return approximate NYSE holidays. Uses pandas_market_calendars if available."""
    try:
        import pandas_market_calendars as mcal
        nyse = mcal.get_calendar("NYSE")
        schedule = nyse.schedule(start_date=start, end_date=end)
        all_days  = pd.bdate_range(start=start, end=end)
        valid     = pd.DatetimeIndex(schedule.index)
        return all_days.difference(valid)
    except ImportError:
        # Fallback: no holiday list (slightly off on 9 US market holidays/year)
        return pd.DatetimeIndex([])


def _reindex_to_calendar(
    df:         pd.DataFrame,
    trading_days: pd.DatetimeIndex,
    ffill_limit: int,
) -> pd.DataFrame:
    """
    Reindex df to trading_days with forward-fill up to ffill_limit.

    The df index is normalised to tz-naive dates before join.
    """
    if df is None or df.empty:
        return pd.DataFrame(index=trading_days)

    idx = pd.to_datetime(df.index).tz_localize(None).normalize()
    df  = df.copy()
    df.index = idx
    df = df[~df.index.duplicated(keep="last")]
    df = df.reindex(trading_days).ffill(limit=ffill_limit)
    return df


def _compute_fwd_ret(
    prices:     pd.DataFrame,
    rf:         pd.Series,
    tickers:    list[str],
    horizons:   list[int],
    vol_window: int,
) -> pd.DataFrame:
    """
    Compute vol-scaled excess forward log returns.

    fwd_ret.loc[T, (ticker, h)]
        = (log(close[T+h]) - log(close[T]) - rf[T] * h/252) / vol_ann[T]

    where vol_ann[T] = rolling(vol_window).std(log_ret) * sqrt(252).

    Last h rows of each (ticker, h) column are NaN (no future price available).
    This is intentional: do NOT forward-fill or interpolate terminal NaNs.
    """
    frames: list[pd.Series] = []

    for ticker in tickers:
        if (ticker, "close") not in prices.columns:
            log.warning("fwd_ret: ticker %s not in prices — skipping", ticker)
            continue

        close     = prices[(ticker, "close")]
        log_c     = np.log(close)
        log_ret   = log_c.diff()
        vol_ann   = log_ret.rolling(vol_window, min_periods=vol_window // 2).std() * np.sqrt(252)

        for h in horizons:
            # Raw log-return from close[T] to close[T+h] (both included)
            # shift(-h) brings future value back to index T
            fwd_raw    = log_c.shift(-h) - log_c           # look-ahead: intentional (target)
            rf_h       = rf * h / 252                       # h-period risk-free accrual
            fwd_excess = fwd_raw - rf_h                     # excess return
            fwd_scaled = fwd_excess / vol_ann               # vol-normalise

            s = fwd_scaled.copy()
            s.name = (ticker, h)
            frames.append(s)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, axis=1)
    out.columns = pd.MultiIndex.from_tuples(out.columns)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Quick smoke-test (run as __main__)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    U = load_universe(start="2015-01-01")

    print("\n=== UNIVERSE SUMMARY ===")
    print(f"Trading days : {U['meta']['n_trading_days']}")
    print(f"Date range   : {U['meta']['date_start']} → {U['meta']['date_end']}")
    print(f"Tickers      : {U['meta']['tickers']}")
    print(f"Horizons     : {U['meta']['horizons']}")

    print("\n--- prices (last 3 rows, close only) ---")
    close_cols = [(t, "close") for t in TICKERS if (t, "close") in U["prices"].columns]
    print(U["prices"][close_cols].tail(3).to_string())

    print("\n--- fwd_ret (last 5 rows) ---")
    print(U["fwd_ret"].tail(5).to_string())

    print("\n--- sentiment (last 5 rows) ---")
    print(U["sentiment"].tail(5).to_string())

    print("\n--- macro (last 3 rows) ---")
    print(U["macro"].tail(3).to_string())

    print("\n--- Missing data % ---")
    for grp, counts in U["meta"]["missing_pct"].items():
        print(f"  {grp}: {counts}")
