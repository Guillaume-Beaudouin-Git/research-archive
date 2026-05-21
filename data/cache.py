"""
data/cache.py  — local data cache layer
=========================================

First call: CSV → parquet + sidecar JSON metadata
Subsequent calls: parquet only (10-50× faster than CSV parse)

Public API
----------
    load_nq_1min(path=None) -> pd.DataFrame
        NQ 1-min Kaggle CSV, indexed by timestamp_et (tz-aware US/Eastern).
        Columns: open, high, low, close, volume, vwap_rth, vwap_eth

    get_cached_or_fetch(ticker, start, end, interval, source, max_age_days) -> pd.DataFrame
        Generic yfinance fetch with parquet cache.

    list_cache() -> pd.DataFrame
        Inventory table of all cached parquets.

    cache_stats() -> dict
        Summary: file count, total size, oldest/newest.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_ROOT = Path(__file__).parent               # Algo_claude/data/
_RAW  = _ROOT / "raw"
_META = _ROOT / "metadata"

_NQ_CSV_DEFAULT = _ROOT.parent / "Dataset_NQ_1min_2022_2025.csv"
_NQ_PARQUET     = _RAW / "NQ_1min_2022-12-26_2025-12-11.parquet"
_NQ_META        = _META / "NQ_1min_2022-12-26_2025-12-11.json"

# CSV column mapping: raw CSV header → normalized name
_NQ_COL_MAP = {
    "timestamp ET": "timestamp_et",
    "open":         "open",
    "high":         "high",
    "low":          "low",
    "close":        "close",
    "volume":       "volume",
    "Vwap_RTH":     "vwap_rth",
    "Vwap_ETH":     "vwap_eth",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_nq_1min(path: str = None) -> pd.DataFrame:
    """
    Load NQ 1-min OHLCV data with transparent parquet caching.

    First call: parses CSV, saves parquet + metadata sidecar.
    Subsequent calls: reads parquet directly (10-50× faster).

    Parameters
    ----------
    path : str, optional
        Absolute path to the Kaggle CSV. Defaults to
        Algo_claude/Dataset_NQ_1min_2022_2025.csv (sibling of data/).

    Returns
    -------
    pd.DataFrame
        Index   : timestamp_et (DatetimeTZDtype US/Eastern, minute freq)
        Columns : open, high, low, close (float, NQ points)
                  volume (int), vwap_rth (float), vwap_eth (float)

    Notes
    -----
    CSV column headers (exact): timestamp ET, open, high, low, close,
        volume, Vwap_RTH, Vwap_ETH
    CSV timestamp format: MM/DD/YYYY HH:MM (already in US/Eastern wall time)
    DST handling: ambiguous='infer' (monotonic 1-min series), nonexistent='shift_forward'
    """
    if _NQ_PARQUET.exists():
        log.info("Cache hit  → %s", _NQ_PARQUET.name)
        df = pd.read_parquet(_NQ_PARQUET, engine="pyarrow")
        return df

    csv_path = Path(path) if path else _NQ_CSV_DEFAULT
    log.info("Cache miss → parsing %s", csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"NQ CSV not found at: {csv_path}\n"
            "Pass the path explicitly: load_nq_1min(path='/absolute/path.csv')"
        )

    df = pd.read_csv(csv_path)

    # Validate expected columns
    missing = set(_NQ_COL_MAP.keys()) - set(df.columns)
    if missing:
        raise ValueError(
            f"Unexpected CSV columns. Missing: {missing}\n"
            f"Got: {list(df.columns)}"
        )

    # Rename
    df.rename(columns=_NQ_COL_MAP, inplace=True)

    # Parse timestamps — format MM/DD/YYYY HH:MM
    ts = pd.to_datetime(df["timestamp_et"], format="%m/%d/%Y %H:%M")
    ts_et = ts.dt.tz_localize(
        "US/Eastern",
        ambiguous="infer",
        nonexistent="shift_forward",
    )
    df["timestamp_et"] = ts_et
    df.set_index("timestamp_et", inplace=True)
    df.sort_index(inplace=True)

    # Cast types for storage efficiency
    for col in ("open", "high", "low", "close", "vwap_rth", "vwap_eth"):
        df[col] = df[col].astype("float32")
    df["volume"] = df["volume"].astype("int32")

    # Save parquet
    _RAW.mkdir(parents=True, exist_ok=True)
    df.to_parquet(_NQ_PARQUET, engine="pyarrow", compression="snappy")

    # Save metadata sidecar
    _META.mkdir(parents=True, exist_ok=True)
    meta = {
        "source":        str(csv_path),
        "rows":          len(df),
        "date_start":    df.index[0].isoformat(),
        "date_end":      df.index[-1].isoformat(),
        "columns":       list(df.columns),
        "dtypes":        {c: str(df[c].dtype) for c in df.columns},
        "created_at":    datetime.now(timezone.utc).isoformat(),
        "parquet_path":  str(_NQ_PARQUET),
        "size_bytes":    _NQ_PARQUET.stat().st_size,
        "size_mb":       round(_NQ_PARQUET.stat().st_size / 1e6, 2),
    }
    with open(_NQ_META, "w") as fh:
        json.dump(meta, fh, indent=2)

    log.info(
        "Saved → %s (%.1f MB, %d rows)",
        _NQ_PARQUET.name, meta["size_mb"], meta["rows"],
    )
    return df


def get_cached_or_fetch(
    ticker:       str,
    start:        str,
    end:          str,
    interval:     str   = "1d",
    source:       str   = "yfinance",
    max_age_days: float = 1.0,
) -> pd.DataFrame:
    """
    Generic cache for yfinance fetches. Keyed by (ticker, start, end, interval).

    Parameters
    ----------
    ticker, start, end, interval : yfinance-compatible args.
    source       : 'yfinance' only for now.
    max_age_days : Invalidate cache after this many days (default 1 day).

    Returns
    -------
    pd.DataFrame — same structure as yf.download() output with lowercased columns.
    Empty DataFrame if yfinance returns nothing.
    """
    key        = hashlib.md5(f"{ticker}|{start}|{end}|{interval}|{source}".encode()).hexdigest()[:10]
    pq_path    = _RAW  / f"yf_{ticker}_{interval}_{key}.parquet"
    meta_path  = _META / f"yf_{ticker}_{interval}_{key}.json"

    if pq_path.exists() and meta_path.exists():
        with open(meta_path) as fh:
            meta = json.load(fh)
        created = datetime.fromisoformat(meta["created_at"])
        age_d   = (datetime.now(timezone.utc) - created).total_seconds() / 86400
        if age_d <= max_age_days:
            log.info("Cache hit  → %s (age %.2fd)", pq_path.name, age_d)
            return pd.read_parquet(pq_path, engine="pyarrow")
        log.info("Cache stale (%.2fd > %.2fd) — refetching", age_d, max_age_days)

    if source != "yfinance":
        raise ValueError(f"Unsupported source: {source!r}. Only 'yfinance' is implemented.")

    import yfinance as yf
    df = yf.download(ticker, start=start, end=end, interval=interval,
                     auto_adjust=True, progress=False)
    if df.empty:
        log.warning("yfinance returned empty for %s", ticker)
        return df

    # Flatten MultiIndex columns if present, lowercase
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    _RAW.mkdir(parents=True, exist_ok=True)
    _META.mkdir(parents=True, exist_ok=True)
    df.to_parquet(pq_path, engine="pyarrow", compression="snappy")

    meta = {
        "ticker":       ticker, "start": start, "end": end,
        "interval":     interval, "source": source,
        "rows":         len(df),
        "date_start":   str(df.index[0]),
        "date_end":     str(df.index[-1]),
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "parquet_path": str(pq_path),
    }
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2)

    log.info("Fetched & cached → %s (%d rows)", pq_path.name, len(df))
    return df


def list_cache() -> pd.DataFrame:
    """
    Inventory of all cached parquets with key metadata.

    Returns
    -------
    pd.DataFrame with columns: name, rows, date_start, date_end, created_at, size_mb
    """
    records = []
    for meta_file in sorted(_META.glob("*.json")):
        try:
            with open(meta_file) as fh:
                m = json.load(fh)
            pq = Path(m.get("parquet_path", ""))
            records.append({
                "name":       meta_file.stem,
                "rows":       m.get("rows"),
                "date_start": m.get("date_start"),
                "date_end":   m.get("date_end"),
                "created_at": m.get("created_at"),
                "size_mb":    round(pq.stat().st_size / 1e6, 2) if pq.exists() else None,
            })
        except Exception as exc:
            log.warning("Could not read %s: %s", meta_file.name, exc)
    return pd.DataFrame(records)


def cache_stats() -> dict:
    """
    Summary stats for the cache directory.

    Returns
    -------
    dict with keys: file_count, total_size_mb, oldest, newest
    """
    parquets    = list(_RAW.glob("*.parquet"))
    total_bytes = sum(p.stat().st_size for p in parquets)
    metas       = []
    for m_path in _META.glob("*.json"):
        try:
            with open(m_path) as fh:
                m = json.load(fh)
            ts = m.get("created_at")
            if ts:
                metas.append(ts)
        except Exception:
            pass
    return {
        "file_count":    len(parquets),
        "total_size_mb": round(total_bytes / 1e6, 2),
        "oldest":        min(metas) if metas else None,
        "newest":        max(metas) if metas else None,
    }
