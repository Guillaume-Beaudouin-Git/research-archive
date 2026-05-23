"""
universe.py — Monthly universe for commodity futures cross-section research.

OUTPUT CONTRACT (U = load_universe())
────────────────────────────────────────────────────────────────────────────────

U["prices_daily"]  pd.DataFrame
    Index   : DatetimeIndex (daily, tz-naive)
    Columns : MultiIndex [(ticker, field)] where field ∈ {close, open, high, low, volume}
    Notes   : raw continuous spliced prices (NOT back-adjusted); roll artifacts visible

U["prices_monthly"]  pd.DataFrame
    Index   : DatetimeIndex (month-end, tz-naive)
    Columns : MultiIndex [(ticker, field)] where field ∈ {close, volume_60d_adv}
    Notes   : month-end resampled; volume_60d_adv = rolling 60d mean volume at month-end

U["active_universe"]  pd.DataFrame (boolean)
    Index   : month-end DatetimeIndex
    Columns : ticker codes
    Values  : True if ADV >= 5000 contracts/day in that month (tradeable)

U["fwd_ret"]  pd.DataFrame
    Index   : month-end DatetimeIndex T
    Columns : MultiIndex [(ticker, h)] where h ∈ {1, 3} (months)
    Definition:
        fwd_ret.loc[T, (ticker, 1)]
          = log(close[T+1m]) - log(close[T]) - rf[T] × 1/12
        Not vol-scaled at this stage (IC engine handles that).

U["basis_monthly"]  pd.DataFrame
    Index   : month-end DatetimeIndex
    Columns : ticker codes
    Values  : annualized roll-gap basis proxy (positive = backwardation)

U["rf"]  pd.Series
    Index   : month-end DatetimeIndex
    Values  : annual risk-free rate (DGS3MO / 100, decimal), e.g. 0.05 = 5% p.a.
    Notes   : monthly accrual = rf × 1/12

U["meta"]  dict
    Keys: date_start, date_end, tickers_all, tickers_active_pct,
          adv_threshold, n_months, last_updated

LOOK-AHEAD CHECKLIST
────────────────────────────────────────────────────────────────────────────────
✓ fwd_ret[T, h] uses close[T+h] / close[T]  (future data intentional as IC target)
✓ Signal computation uses data up to T-1 (enforced in signal modules)
✓ ADV filter uses rolling 60d volume up to T (month-end, no future data)
✓ Basis proxy at T uses rolls that occurred ≤ T (no future roll data)
✓ rf[T] = DGS3MO at month-end T (observable at T close)
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[5]
sys.path.insert(0, str(ROOT))

log = logging.getLogger(__name__)

ADV_THRESHOLD    = 5_000   # contracts/day minimum rolling 60d ADV
FWD_HORIZONS     = [1, 3]  # forecast horizons in months
DEFAULT_START    = "2005-01-01"
FFILL_LIMIT      = 3        # max days to forward-fill gaps in monthly data


def load_universe(
    start:         str        = DEFAULT_START,
    end:           str | None = None,
    adv_threshold: int        = ADV_THRESHOLD,
    max_age_days:  int        = 3,
    force_refresh: bool       = False,
) -> dict[str, Any]:
    """
    Load and consolidate daily commodity futures data into monthly universe.

    Parameters
    ----------
    start         : data start date (string YYYY-MM-DD)
    end           : data end date (default: today)
    adv_threshold : minimum 60d rolling ADV to include in cross-section
    max_age_days  : cache age limit for yfinance data
    force_refresh : bypass parquet cache

    Returns
    -------
    dict — see module docstring for full schema.
    """
    end_str = end or pd.Timestamp.today().strftime("%Y-%m-%d")

    # ── 1. Fetch daily OHLCV ──────────────────────────────────────────────────
    log.info("Fetching continuous futures (start=%s)…", start)
    from .fetch_continuous import fetch_all_continuous
    prices_daily = fetch_all_continuous(start=start, end=end_str, max_age_days=max_age_days)

    tickers_all = sorted({c[0] for c in prices_daily.columns})
    log.info("Universe: %d tickers, %d daily rows", len(tickers_all), len(prices_daily))

    # ── 2. Roll validation and basis proxy ────────────────────────────────────
    log.info("Running roll validation and building basis proxy…")
    from .roll_validation import validate_universe
    close_daily = prices_daily.xs("close", axis=1, level=1) if "close" in prices_daily.columns.get_level_values(1) else prices_daily.iloc[:, ::5]
    volume_daily = prices_daily.xs("volume", axis=1, level=1) if "volume" in prices_daily.columns.get_level_values(1) else None

    universe_stats = validate_universe(close_daily, volume_daily, adv_threshold)

    from .fetch_front_second import build_basis_monthly
    basis_monthly = build_basis_monthly(prices_daily)

    # ── 3. Risk-free rate (FRED DGS3MO) ──────────────────────────────────────
    log.info("Loading risk-free rate…")
    rf_daily = _load_rf(start, end_str)

    # ── 4. Resample to month-end ──────────────────────────────────────────────
    log.info("Resampling to month-end…")
    prices_monthly = _resample_monthly(prices_daily, volume_daily)
    rf_monthly     = rf_daily.resample("ME").last().ffill(limit=5)

    # ── 5. ADV filter (rolling 60d mean volume at month-end) ─────────────────
    if volume_daily is not None:
        adv_60d        = volume_daily.rolling(60, min_periods=30).mean()
        adv_monthly    = adv_60d.resample("ME").last()
        active_universe = adv_monthly >= adv_threshold
    else:
        # If volume unavailable, default to True (let downstream filter by hand)
        all_months  = prices_monthly.index
        active_universe = pd.DataFrame(
            True, index=all_months,
            columns=tickers_all,
        )
        log.warning("Volume data unavailable — ADV filter cannot be applied")

    # ── 6. Forward returns ────────────────────────────────────────────────────
    log.info("Computing forward returns…")
    close_monthly   = prices_monthly.xs("close", axis=1, level=1) if "close" in prices_monthly.columns.get_level_values(1) else prices_monthly
    fwd_ret         = _compute_fwd_ret_monthly(close_monthly, rf_monthly, FWD_HORIZONS)

    # ── 7. Align all series to common month-end index ─────────────────────────
    common_idx     = prices_monthly.index
    basis_monthly  = basis_monthly.reindex(common_idx)
    rf_monthly     = rf_monthly.reindex(common_idx).ffill(limit=5)
    active_universe = active_universe.reindex(common_idx).fillna(False)

    # ── 8. Meta ───────────────────────────────────────────────────────────────
    n_active_pct = active_universe.mean().mean() if not active_universe.empty else 0.0
    meta: dict[str, Any] = {
        "date_start":          str(common_idx[0].date()) if len(common_idx) > 0 else start,
        "date_end":            str(common_idx[-1].date()) if len(common_idx) > 0 else end_str,
        "tickers_all":         tickers_all,
        "n_tickers":           len(tickers_all),
        "n_months":            len(common_idx),
        "adv_threshold":       adv_threshold,
        "tickers_active_pct":  round(float(n_active_pct), 3),
        "universe_stats":      universe_stats,
        "last_updated":        datetime.now(timezone.utc).isoformat(),
    }

    log.info(
        "Universe ready: %d months  %s → %s  active_pct=%.1f%%",
        len(common_idx), meta["date_start"], meta["date_end"],
        n_active_pct * 100,
    )

    return {
        "prices_daily":    prices_daily,
        "prices_monthly":  prices_monthly,
        "close_monthly":   close_monthly,
        "active_universe": active_universe,
        "fwd_ret":         fwd_ret,
        "basis_monthly":   basis_monthly,
        "rf":              rf_monthly,
        "meta":            meta,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_rf(start: str, end: str) -> pd.Series:
    """Load DGS3MO from FRED (annual decimal rate)."""
    try:
        from data.cache import get_cached_or_fetch_http
        url = (
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS3MO"
            f"&vintage_date={end}"
        )
        raw = get_cached_or_fetch_http(url, "fred_DGS3MO_commodities", max_age_days=7)
        if isinstance(raw, pd.DataFrame) and not raw.empty:
            rf = raw.squeeze()
        else:
            rf = pd.Series(dtype=float)
    except Exception as exc:
        log.warning("_load_rf failed: %s — using FRED fallback", exc)
        rf = pd.Series(dtype=float)

    if rf.empty:
        # Absolute fallback: simple fixed rate
        log.warning("DGS3MO unavailable — rf set to 0 for all months")
        return pd.Series(
            0.0,
            index=pd.date_range(start, end, freq="ME"),
            name="rf",
        )

    rf.index = pd.to_datetime(rf.index).tz_localize(None).normalize()
    rf       = pd.to_numeric(rf, errors="coerce") / 100.0  # annual decimal
    rf       = rf[start:end].ffill(limit=10)
    return rf


def _resample_monthly(
    prices_daily:  pd.DataFrame,
    volume_daily:  pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Resample daily OHLCV to month-end.

    close, open, high, low → last business day of month (close price)
    volume → rolling 60d mean at month-end (ADV proxy)
    """
    frames: list[pd.Series] = []

    if isinstance(prices_daily.columns, pd.MultiIndex):
        tickers = sorted({c[0] for c in prices_daily.columns})
        for ticker in tickers:
            for field in ("close",):
                key = (ticker, field)
                if key in prices_daily.columns:
                    s = prices_daily[key].resample("ME").last()
                    s.name = key
                    frames.append(s)
            # Volume: 60d ADV at month-end
            vol_key = (ticker, "volume")
            if volume_daily is not None and ticker in volume_daily.columns:
                adv = volume_daily[ticker].rolling(60, min_periods=30).mean().resample("ME").last()
                adv.name = (ticker, "volume_60d_adv")
                frames.append(adv)
    else:
        for col in prices_daily.columns:
            s = prices_daily[col].resample("ME").last()
            s.name = (col, "close")
            frames.append(s)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, axis=1)
    out.columns = pd.MultiIndex.from_tuples(out.columns)
    return out.sort_index()


def _compute_fwd_ret_monthly(
    close_monthly: pd.DataFrame,
    rf_monthly:    pd.Series,
    horizons:      list[int],
) -> pd.DataFrame:
    """
    Monthly forward log-excess returns (NOT vol-scaled; IC engine applies XS rank).

    fwd_ret[T, h] = log(close[T+h]) - log(close[T]) - rf[T] × h/12

    The last h rows per horizon are NaN (no future price).
    """
    frames: list[pd.Series] = []

    for ticker in close_monthly.columns:
        close   = close_monthly[ticker]
        log_c   = np.log(close)

        for h in horizons:
            fwd_raw = log_c.shift(-h) - log_c         # future return at T (look-ahead: intended target)
            rf_h    = rf_monthly.reindex(close.index).ffill(limit=3) * h / 12
            fwd_exc = fwd_raw - rf_h

            s       = fwd_exc.copy()
            s.name  = (ticker, h)
            frames.append(s)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, axis=1)
    out.columns = pd.MultiIndex.from_tuples(out.columns)
    return out.sort_index()
