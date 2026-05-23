"""
Fetch weekly and daily sentiment indicators.

Sources and publication-lag correction
----------------------------------------
AAII Sentiment Survey
  - Published: Thursday ~noon US Eastern (data covers the prior week's survey).
  - ready_date = publication_thursday + 1 business day (Friday).
  - URL: https://www.aaii.com/files/surveys/sentiment.xls (XLS download)

NAAIM Exposure Index
  - Published: Wednesday after market close.
  - ready_date = publication_wednesday + 1 business day (Thursday).
  - Source: NAAIM public CSV (URL may change; handled with fallback).

CBOE Put/Call Ratio (equity and total)
  - Published: same-day close (no lag).
  - ready_date = trade_date (observable at T close).
  - URLs: cdn.cboe.com/resources/options/volume_and_call_put_ratios/

Downstream usage
-----------------
All returned series are indexed on ready_date (the first day you can trade on
the information). Signal code MUST NOT apply an additional shift; the lag is
already baked in.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay

log = logging.getLogger(__name__)

_AAII_URL         = "https://www.aaii.com/files/surveys/sentiment.xls"   # Returns bot-intercept HTML
_NAAIM_PAGE_URL   = "https://www.naaim.org/programs/naaim-exposure-index/"  # Scrape for xlsx link
_PCR_EQUITY_URL   = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv"
_PCR_TOTAL_URL    = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/totalpc.csv"

# Manual-download fallbacks for blocked sources (403 Forbidden on automated fetch).
# AAII  : download from https://www.aaii.com/sentimentsurvey/sent_results
#          → save as: data/aaii_sentiment_manual.xls (or .csv)
# NAAIM : download from https://www.naaim.org/programs/naaim-exposure-index/
#          → save as: data/naaim_exposure_manual.csv
# CBOE PCR post-2019: CDN only covers 2006-2019; for recent data download from
#          https://www.cboe.com/data/historical-options-data/put-call-ratios/
#          → save as: data/cboe_pcr_equity_manual.csv / cboe_pcr_total_manual.csv
_MANUAL_DIR      = Path(__file__).parent
_AAII_MANUAL     = _MANUAL_DIR / "aaii_sentiment_manual.xls"
_NAAIM_MANUAL    = _MANUAL_DIR / "naaim_exposure_manual.csv"
_PCR_EQ_MANUAL   = _MANUAL_DIR / "cboe_pcr_equity_manual.csv"
_PCR_TOT_MANUAL  = _MANUAL_DIR / "cboe_pcr_total_manual.csv"

DEFAULT_START = "2003-01-01"


# ─── AAII ────────────────────────────────────────────────────────────────────

def _load_manual_csv_or_xls(path: Path, date_col_hint: str = "date") -> pd.DataFrame:
    """Read a manually-downloaded file (.xls, .xlsx, .csv) into a raw DataFrame."""
    suf = path.suffix.lower()
    if suf in (".xls",):
        return pd.read_excel(path, engine="xlrd")
    elif suf in (".xlsx",):
        return pd.read_excel(path, engine="openpyxl")
    else:
        return pd.read_csv(path)


def fetch_aaii(
    start:        str   = DEFAULT_START,
    max_age_days: float = 7.0,
) -> pd.Series:
    """
    Fetch AAII Bullish-Bearish sentiment spread (weekly).

    Returns
    -------
    pd.Series[float], name='aaii_bull_spread'
        Index : DatetimeIndex of ready_date (Thursday pub + 1BD = Friday).
                Forward-filled with limit=4 to daily (callers must reindex to
                trading-day calendar then ffill).
        Values: bull% - bear% (raw survey percentages, e.g. 0.38 - 0.27 = 0.11).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))
    from data.cache import get_cached_or_fetch_http

    def _parse_aaii(raw: bytes) -> pd.DataFrame:
        # The AAII XLS may be true Excel (.xls binary) or a renamed CSV.
        # Try Excel first, fall back to CSV.
        try:
            df = pd.read_excel(io.BytesIO(raw), header=None, engine="xlrd")
        except Exception:
            try:
                df = pd.read_excel(io.BytesIO(raw), header=None, engine="openpyxl")
            except Exception:
                df = pd.read_csv(io.BytesIO(raw), header=None)

        # Locate the header row: look for 'Bullish' or 'Bull' in any column
        header_row = None
        for i, row in df.iterrows():
            row_str = " ".join(str(v) for v in row.values).lower()
            if "bullish" in row_str and "bearish" in row_str:
                header_row = i
                break
        if header_row is None:
            raise ValueError("AAII: could not find header row with Bullish/Bearish")

        df.columns = [str(v).strip().lower() for v in df.iloc[header_row].values]
        df = df.iloc[header_row + 1:].reset_index(drop=True)

        # Identify date column
        date_col = next(
            (c for c in df.columns if any(x in c for x in ["date", "week", "reported"])), None
        )
        if date_col is None:
            date_col = df.columns[0]

        df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["_date"])

        bull_col = next((c for c in df.columns if "bull" in c and "bear" not in c), None)
        bear_col = next((c for c in df.columns if "bear" in c and "bull" not in c), None)
        if bull_col is None or bear_col is None:
            raise ValueError(f"AAII: bull/bear columns not found. Columns: {list(df.columns)}")

        df["bull"] = pd.to_numeric(df[bull_col], errors="coerce")
        df["bear"] = pd.to_numeric(df[bear_col], errors="coerce")

        # Normalise to decimal if values look like percentages (>1)
        if df["bull"].median() > 1:
            df["bull"] /= 100
            df["bear"] /= 100

        df["aaii_bull_spread"] = df["bull"] - df["bear"]
        df = df.set_index("_date")[["aaii_bull_spread"]].dropna()
        return df

    # Try manual file first (manual takes precedence; likely more complete)
    if _AAII_MANUAL.exists():
        try:
            raw_df = _load_manual_csv_or_xls(_AAII_MANUAL)
            df = _parse_aaii(raw_df.to_csv(index=False).encode())
            log.info("fetch_aaii: loaded from manual file %s", _AAII_MANUAL.name)
        except Exception as exc:
            log.warning("Manual AAII parse failed (%s), trying HTTP", exc)
            df = pd.DataFrame()
    else:
        df = get_cached_or_fetch_http(
            url=_AAII_URL,
            cache_key="aaii_sentiment",
            parser=_parse_aaii,
            max_age_days=max_age_days,
        )

    if df.empty:
        log.warning(
            "fetch_aaii: no data (HTTP 403 + no manual file). "
            "Download from https://www.aaii.com/sentimentsurvey/sent_results "
            "and save as %s",
            _AAII_MANUAL,
        )
        return pd.Series(dtype=float, name="aaii_bull_spread")

    series = df["aaii_bull_spread"].sort_index()
    # AAII is published Thursday; shift index to ready_date = next business day (Friday)
    series.index = series.index + BDay(1)
    series = series[series.index >= pd.Timestamp(start)]
    series.name = "aaii_bull_spread"
    log.info("fetch_aaii: %d weekly obs, %s → %s", len(series),
             series.index[0].date(), series.index[-1].date())
    return series


