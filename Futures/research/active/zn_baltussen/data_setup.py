"""
ZN intraday data loader + macro event calendar.

Data source hierarchy
---------------------
1. Local parquet (data/raw/ZN_1h_cache.parquet or ZN_1min_cache.parquet)
2. Local CSV    (data/raw/ZN_1min.csv — FirstRateData format, columns:
                 datetime,open,high,low,close,volume, datetime in ET)
3. yfinance 1h  (fallback, max ~730-day lookback; APPROXIMATION WARNING)

Run standalone:  python -m Futures.research.active.zn_baltussen.data_setup
Prints STOP-POINT 1 diagnostics.

ZN contract specs
-----------------
  Face value  : $100,000
  Point value : $1,000 / pt
  Tick size   : 1/64 pt = 0.015625 pt
  Tick value  : $15.625
  RTH session : 08:30-17:00 ET (CBOT), equity-hours signal: 09:30-17:00 ET
"""
from __future__ import annotations

import json
import logging
import os
import sys
from enum import Enum, auto
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── repo paths ────────────────────────────────────────────────────────────────
_REPO = Path(__file__).parents[4]
_DATA_RAW = _REPO / "data" / "raw"
_ZN_1H_PARQUET = _DATA_RAW / "ZN_1h_cache.parquet"
_ZN_1MIN_PARQUET = _DATA_RAW / "ZN_1min_cache.parquet"
_ZN_1MIN_CSV = _DATA_RAW / "ZN_1min.csv"

# ── ZN contract constants ─────────────────────────────────────────────────────
ZN_POINT_VALUE: float = 1_000.0
ZN_TICK_VALUE: float = 15.625
ZN_TICK_SIZE: float = 1.0 / 64.0  # points

# ── session timing (US/Eastern) ───────────────────────────────────────────────
SIGNAL_START_HOUR = 10   # proxy for 09:30 ET open using first full bar after open
SIGNAL_END_HOUR   = 15   # price at 15:00 ET
EXIT_HOUR         = 15   # bar covers 15:00-16:00; mid used as 15:30 proxy


class DataSource(Enum):
    LOCAL_1MIN = auto()
    LOCAL_1H   = auto()
    YFINANCE   = auto()
    UNAVAILABLE = auto()


# ── macro calendar ────────────────────────────────────────────────────────────

# FOMC statement release dates (14:00 ET), from Federal Reserve website
_FOMC_DATES: list[str] = [
    # 2018
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13",
    "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020 (includes 2 emergency unscheduled meetings Mar 3 and Mar 15)
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29",
    "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
]

# CPI release dates (08:30 ET), from BLS records
_CPI_DATES: list[str] = [
    "2018-01-12", "2018-02-14", "2018-03-13", "2018-04-11",
    "2018-05-10", "2018-06-12", "2018-07-12", "2018-08-10",
    "2018-09-13", "2018-10-11", "2018-11-14", "2018-12-12",
    "2019-01-11", "2019-02-13", "2019-03-12", "2019-04-10",
    "2019-05-10", "2019-06-12", "2019-07-11", "2019-08-13",
    "2019-09-12", "2019-10-10", "2019-11-13", "2019-12-11",
    "2020-01-14", "2020-02-13", "2020-03-11", "2020-04-10",
    "2020-05-12", "2020-06-10", "2020-07-14", "2020-08-12",
    "2020-09-11", "2020-10-13", "2020-11-12", "2020-12-10",
    "2021-01-13", "2021-02-10", "2021-03-10", "2021-04-13",
    "2021-05-12", "2021-06-10", "2021-07-13", "2021-08-11",
    "2021-09-14", "2021-10-13", "2021-11-10", "2021-12-10",
    "2022-01-12", "2022-02-10", "2022-03-10", "2022-04-12",
    "2022-05-11", "2022-06-10", "2022-07-13", "2022-08-10",
    "2022-09-13", "2022-10-13", "2022-11-10", "2022-12-13",
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12",
    "2023-05-10", "2023-06-13", "2023-07-12", "2023-08-10",
    "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10",
    "2024-05-15", "2024-06-12", "2024-07-11", "2024-08-14",
    "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10",
    "2025-05-13", "2025-06-11", "2025-07-11", "2025-08-13",
    "2025-09-10", "2025-10-15", "2025-11-13", "2025-12-10",
]

