"""
Fetch VIX-related data for Sprint 1.

Sources
-------
vix_close    VIXCLS (FRED public API) — CBOE VIX daily settlement
vix9d_close  ^VIX9D (yfinance) — CBOE 9-day VIX, available 2011+
vx1, vx2     VIX front-month and 2nd-month futures — from local CSV (manual Sprint 1)
             Download from: https://www.cboe.com/us/futures/market_statistics/historical_data/
             Product: VX (CBOE Volatility Index Futures)
             Expected CSV columns: Trade Date, Open, High, Low, Close, Settle, ...
             Save as: Equities/research/active/indices_swing/data/vx_futures_manual.csv
vstoxx_close VSTOXX (STOXX.com manual download) — Euro Stoxx 50 implied vol index.
             VSTOXX is NOT available on yfinance (404) or Stooq (API key required).
             Download from: https://www.stoxx.com/indices-details.html#/DE000A0C4CA4
             Save as: Equities/research/active/indices_swing/data/vstoxx_manual.csv
             Sprint 2 item: required for EWQ VRP signal (S1).

Temporal alignment
------------------
VIX closes at 15:15 CT on the same day. Observable at T close, used for signals at T.
VX futures use the same settlement day.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

DEFAULT_START       = "2003-01-01"
VX_CSV_DEFAULT      = Path(__file__).parent / "vx_futures_manual.csv"
VSTOXX_CSV_DEFAULT  = Path(__file__).parent / "vstoxx_manual.csv"


def fetch_vix(
    start:           str         = DEFAULT_START,
    end:             str | None  = None,
    vx_csv_path:     Path | None = None,
    vstoxx_csv_path: Path | None = None,
    max_age_days:    float       = 1.0,
) -> pd.DataFrame:
    """
    Fetch VIX daily settlement, VIX9D, optionally VX futures, and optionally VSTOXX.

    Parameters
    ----------
    start            : 'YYYY-MM-DD'.
    end              : 'YYYY-MM-DD', defaults to today.
    vx_csv_path      : path to manually-downloaded VX futures CSV.
    vstoxx_csv_path  : path to manually-downloaded VSTOXX CSV (Sprint 2).
    max_age_days     : cache TTL for VIXCLS and VIX9D fetches.

    Returns
    -------
    pd.DataFrame
        Index   : DatetimeIndex (tz-naive), FRED calendar days (gaps = NaN).
        Columns :
            vix_close    — CBOE VIX daily settlement (VIXCLS from FRED)
            vix9d_close  — CBOE 9-day VIX (^VIX9D from yfinance, 2011+)
            vx1          — front-month VX futures settle (NaN if unavailable)
            vx2          — second-month VX futures settle (NaN if unavailable)
            vx_ratio     — vx1 / vx2 (NaN if futures unavailable)
            vx_backw     — bool, True when vx1 > vx2 (NaN if unavailable)
            vstoxx_close — VSTOXX daily close (NaN if manual CSV not provided)
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))
    from data.cache import get_cached_or_fetch_fred, get_cached_or_fetch

    end_str = end or pd.Timestamp.today().strftime("%Y-%m-%d")

    # ── VIXCLS from FRED ──────────────────────────────────────────────────────
    raw = get_cached_or_fetch_fred(
        series="VIXCLS",
        start=start,
        end=end_str,
        max_age_days=max_age_days,
    )
    df = raw.rename(columns={"vixcls": "vix_close"})

    # ── VIX9D from yfinance (2011+) ───────────────────────────────────────────
    try:
        vix9d_raw = get_cached_or_fetch(
            ticker="^VIX9D",
            start=start,
            end=end_str,
            interval="1d",
            max_age_days=max_age_days,
        )
        if not vix9d_raw.empty and ("^VIX9D", "close") in vix9d_raw.columns:
            df["vix9d_close"] = vix9d_raw[("^VIX9D", "close")].reindex(df.index)
        elif not vix9d_raw.empty and "close" in vix9d_raw.columns:
            df["vix9d_close"] = vix9d_raw["close"].reindex(df.index)
        else:
            df["vix9d_close"] = np.nan
            log.warning("VIX9D: could not parse column from yfinance response")
    except Exception as exc:
        df["vix9d_close"] = np.nan
        log.warning("VIX9D fetch failed: %s", exc)

    # ── VX futures from manual CSV ─────────────────────────────────────────────
    csv_path = Path(vx_csv_path) if vx_csv_path else VX_CSV_DEFAULT
    if csv_path.exists():
        vx = _parse_vx_csv(csv_path, start, end_str)
        df = df.join(vx, how="outer")
        log.info("VX futures loaded from %s (%d rows)", csv_path.name, len(vx))
    else:
        log.warning(
            "VX futures CSV not found at %s — vx1/vx2/vx_ratio/vx_backw will be NaN.\n"
            "Download from https://www.cboe.com/us/futures/market_statistics/historical_data/\n"
            "and save as %s",
            csv_path, csv_path,
        )
        df["vx1"]      = np.nan
        df["vx2"]      = np.nan
        df["vx_ratio"] = np.nan
        df["vx_backw"] = np.nan

    # ── VSTOXX from manual CSV (Sprint 2) ─────────────────────────────────────
    vstoxx_path = Path(vstoxx_csv_path) if vstoxx_csv_path else VSTOXX_CSV_DEFAULT
    if vstoxx_path.exists():
        vstoxx = _parse_vstoxx_csv(vstoxx_path, start, end_str)
        df["vstoxx_close"] = vstoxx.reindex(df.index)
        log.info("VSTOXX loaded from %s (%d non-NaN rows)", vstoxx_path.name,
                 df["vstoxx_close"].notna().sum())
    else:
        df["vstoxx_close"] = np.nan
        log.warning(
            "VSTOXX CSV not found at %s — vstoxx_close will be NaN.\n"
            "VSTOXX not available on yfinance or Stooq (requires API key).\n"
            "Sprint 2: download from STOXX.com and save as %s",
            vstoxx_path, vstoxx_path,
        )

    log.info(
        "fetch_vix: %d rows, %s → %s | vix9d non-NaN=%d",
        len(df),
        df.index[0].date() if len(df) else "?",
        df.index[-1].date() if len(df) else "?",
        df["vix9d_close"].notna().sum() if "vix9d_close" in df.columns else 0,
    )
    return df