# ─── NAAIM ───────────────────────────────────────────────────────────────────

def _find_naaim_xlsx_url() -> str | None:
    """
    Scrape naaim.org to find the current weekly-updated Excel URL.

    NAAIM uploads a new xlsx each week, filename contains the pub date:
      https://naaim.org/wp-content/uploads/YYYY/MM/USE_Data-since-Inception_YYYY-MM-DD.xlsx
    We scrape the page to discover the current URL rather than hardcoding it.
    """
    import re
    import urllib.request as _req
    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    try:
        r    = _req.urlopen(_req.Request(_NAAIM_PAGE_URL, headers={"User-Agent": UA}), timeout=20)
        html = r.read().decode("utf-8", errors="replace")
        links = re.findall(r'href=["\']([^"\']*\.xlsx)["\']', html, re.IGNORECASE)
        links = [
            l if l.startswith("http") else "https://www.naaim.org" + l
            for l in links
        ]
        # Prefer links that contain "Data-since-Inception" or "Exposure"
        ranked = sorted(
            links,
            key=lambda l: ("since-inception" in l.lower() or "exposure" in l.lower()),
            reverse=True,
        )
        return ranked[0] if ranked else None
    except Exception as exc:
        log.warning("NAAIM page scrape failed: %s", exc)
        return None