# PCE release dates (08:30 ET), from BEA records
_PCE_DATES: list[str] = [
    "2018-01-29", "2018-03-01", "2018-03-29", "2018-04-27",
    "2018-05-31", "2018-06-29", "2018-07-27", "2018-08-30",
    "2018-09-28", "2018-11-01", "2018-11-30", "2018-12-21",
    "2019-01-28", "2019-03-01", "2019-03-29", "2019-04-26",
    "2019-05-31", "2019-06-28", "2019-07-26", "2019-08-30",
    "2019-09-27", "2019-10-31", "2019-11-27", "2019-12-20",
    "2020-01-31", "2020-02-28", "2020-03-27", "2020-04-30",
    "2020-05-29", "2020-06-26", "2020-07-31", "2020-08-28",
    "2020-09-25", "2020-10-30", "2020-11-25", "2020-12-23",
    "2021-01-29", "2021-02-26", "2021-03-26", "2021-04-30",
    "2021-05-28", "2021-06-25", "2021-07-30", "2021-08-27",
    "2021-09-24", "2021-10-29", "2021-11-24", "2021-12-23",
    "2022-01-28", "2022-02-25", "2022-03-31", "2022-04-29",
    "2022-05-27", "2022-06-30", "2022-07-29", "2022-08-26",
    "2022-09-30", "2022-10-28", "2022-11-23", "2022-12-23",
    "2023-01-27", "2023-02-24", "2023-03-31", "2023-04-28",
    "2023-05-26", "2023-06-30", "2023-07-28", "2023-08-31",
    "2023-09-29", "2023-10-27", "2023-11-22", "2023-12-22",
    "2024-01-26", "2024-02-29", "2024-03-29", "2024-04-26",
    "2024-05-31", "2024-06-28", "2024-07-26", "2024-08-30",
    "2024-09-27", "2024-10-31", "2024-11-27", "2024-12-20",
    "2025-01-31", "2025-02-28", "2025-03-28", "2025-04-25",
    "2025-05-30", "2025-06-27", "2025-07-25", "2025-08-29",
    "2025-09-26", "2025-10-31", "2025-11-26", "2025-12-19",
]


def _nfp_dates(start_year: int, end_year: int) -> list[str]:
    """First Friday of each month — approximates NFP release (actual may differ by 1 week)."""
    out: list[str] = []
    for yr in range(start_year, end_year + 1):
        for mo in range(1, 13):
            d = pd.Timestamp(yr, mo, 1)
            while d.day_of_week != 4:   # 4 = Friday
                d += pd.Timedelta(days=1)
            out.append(d.strftime("%Y-%m-%d"))
    return out


def build_macro_calendar(start_year: int = 2018, end_year: int = 2025) -> pd.DataFrame:
    """
    Build a DataFrame of macro event days.

    Returns
    -------
    pd.DataFrame
        Columns: date (pd.Timestamp), event_type (str), is_fomc (bool),
                 is_nfp (bool), is_cpi (bool), is_pce (bool), is_event_day (bool)
    """
    fomc = pd.to_datetime(_FOMC_DATES)
    cpi  = pd.to_datetime(_CPI_DATES)
    pce  = pd.to_datetime(_PCE_DATES)
    nfp  = pd.to_datetime(_nfp_dates(start_year, end_year))

    all_dates = sorted(set(fomc) | set(cpi) | set(pce) | set(nfp))
    mask_start = pd.Timestamp(f"{start_year}-01-01")
    mask_end   = pd.Timestamp(f"{end_year}-12-31")
    all_dates  = [d for d in all_dates if mask_start <= d <= mask_end]

    rows = []
    for d in all_dates:
        rows.append({
            "date":         d.normalize(),
            "is_fomc":      d in fomc,
            "is_nfp":       d in nfp,
            "is_cpi":       d in cpi,
            "is_pce":       d in pce,
        })

    df = pd.DataFrame(rows)
    df["is_event_day"] = True
    # human-readable label
    def _label(r: pd.Series) -> str:
        parts = []
        if r["is_fomc"]: parts.append("FOMC")
        if r["is_nfp"]:  parts.append("NFP")
        if r["is_cpi"]:  parts.append("CPI")
        if r["is_pce"]:  parts.append("PCE")
        return "+".join(parts)
    df["event_type"] = df.apply(_label, axis=1)
    return df.sort_values("date").reset_index(drop=True)


