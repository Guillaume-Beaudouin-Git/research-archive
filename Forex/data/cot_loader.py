"""
Forex/data/cot_loader.py
========================
CFTC COT (Commitment of Traders) FX positioning data via ``cot_reports``.

Dependency: pip install cot_reports

Publication lag: T+3 (CFTC publishes Friday for Tuesday positions).
Rolling percentile: 3-year window (156 weeks).
Signal: 0 when percentile < 80th; reduce carry weight when > 80th (crowding risk).

Public API
----------
load_fx_cot(ccys, start, end) -> pd.DataFrame
    Weekly net speculative positions as 3Y rolling percentile (0-100).
    Publication lag already applied (shift = 3 days → weekly carries to next Friday).

Status: STUB — Phase 2 enhancement. Not used in Phase 1 IC feasibility.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# CME FX futures contract codes for COT data
# cot_reports uses CFTC-style market names
_COT_MARKET_NAMES: dict[str, str] = {
    "EUR": "EURO FX",
    "GBP": "BRITISH POUND",
    "JPY": "JAPANESE YEN",
    "CHF": "SWISS FRANC",
    "AUD": "AUSTRALIAN DOLLAR",
    "CAD": "CANADIAN DOLLAR",
    "NZD": "NEW ZEALAND DOLLAR",
    "MXN": "MEXICAN PESO",
    "BRL": "BRAZILIAN REAL",
}


def load_fx_cot(
    ccys: list[str] | None = None,
    start: str = "2010-01-01",
    end:   str = "2026-05-01",
    percentile_window_weeks: int = 156,
    max_age_days: float = 7.0,
) -> pd.DataFrame:
    """
    Weekly COT net speculative positioning as 3Y rolling percentile.

    Parameters
    ----------
    ccys                     : list of currency codes (default G10 subset with COT).
    start, end               : date range.
    percentile_window_weeks  : lookback for rolling percentile (default 156 = 3Y).
    max_age_days             : cache TTL.

    Returns
    -------
    pd.DataFrame
        Index  : DatetimeIndex, weekly (Friday).
        Columns: currency codes.
        Values : 0–100 (rolling percentile of net speculative position).
        NaN    : for first ``percentile_window_weeks`` rows.

    Notes
    -----
    Publication lag (T+3) is applied: CFTC releases data on Friday (COT report)
    for positions as of Tuesday. We shift by 3 days to align with week-end.
    Crowding signal: if percentile > 80 for a LONG carry currency, position is
    crowded — reduce carry weight by 50% (applied in signal.py, Phase 2).

    STATUS: PHASE 2 ENHANCEMENT — not used in Phase 1 IC feasibility.
    Install `cot_reports` to activate: pip install cot_reports
    """
    if ccys is None:
        ccys = list(_COT_MARKET_NAMES.keys())

    try:
        import cot_reports as cot
    except ImportError:
        log.warning("cot_reports not installed. COT data unavailable. Install: pip install cot_reports")
        return pd.DataFrame()

    pq = _CACHE_DIR / "fx_cot_percentile.parquet"
    meta = _CACHE_DIR / "fx_cot_percentile.json"

    if pq.exists() and meta.exists():
        import json
        from datetime import datetime, timezone
        with open(meta) as fh:
            m = json.load(fh)
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(m["created_at"])).total_seconds() / 86400
        if age <= max_age_days:
            log.info("COT cache hit (%.1f days old)", age)
            df = pd.read_parquet(pq)
            return df.loc[start:end, [c for c in ccys if c in df.columns]]

    log.info("Fetching COT data (this may take several minutes for full history)...")
    raw_frames = []
    for year in range(int(start[:4]), 2026):
        try:
            df_y = cot.cot_year(year, cot_report_type="legacy_fut_only")
            raw_frames.append(df_y)
        except Exception as exc:
            log.debug("COT year %d: %s", year, exc)

    if not raw_frames:
        log.warning("No COT data fetched.")
        return pd.DataFrame()

    raw = pd.concat(raw_frames, ignore_index=True)

    cols: dict[str, pd.Series] = {}
    for ccy, mkt_name in _COT_MARKET_NAMES.items():
        if ccy not in ccys:
            continue
        subset = raw[raw["Market and Exchange Names"].str.upper().str.contains(mkt_name.upper(), na=False)]
        if subset.empty:
            log.warning("No COT rows for %s (%s)", ccy, mkt_name)
            continue
        subset = subset.copy()
        subset["date"] = pd.to_datetime(subset["As of Date in Form YYYY-MM-DD"])
        subset = subset.sort_values("date").set_index("date")
        net = subset["Noncommercial Positions-Long (All)"] - subset["Noncommercial Positions-Short (All)"]
        net = net.resample("W-FRI").last().ffill(limit=4)
        # Shift T+3 (publication lag: CFTC releases Friday for Tuesday positions)
        net = net.shift(1)  # 1 week shift (weekly data; exact T+3 irrelevant at monthly freq)
        # Rolling percentile
        pct = net.rolling(percentile_window_weeks, min_periods=int(percentile_window_weeks * 0.8))
        pct_series = pct.apply(lambda x: 100.0 * (x[-1] > x[:-1]).mean() if len(x) > 1 else np.nan)
        cols[ccy] = pct_series

    if not cols:
        return pd.DataFrame()

    result = pd.DataFrame(cols).loc[start:end]
    result.to_parquet(pq)
    import json
    from datetime import datetime, timezone
    with open(meta, "w") as fh:
        json.dump({"created_at": datetime.now(timezone.utc).isoformat()}, fh)

    return result