def fetch_naaim(
    start:        str   = DEFAULT_START,
    max_age_days: float = 7.0,
) -> pd.Series:
    """
    Fetch NAAIM Exposure Index (weekly Wednesday, ready Thursday).

    Acquisition strategy:
      1. Manual file override: data/naaim_exposure_manual.csv (if present)
      2. Auto-scrape: scrapes naaim.org for the current weekly xlsx URL,
         then downloads and caches via data/cache.py.
         Full history from 2006-07-05 to present (~1 039 obs).

    Returns
    -------
    pd.Series[float], name='naaim_exposure'
        Index : DatetimeIndex of ready_date (Wednesday pub + 1BD = Thursday).
        Values: 'NAAIM Number' (composite weekly exposure, 0-200 range;
                100 = fully invested, 0 = flat, negative = net short).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))
    from data.cache import get_cached_or_fetch_http

    def _parse_naaim_xlsx(raw: bytes) -> pd.DataFrame:
        df = pd.read_excel(io.BytesIO(raw))
        df.columns = [str(c).strip().lower() for c in df.columns]
        dc = next((c for c in df.columns if "date" in c or "week" in c), df.columns[0])
        # "NAAIM Number" is the official headline figure
        exp_col = next(
            (c for c in df.columns if "naaim number" in c),
            next(
                (c for c in df.columns if any(x in c for x in ["mean", "average", "exposure"])),
                df.columns[1],
            ),
        )
        df["_date"] = pd.to_datetime(df[dc], errors="coerce")
        df = df.dropna(subset=["_date"])
        df["naaim_exposure"] = pd.to_numeric(df[exp_col], errors="coerce")
        return df.set_index("_date")[["naaim_exposure"]]

    df = pd.DataFrame()

    # Manual file override
    if _NAAIM_MANUAL.exists():
        try:
            raw_df = _load_manual_csv_or_xls(_NAAIM_MANUAL)
            df_tmp = pd.DataFrame()
            # Try naaim_xlsx parse if xls/xlsx, otherwise CSV fallback
            if _NAAIM_MANUAL.suffix.lower() in (".xls", ".xlsx"):
                df_tmp = _parse_naaim_xlsx(_NAAIM_MANUAL.read_bytes())
            else:
                raw_csv = _NAAIM_MANUAL.read_bytes()
                df_csv  = pd.read_csv(io.BytesIO(raw_csv))
                df_csv.columns = [str(c).strip().lower() for c in df_csv.columns]
                dc = next((c for c in df_csv.columns if "date" in c or "week" in c), df_csv.columns[0])
                exp_col = next((c for c in df_csv.columns if any(x in c for x in ["exposure","naaim","mean","average"])), df_csv.columns[1])
                df_csv["_date"] = pd.to_datetime(df_csv[dc], errors="coerce")
                df_csv = df_csv.dropna(subset=["_date"]).set_index("_date")
                df_csv["naaim_exposure"] = pd.to_numeric(df_csv[exp_col], errors="coerce")
                df_tmp = df_csv[["naaim_exposure"]]
            df = df_tmp
            log.info("fetch_naaim: loaded from manual file %s", _NAAIM_MANUAL.name)
        except Exception as exc:
            log.warning("Manual NAAIM parse failed (%s), trying auto-scrape", exc)

    # Auto-scrape from naaim.org
    if df.empty:
        xlsx_url = _find_naaim_xlsx_url()
        if xlsx_url:
            df = get_cached_or_fetch_http(
                url=xlsx_url,
                cache_key="naaim_exposure_xlsx",
                parser=_parse_naaim_xlsx,
                max_age_days=max_age_days,
            )
        if df.empty:
            log.warning(
                "fetch_naaim: auto-scrape found no usable data. "
                "Save manual file as %s.",
                _NAAIM_MANUAL,
            )
            return pd.Series(dtype=float, name="naaim_exposure")

    series = df["naaim_exposure"].dropna().sort_index()
    # NAAIM published Wednesday after close; ready Thursday
    series.index = series.index + BDay(1)
    series = series[series.index >= pd.Timestamp(start)]
    series.name = "naaim_exposure"
    log.info(
        "fetch_naaim: %d weekly obs, %s → %s",
        len(series), series.index[0].date(), series.index[-1].date(),
    )
    return series


# ─── CBOE PCR ─────────────────────────────────────────────────────────────────

def fetch_cboe_pcr(
    start:        str   = DEFAULT_START,
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Fetch CBOE daily put/call ratios (equity + total).

    Returns
    -------
    pd.DataFrame
        Index   : DatetimeIndex (tz-naive, trade date, ready same-day close).
        Columns : pcr_equity, pcr_total (float, ratio of puts to calls volume).
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parents[4]))
    from data.cache import get_cached_or_fetch_http

    def _parse_pcr(raw: bytes, col_name: str) -> pd.DataFrame:
        # CBOE PCR CSV has a 1-row disclaimer before the actual header.
        # Row 0: legal disclaimer text
        # Row 1: "DATE", "CALL VOLUME", "PUT VOLUME", "TOTAL VOLUME", "P/C Ratio"
        # Row 2+: data
        # Strategy: find the row that contains 'DATE' and use it as header.
        raw_text = io.BytesIO(raw)
        lines = raw.decode("utf-8", errors="replace").splitlines()
        skip = 0
        for i, line in enumerate(lines):
            if "DATE" in line.upper() and ("VOLUME" in line.upper() or "RATIO" in line.upper()):
                skip = i
                break
        df = pd.read_csv(io.BytesIO(raw), skiprows=skip)
        df.columns = [c.strip().lower() for c in df.columns]
        date_col = next((c for c in df.columns if "date" in c), df.columns[0])
        val_col  = next(
            (c for c in df.columns if "p/c" in c or "ratio" in c or "put/call" in c),
            df.columns[-1],
        )
        df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["_date"])
        df[col_name] = pd.to_numeric(df[val_col], errors="coerce")
        return df.set_index("_date")[[col_name]]

    def _load_pcr_manual(path: Path, col_name: str) -> pd.DataFrame:
        """Load manually-downloaded CBOE PCR CSV supplement."""
        if not path.exists():
            return pd.DataFrame()
        try:
            raw = path.read_bytes()
            return _parse_pcr(raw, col_name)
        except Exception as exc:
            log.warning("Manual PCR file %s parse failed: %s", path.name, exc)
            return pd.DataFrame()

    eq = get_cached_or_fetch_http(
        url=_PCR_EQUITY_URL,
        cache_key="cboe_pcr_equity",
        parser=lambda raw: _parse_pcr(raw, "pcr_equity"),
        max_age_days=max_age_days,
    )
    # Supplement with manual file if available (for post-2019 data)
    eq_manual = _load_pcr_manual(_PCR_EQ_MANUAL, "pcr_equity")
    if not eq_manual.empty:
        eq = pd.concat([eq, eq_manual]).sort_index()
        eq = eq[~eq.index.duplicated(keep="last")]

    tot = get_cached_or_fetch_http(
        url=_PCR_TOTAL_URL,
        cache_key="cboe_pcr_total",
        parser=lambda raw: _parse_pcr(raw, "pcr_total"),
        max_age_days=max_age_days,
    )
    tot_manual = _load_pcr_manual(_PCR_TOT_MANUAL, "pcr_total")
    if not tot_manual.empty:
        tot = pd.concat([tot, tot_manual]).sort_index()
        tot = tot[~tot.index.duplicated(keep="last")]

    frames = [f for f in [eq, tot] if not f.empty]
    if not frames:
        log.warning("fetch_cboe_pcr: both equity and total PCR returned empty")
        return pd.DataFrame(columns=["pcr_equity", "pcr_total"])

    df = pd.concat(frames, axis=1).sort_index()
    # Filter to requested start (PCR CDN only covers 2006-2019 regardless of start)
    mask = df.index >= pd.Timestamp(start)
    df = df.loc[mask]
    if df.empty:
        log.warning(
            "fetch_cboe_pcr: no data for start=%s — CBOE CDN covers 2006-11 to 2019-10 only. "
            "For post-2019 data, save cboe_pcr_equity_manual.csv / cboe_pcr_total_manual.csv.",
            start,
        )
        return pd.DataFrame(columns=["pcr_equity", "pcr_total"])
    log.info(
        "fetch_cboe_pcr: %d rows, %s → %s",
        len(df), df.index[0].date(), df.index[-1].date(),
    )
    return df


# ─── Consolidated ─────────────────────────────────────────────────────────────

def fetch_sentiment(
    start:              str   = DEFAULT_START,
    max_age_days_daily: float = 1.0,
    max_age_days_weekly:float = 7.0,
) -> pd.DataFrame:
    """
    Consolidated daily sentiment DataFrame, all series at ready_date.

    Returns
    -------
    pd.DataFrame
        Index   : DatetimeIndex (tz-naive), all dates (gaps present for missing data).
        Columns :
            aaii_bull_spread  — weekly, ready Friday (forward-filled from weekly obs)
            naaim_exposure    — weekly, ready Thursday (forward-filled)
            pcr_equity        — daily, ready same-day close (no fill needed)
            pcr_total         — daily, ready same-day close
            pcr_equity_10d    — 10-day SMA of pcr_equity (no look-ahead: rolling on past)
            pcr_total_10d     — 10-day SMA of pcr_total

    Notes
    -----
    - All publication lags are already applied. Signals must NOT add further shifts.
    - AAII and NAAIM are indexed to their ready_date and outer-joined; callers
      forward-fill to a common trading-day calendar (universe.py handles this).
    """
    aaii  = fetch_aaii(start=start, max_age_days=max_age_days_weekly)
    naaim = fetch_naaim(start=start, max_age_days=max_age_days_weekly)
    pcr   = fetch_cboe_pcr(start=start, max_age_days=max_age_days_daily)

    frames: list[pd.DataFrame] = []
    if not aaii.empty:
        frames.append(aaii.to_frame())
    if not naaim.empty:
        frames.append(naaim.to_frame())
    if not pcr.empty:
        # PCR 10-day rolling mean (no look-ahead: rolling uses only past obs)
        pcr["pcr_equity_10d"] = pcr["pcr_equity"].rolling(10, min_periods=5).mean()
        pcr["pcr_total_10d"]  = pcr["pcr_total"].rolling(10,  min_periods=5).mean()
        frames.append(pcr)

    if not frames:
        log.warning("fetch_sentiment: all sources empty — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.concat(frames, axis=1).sort_index()
    log.info(
        "fetch_sentiment: %d rows, cols=%s",
        len(df), list(df.columns),
    )
    return df