# ── data loading ──────────────────────────────────────────────────────────────

def _detect_source() -> DataSource:
    if _ZN_1MIN_PARQUET.exists() or _ZN_1MIN_CSV.exists():
        return DataSource.LOCAL_1MIN
    if _ZN_1H_PARQUET.exists():
        return DataSource.LOCAL_1H
    try:
        import yfinance  # noqa: F401
        return DataSource.YFINANCE
    except ImportError:
        return DataSource.UNAVAILABLE


def _load_local_1min() -> pd.DataFrame:
    if _ZN_1MIN_PARQUET.exists():
        log.info("Loading ZN 1-min from parquet cache")
        return pd.read_parquet(_ZN_1MIN_PARQUET, engine="pyarrow")

    log.info("Parsing ZN 1-min CSV (first time, building parquet cache)")
    df = pd.read_csv(_ZN_1MIN_CSV)
    # Expected columns: datetime, open, high, low, close, volume
    df.columns = [c.lower().strip() for c in df.columns]
    dt_col = next(c for c in df.columns if "date" in c or "time" in c)
    df["ts_et"] = pd.to_datetime(df[dt_col]).dt.tz_localize(
        "America/New_York", ambiguous="infer", nonexistent="shift_forward"
    )
    df = df.set_index("ts_et").sort_index()
    _DATA_RAW.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_ZN_1MIN_PARQUET, engine="pyarrow", compression="snappy")
    log.info("Saved ZN 1-min parquet: %d bars", len(df))
    return df


def _load_yfinance_1h(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    log.info("Fetching ZN=F 1h from yfinance (%s → %s)", start, end)
    raw = yf.download("ZN=F", start=start, end=end, interval="1h",
                      auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError(
            f"yfinance returned empty for ZN=F 1h ({start}→{end}). "
            "The requested window may be outside the 730-day lookback limit."
        )
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0].lower() for c in raw.columns]
    else:
        raw.columns = [c.lower() for c in raw.columns]
    raw.index = raw.index.tz_convert("America/New_York")
    raw.index.name = "ts_et"
    _DATA_RAW.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(_ZN_1H_PARQUET, engine="pyarrow", compression="snappy")
    log.info("Cached ZN 1h parquet: %d bars", len(raw))
    return raw


def load_zn_intraday(
    start: str = "2024-07-01",
    end: str   = "2025-12-31",
) -> tuple[pd.DataFrame, DataSource]:
    """
    Load ZN intraday bars in US/Eastern timezone.

    Returns (df, source) where source indicates resolution/provenance.
    Caller must handle DataSource.UNAVAILABLE.
    """
    src = _detect_source()

    if src == DataSource.LOCAL_1MIN:
        df = _load_local_1min()
        start_ts = pd.Timestamp(start, tz="America/New_York")
        end_ts   = pd.Timestamp(end,   tz="America/New_York") + pd.Timedelta(days=1)
        return df.loc[start_ts:end_ts], src

    if src == DataSource.LOCAL_1H:
        df = pd.read_parquet(_ZN_1H_PARQUET, engine="pyarrow")
        start_ts = pd.Timestamp(start, tz="America/New_York")
        end_ts   = pd.Timestamp(end,   tz="America/New_York") + pd.Timedelta(days=1)
        return df.loc[start_ts:end_ts], src

    if src == DataSource.YFINANCE:
        if _ZN_1H_PARQUET.exists():
            df = pd.read_parquet(_ZN_1H_PARQUET, engine="pyarrow")
        else:
            df = _load_yfinance_1h(start, end)
        start_ts = pd.Timestamp(start, tz="America/New_York")
        end_ts   = pd.Timestamp(end,   tz="America/New_York") + pd.Timedelta(days=1)
        mask = (df.index >= start_ts) & (df.index <= end_ts)
        return df.loc[mask], src

    return pd.DataFrame(), DataSource.UNAVAILABLE


