"""
Unified data loaders for the feasibility pipeline.
Wraps cached parquet (crypto 8h OHLCV + funding), Binance klines, and NQ 1-min CSV
via the project's existing data/cache.py infrastructure.

Network policy (2026-07)
------------------------
The feasibility routine runs inside the Anthropic cloud sandbox, which blocks
yfinance AND Binance (403 via proxy). ``load_strategy_a_universe`` therefore
reads a **local parquet cache** built on the VPS (see ``build_price_cache.py``)
instead of hitting the network live. A live fetch is only attempted when the
cache is missing or stale, and a *data* failure is never allowed to masquerade
as a *strategy* failure: if no cache exists and the live fetch is blocked, we
raise :class:`PriceDataUnavailable` (never return an empty DataFrame).
"""
from __future__ import annotations

import logging
import os
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Price cache configuration ───────────────────────────────────────────────────
CACHE_DIR: Path = Path(__file__).parent / "cache"
CACHE_PATH: Path = CACHE_DIR / "strategy_a_universe.parquet"
CACHE_MAX_AGE_DAYS: int = 14
_CACHED_AT_KEY: bytes = b"_cached_at"


class PriceDataUnavailable(RuntimeError):
    """
    Raised when no price cache exists AND a live fetch is impossible.

    This is deliberately distinct from a strategy-level failure: a caller (the
    orchestrator) that sees this must record DATA_UNAVAILABLE, NOT FAIL_A — an
    absence of data must never be counted as a tested hypothesis (n_tests is the
    DSR denominator and must stay exact).
    """

# Minimum listing dates to discard pre-launch garbage from yfinance
# (same as strategies/tsmom_v2_propfirm/config.py MIN_LISTING_DATES)
_MIN_LISTING_DATES: dict[str, str] = {
    "SOL-USD": "2020-04-10",
    "AVAX-USD": "2020-07-13",
    "DOT-USD": "2020-08-19",
    "UNI-USD": "2020-09-17",
    "MATIC-USD": "2019-04-01",
    "OP-USD": "2022-05-31",
    "ARB-USD": "2023-03-23",
}

# Full Strategy A universe (from config.py)
STRATEGY_A_FULL_UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD",
    "AVAX-USD", "LINK-USD", "DOGE-USD", "ADA-USD",
    "DOT-USD", "UNI-USD", "LTC-USD", "BCH-USD",
    "MATIC-USD", "OP-USD", "ARB-USD",
]

STRATEGY_A_CORE: list[str] = ["BTC-USD", "ETH-USD", "SOL-USD"]

STRATEGY_A_ADJACENT: list[str] = [
    "ADA-USD", "AVAX-USD", "DOT-USD", "LINK-USD", "MATIC-USD"
]


# ── Cache read/write helpers ────────────────────────────────────────────────────