def _parse_vx_csv(path: Path, start: str, end: str) -> pd.DataFrame:
    """
    Parse CBOE VX futures historical CSV into front-month / 2nd-month series.

    The CBOE provides separate CSVs per contract expiry. This function handles
    a consolidated CSV with a 'Trade Date' column and a 'Settle' column.
    If you have separate monthly files, concatenate them first and add a
    'month_offset' column (1 = front, 2 = second).

    For Sprint 1, if you have a single-contract CSV (front-month only),
    vx2 will remain NaN.
    """
    try:
        raw = pd.read_csv(path)
        raw.columns = [c.strip().lower() for c in raw.columns]

        # Accept both 'trade date' and 'date' column names
        date_col = next((c for c in raw.columns if "date" in c), None)
        if date_col is None:
            log.warning("VX CSV: no date column found, columns: %s", list(raw.columns))
            return pd.DataFrame()

        raw["_date"] = pd.to_datetime(raw[date_col], infer_datetime_format=True)
        raw = raw[(raw["_date"] >= pd.Timestamp(start)) & (raw["_date"] <= pd.Timestamp(end))]
        raw = raw.set_index("_date").sort_index()

        settle_col = next((c for c in raw.columns if "settle" in c), None)
        if settle_col is None:
            settle_col = next((c for c in raw.columns if "close" in c), None)

        out = pd.DataFrame(index=raw.index)
        if "month_offset" in raw.columns:
            front  = raw[raw["month_offset"] == 1][settle_col].rename("vx1")
            second = raw[raw["month_offset"] == 2][settle_col].rename("vx2")
            out    = pd.concat([front, second], axis=1)
        elif settle_col:
            out["vx1"] = raw[settle_col].astype(float)
            out["vx2"] = np.nan

        out["vx_ratio"] = out["vx1"] / out["vx2"] if "vx2" in out.columns else np.nan
        out["vx_backw"] = (out["vx1"] > out["vx2"]) if "vx2" in out.columns else np.nan
        return out

    except Exception as exc:
        log.warning("Failed to parse VX CSV %s: %s", path, exc)
        return pd.DataFrame()


def _parse_vstoxx_csv(path: Path, start: str, end: str) -> pd.Series:
    """
    Parse a VSTOXX manual CSV into a daily Series.

    Accepts any CSV with a date column and a numeric close/value column.
    The STOXX.com download typically has columns: Date, Open, High, Low, Close.
    """
    try:
        raw = pd.read_csv(path)
        raw.columns = [c.strip().lower() for c in raw.columns]
        date_col = next((c for c in raw.columns if "date" in c), None)
        val_col  = next((c for c in raw.columns if c in ("close", "settle", "value", "last")), None)
        if date_col is None or val_col is None:
            log.warning("VSTOXX CSV: could not find date/value columns in %s", list(raw.columns))
            return pd.Series(dtype=float)
        raw["_date"] = pd.to_datetime(raw[date_col], infer_datetime_format=True)
        raw = raw[(raw["_date"] >= pd.Timestamp(start)) & (raw["_date"] <= pd.Timestamp(end))]
        raw = raw.set_index("_date").sort_index()
        return raw[val_col].rename("vstoxx_close").astype(float)
    except Exception as exc:
        log.warning("Failed to parse VSTOXX CSV %s: %s", path, exc)
        return pd.Series(dtype=float)