def load_vix(start: str, end: str) -> pd.Series:
    """Daily VIX close (^VIX from yfinance, cached)."""
    sys.path.insert(0, str(_REPO))
    try:
        from data.cache import get_cached_or_fetch
        df = get_cached_or_fetch("^VIX", start=start, end=end, interval="1d",
                                  max_age_days=1.0)
        if "close" in df.columns:
            return df["close"].rename("vix")
        if "Close" in df.columns:
            return df["Close"].rename("vix")
    except Exception as exc:
        log.warning("VIX fetch failed: %s — using zeros", exc)
    return pd.Series(dtype=float, name="vix")


# ── session feature extraction ─────────────────────────────────────────────────

def compute_session_features(
    df: pd.DataFrame,
    source: DataSource,
    calendar: Optional[pd.DataFrame] = None,
    vix: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """
    Build one row per trading day with Baltussen signal inputs.

    Columns returned
    ----------------
    date          : trading date (NY tz-naive date)
    p_open_proxy  : price proxy for 09:30 ET (open of 10:00 bar for 1h; exact for 1min)
    p_1500        : price at 15:00 ET
    p_exit_proxy  : price proxy for 15:30 ET exit
    return_rtd    : (p_1500 - p_open_proxy) / p_open_proxy
    direction     : +1 or -1 (signal)
    vix_close     : daily VIX close (for skip filter)
    is_event_day  : from macro calendar
    event_type    : FOMC/NFP/CPI/PCE label
    """
    tz = "America/New_York"
    df_et = df.copy()
    if df_et.index.tz is None:
        df_et.index = df_et.index.tz_localize(tz)
    else:
        df_et.index = df_et.index.tz_convert(tz)

    dates = pd.Series(df_et.index.normalize().unique()).sort_values()
    rows = []

    for d in dates:
        d_ts    = pd.Timestamp(d)
        d_start = d_ts.tz_convert(tz) if d_ts.tzinfo is not None else d_ts.tz_localize(tz)
        d_end   = d_start + pd.Timedelta(hours=23, minutes=59)
        day_df  = df_et.loc[d_start:d_end]
        if day_df.empty:
            continue

        if source == DataSource.LOCAL_1MIN:
            # Exact 1-min: get bar at 09:30 and 15:00
            t_0930 = d_start.replace(hour=9,  minute=30)
            t_1500 = d_start.replace(hour=15, minute=0)
            t_1530 = d_start.replace(hour=15, minute=30)
            bar_0930 = day_df.loc[t_0930:t_0930 + pd.Timedelta(minutes=1)]
            bar_1500 = day_df.loc[t_1500:t_1500 + pd.Timedelta(minutes=1)]
            bar_1530 = day_df.loc[t_1530:t_1530 + pd.Timedelta(minutes=1)]
            if bar_0930.empty or bar_1500.empty or bar_1530.empty:
                continue
            p_open  = float(bar_0930.iloc[0]["open"])
            p_1500  = float(bar_1500.iloc[0]["open"])
            p_exit  = float(bar_1530.iloc[0]["open"])
        else:
            # 1h approximation
            t_1000 = d_start.replace(hour=10, minute=0)
            t_1500 = d_start.replace(hour=15, minute=0)
            bar_1000 = day_df.loc[
                (day_df.index.hour == 10) & (day_df.index.minute == 0)
            ]
            bar_1500_df = day_df.loc[
                (day_df.index.hour == 15) & (day_df.index.minute == 0)
            ]
            if bar_1000.empty or bar_1500_df.empty:
                continue
            p_open = float(bar_1000.iloc[0]["open"])
            p_1500_bar = bar_1500_df.iloc[0]
            p_1500 = float(p_1500_bar["open"])
            # Exit proxy: midpoint of 15:00-16:00 bar
            p_exit = float((p_1500_bar["open"] + p_1500_bar["close"]) / 2.0)

        if p_open <= 0:
            continue
        return_rtd = (p_1500 - p_open) / p_open
        direction  = 1 if return_rtd > 0 else -1

        rows.append({
            "date":         d.date(),
            "p_open_proxy": p_open,
            "p_1500":       p_1500,
            "p_exit_proxy": p_exit,
            "return_rtd":   return_rtd,
            "direction":    direction,
        })

    sessions = pd.DataFrame(rows)
    if sessions.empty:
        return sessions
    sessions["date"] = pd.to_datetime(sessions["date"])
    sessions = sessions.set_index("date").sort_index()

    # Attach VIX
    if vix is not None and not vix.empty:
        vix_idx = vix.index
        if hasattr(vix_idx, "tz") and vix_idx.tz is not None:
            vix_idx = vix_idx.tz_localize(None)
        vix_plain = vix.copy()
        vix_plain.index = vix_idx
        sessions["vix_close"] = vix_plain.reindex(sessions.index).ffill().fillna(0.0)
    else:
        sessions["vix_close"] = 0.0

    # Attach calendar
    if calendar is not None and not calendar.empty:
        cal = calendar.set_index("date")[["is_event_day", "event_type"]].copy()
        cal.index = pd.to_datetime(cal.index)
        sessions = sessions.join(cal, how="left")
        sessions["is_event_day"] = sessions["is_event_day"].fillna(False).astype(bool)
        sessions["event_type"]   = sessions["event_type"].fillna("none")
    else:
        sessions["is_event_day"] = False
        sessions["event_type"]   = "none"

    return sessions


# ── STOP-POINT 1: diagnostics ─────────────────────────────────────────────────

def diagnose(
    start: str = "2024-07-01",
    end:   str = "2025-12-31",
) -> None:
    """
    STOP-POINT 1 — Print data availability + calendar + return_rtd distribution.
    """
    sep = "─" * 60
    print(f"\n{'='*60}")
    print("  STOP-POINT 1 — ZN Baltussen Data Diagnostics")
    print(f"{'='*60}")

    # ── 1. Data availability ─────────────────────────────────────────────────
    src = _detect_source()
    print(f"\n[1] Data source detected: {src.name}")
    if src == DataSource.LOCAL_1MIN:
        print("    ✓ 1-min data available — full backtest 2018-2025 feasible")
    elif src in (DataSource.LOCAL_1H, DataSource.YFINANCE):
        print("    ⚠  1h approximate data — canary mode only")
        print(f"    Fetching {start} → {end} ...")
    else:
        print("    ✗ No data source available.")
        print("    Install options:")
        print("      · FirstRateData ZN 1-min (~$99) → save to data/raw/ZN_1min.csv")
        print("      · Databento: pip install databento + set DATABENTO_API_KEY")
        print(f"    yfinance: pip install yfinance (1h back ~730 days)")
        return

    df, src = load_zn_intraday(start=start, end=end)
    print(f"    Loaded: {len(df):,} bars")
    if len(df) == 0:
        print("    ✗ Empty DataFrame — data outside yfinance lookback window")
        print(f"      Adjust start date to within 730 days of today")
        return
    print(f"    Date range: {df.index[0].date()} → {df.index[-1].date()}")
    print(f"    Resolution: {'1-min' if src == DataSource.LOCAL_1MIN else '1h (approx)'}")

    # ── 2. Calendar stats ────────────────────────────────────────────────────
    cal = build_macro_calendar(
        start_year=int(start[:4]),
        end_year=int(end[:4]),
    )
    start_dt = pd.Timestamp(start)
    end_dt   = pd.Timestamp(end)
    cal_window = cal[(cal["date"] >= start_dt) & (cal["date"] <= end_dt)]

    print(f"\n[2] Macro calendar ({start[:4]}–{end[:4]})")
    print(f"    Total event-days: {len(cal_window)}")
    for etype in ["FOMC", "NFP", "CPI", "PCE"]:
        col = f"is_{etype.lower()}"
        n = int(cal_window[col].sum())
        print(f"      {etype}: {n}")

    if not cal_window.empty:
        print(f"\n    Sample 2024 event-days (first 12):")
        yr_cal = cal_window[cal_window["date"].dt.year.isin([2024, 2025])]
        for _, row in yr_cal.head(12).iterrows():
            print(f"      {row['date'].date()}  {row['event_type']}")

    # ── 3. Session features ──────────────────────────────────────────────────
    vix_start = (pd.Timestamp(start) - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    vix = load_vix(vix_start, end)
    sessions = compute_session_features(df, src, calendar=cal_window, vix=vix)

    print(f"\n[3] Session features computed: {len(sessions)} trading days")
    if sessions.empty:
        print("    ✗ No sessions extracted — check data coverage")
        return

    rtd = sessions["return_rtd"]
    print(f"    return_rtd stats:")
    print(f"      mean  = {rtd.mean()*100:.3f}%")
    print(f"      std   = {rtd.std()*100:.3f}%")
    print(f"      min   = {rtd.min()*100:.3f}%")
    print(f"      max   = {rtd.max()*100:.3f}%")
    print(f"      >0 (long signal): {(rtd > 0).sum()} days ({(rtd>0).mean()*100:.1f}%)")
    print(f"      <0 (short signal): {(rtd < 0).sum()} days ({(rtd<0).mean()*100:.1f}%)")

    print(f"\n    VIX filter (VIX>25) would skip: {(sessions['vix_close']>25).sum()} days "
          f"({(sessions['vix_close']>25).mean()*100:.1f}%)")

    n_event = sessions["is_event_day"].sum()
    n_total = len(sessions)
    print(f"\n    Event-day sessions: {n_event}/{n_total} ({n_event/n_total*100:.1f}%)")
    if n_event > 0:
        ev = sessions[sessions["is_event_day"]]
        nev = sessions[~sessions["is_event_day"]]
        print(f"    return_rtd mean — event: {ev['return_rtd'].mean()*100:.3f}%  "
              f"non-event: {nev['return_rtd'].mean()*100:.3f}%")
        print(f"    return_rtd std  — event: {ev['return_rtd'].std()*100:.3f}%  "
              f"non-event: {nev['return_rtd'].std()*100:.3f}%")

    print(f"\n[4] Data resolution note:")
    if src != DataSource.LOCAL_1MIN:
        print("    ⚠  CANARY MODE (1h data)")
        print("    · p_open_proxy = Open(10:00 bar)  [proxy for 09:30]")
        print("    · p_1500       = Open(15:00 bar)  [exact hour boundary]")
        print("    · p_exit_proxy = midpoint(15:00-16:00 bar)  [proxy for 15:30]")
        print("    · SL intra-bar: approximated via bar High/Low")
        print("    · For full 2018-2025 backtest:")
        print("      → Buy ZN 1-min from FirstRateData (~$99)")
        print("        https://firstratedata.com/i/futures")
        print("      → Save CSV to: data/raw/ZN_1min.csv")
    else:
        print("    ✓ 1-min data — full precision signal")

    print(f"\n{'='*60}")
    print("  STOP-POINT 1 complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    diagnose()