def _write_cache(
    df: pd.DataFrame, path: Path, cached_at: datetime | None = None
) -> datetime:
    """
    Persist ``df`` to ``path`` with an embedded ``_cached_at`` timestamp.

    Prefers pyarrow schema metadata (portable, engine-independent); falls back to
    a plain ``to_parquet`` (freshness then relies on the file mtime).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    cached_at = cached_at or datetime.now(timezone.utc)
    iso = cached_at.isoformat()
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.Table.from_pandas(df)
        meta = dict(table.schema.metadata or {})
        meta[_CACHED_AT_KEY] = iso.encode()
        table = table.replace_schema_metadata(meta)
        pq.write_table(table, path)
    except Exception:
        # No pyarrow (or write failed) → plain parquet; mtime carries freshness.
        df.to_parquet(path)
    return cached_at


def _read_cached_at(path: Path) -> datetime | None:
    """Return the cache timestamp: embedded ``_cached_at`` if present, else mtime."""
    try:
        import pyarrow.parquet as pq

        meta = pq.read_schema(path).metadata or {}
        raw = meta.get(_CACHED_AT_KEY)
        if raw:
            ts = datetime.fromisoformat(raw.decode())
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
    except Exception:
        pass
    try:
        return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    except OSError:
        return None


def _slice_universe(
    df: pd.DataFrame, start: str, end: str, tickers: list[str]
) -> pd.DataFrame:
    """Restrict a cached full-universe frame to the requested window and tickers."""
    idx = df.index
    mask = (idx >= pd.Timestamp(start)) & (idx <= pd.Timestamp(end))
    out = df.loc[mask]
    cols = [t for t in tickers if t in out.columns]
    if not cols:
        return out.iloc[:, :0]
    return out[cols].dropna(how="all")


def load_strategy_a_universe(
    start: str = "2018-01-01",
    end: str = "2025-12-31",
    tickers: list[str] | None = None,
    *,
    force_live: bool = False,
    cache_path: Path | str | None = None,
) -> pd.DataFrame:
    """
    Load Strategy A universe prices, preferring a local parquet cache over the network.

    Resolution order (default, ``force_live=False``):
      1. If the cache exists AND is < ``CACHE_MAX_AGE_DAYS`` days old → read cache.
      2. Otherwise attempt a live yfinance fetch:
         - success → refresh the cache (rewrite parquet + timestamp) then return;
         - failure with an existing (stale) cache → log a WARNING and return the
           stale cache;
         - failure with NO cache → raise :class:`PriceDataUnavailable` (never an
           empty DataFrame — a data failure must not be confused with FAIL_A).

    Parameters
    ----------
    start, end : str
        ISO date bounds (defaults '2018-01-01' → '2025-12-31').
    tickers : list[str] or None
        Explicit yfinance tickers. If None, the full 14-asset Strategy A universe.
    force_live : bool
        Bypass the cache, fetch live, and rewrite the cache. Used by
        ``build_price_cache.py`` on the VPS (which has network access).
    cache_path : Path or str or None
        Override the cache location (defaults to ``CACHE_PATH``).

    Returns
    -------
    pd.DataFrame
        date × ticker DataFrame of daily Close prices, sorted by date.
    """
    if tickers is None:
        tickers = STRATEGY_A_FULL_UNIVERSE
    path = Path(cache_path) if cache_path is not None else CACHE_PATH
    now = datetime.now(timezone.utc)

    # ── Forced live refresh (VPS build) ─────────────────────────────────────────
    if force_live:
        df = _fetch_live_universe(start, end, tickers)
        _write_cache(df, path, now)
        return _slice_universe(df, start, end, tickers)

    cache_exists = path.exists()
    cached_at = _read_cached_at(path) if cache_exists else None

    # ── Fresh cache → use it ────────────────────────────────────────────────────
    if cache_exists and cached_at is not None:
        age = now - cached_at
        if age <= timedelta(days=CACHE_MAX_AGE_DAYS):
            return _slice_universe(pd.read_parquet(path), start, end, tickers)

    # ── Cache missing or stale → try live, degrade gracefully ───────────────────
    try:
        df = _fetch_live_universe(start, end, tickers)
        _write_cache(df, path, now)
        return _slice_universe(df, start, end, tickers)
    except Exception as exc:
        if cache_exists:
            stale_date = cached_at.date() if cached_at else "unknown"
            msg = (
                f"using stale cache from {stale_date}, live fetch failed: {exc}"
            )
            logger.warning(msg)
            warnings.warn(msg, RuntimeWarning, stacklevel=2)
            return _slice_universe(pd.read_parquet(path), start, end, tickers)
        raise PriceDataUnavailable(
            "no price cache and live fetch blocked — "
            "run build_price_cache.py on VPS first"
        ) from exc


def _fetch_live_universe(
    start: str,
    end: str,
    tickers: list[str],
) -> pd.DataFrame:
    """
    Fetch Strategy A universe prices live via yfinance (network required).

    Returns
    -------
    pd.DataFrame
        date × ticker DataFrame of daily Close prices, sorted by date.
        Columns with > 50% NaN in the leading rows are dropped (asset listed late).
        Rows with all-NaN are dropped.

    Raises
    ------
    ValueError
        If no data could be loaded for any ticker (e.g. sandbox 403). The caller
        translates this into cache fallback or :class:`PriceDataUnavailable`.
    """
    import yfinance as yf

    prices: dict[str, pd.Series] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for ticker in tickers:
            try:
                raw = yf.download(
                    ticker,
                    start=start,
                    end=end,
                    interval="1d",
                    auto_adjust=True,
                    progress=False,
                )
                if raw is None or raw.empty:
                    continue
                # Apply minimum listing date filter
                if ticker in _MIN_LISTING_DATES:
                    raw = raw.loc[raw.index >= pd.Timestamp(_MIN_LISTING_DATES[ticker])]
                if len(raw) < 30:
                    continue
                # Extract Close; yfinance may return MultiIndex columns
                if isinstance(raw.columns, pd.MultiIndex):
                    px = raw["Close"][ticker].squeeze()
                else:
                    px = raw["Close"].squeeze()
                px = px.dropna()
                if len(px) < 30:
                    continue
                # Clip extreme log-returns at ±1.0 (yfinance data quality)
                log_r = np.log(px / px.shift(1))
                extreme = int((log_r.abs() > 1.0).sum())
                if extreme > 0:
                    # Reconstruct price series from clipped log-returns
                    log_r_clipped = log_r.clip(-1.0, 1.0)
                    px = pd.Series(
                        np.exp(np.log(px.iloc[0]) + log_r_clipped.fillna(0).cumsum()),
                        index=px.index,
                    )
                prices[ticker] = px
            except Exception:
                continue

    if not prices:
        raise ValueError(f"No data loaded for tickers {tickers} ({start} → {end})")

    df = pd.DataFrame(prices).sort_index()

    # Keep an asset unless it has genuinely sparse data DURING ITS OWN LIVE PERIOD
    # (from its first valid observation onward). Late-listed assets (SOL 2020, ARB 2023,
    # …) carry leading NaNs that PREDATE their listing — that is expected, not missing
    # data, and is handled downstream by the rolling/shift signal (positions stay NaN
    # pre-listing, so skipna sums exclude the asset until it lists). Measuring %NaN from
    # the 2018 frame start would wrongly drop every asset that did not exist in 2018 —
    # the original bug that amputated the 14-asset universe down to 7 (SOL is CORE).
    keep_cols: list[str] = []
    for col in df.columns:
        s = df[col]
        first = s.first_valid_index()
        if first is None:
            continue  # no data at all
        live = s.loc[first:]
        if len(live) < 30:
            continue  # too short to be usable
        if live.isna().mean() > 0.5:
            continue  # > 50% NaN WITHIN its live span = real data-quality problem
        keep_cols.append(col)
    df = df[keep_cols]

    return df.dropna(how="all")


def split_universe(
    prices: pd.DataFrame,
    main_tickers: list[str],
    adjacent_tickers: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split a prices DataFrame into main and adjacent universes.

    Parameters
    ----------
    prices : pd.DataFrame
        Full date × ticker price DataFrame.
    main_tickers : list[str]
        Tickers that form the primary universe (must be present in prices.columns).
    adjacent_tickers : list[str] or None
        Tickers for the adjacent universe. If None, uses all columns not in main_tickers.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        (prices_main, prices_adjacent) — columns filtered and NaN-trimmed.
    """
    available = set(prices.columns)
    main_cols = [t for t in main_tickers if t in available]
    if not main_cols:
        raise ValueError(f"None of main_tickers {main_tickers} found in prices columns.")

    if adjacent_tickers is None:
        adj_cols = [c for c in prices.columns if c not in main_cols]
    else:
        adj_cols = [t for t in adjacent_tickers if t in available]

    prices_main = prices[main_cols].dropna(how="all")
    prices_adjacent = prices[adj_cols].dropna(how="all") if adj_cols else pd.DataFrame()

    return prices_main, prices_adjacent
