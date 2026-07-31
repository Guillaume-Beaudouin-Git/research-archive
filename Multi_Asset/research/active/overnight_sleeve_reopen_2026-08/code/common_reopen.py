"""Shared plumbing — overnight gold reopen sleeve, re-opened against FTMO barriers.

Read-only against the main working copy (caches are gitignored and therefore absent
from a fresh worktree). Nothing here fits, selects or optimises a window: the spec is
inherited verbatim from `overnight_futures_2026-07` (LONG at the Globex reopen
18:00 America/New_York, exit 8h later, settlement gap excluded by construction).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)

PRIOR = MAIN / "Multi_Asset" / "research" / "active" / "overnight_futures_2026-07"
M1_CACHE = PRIOR / "code" / "_m1cache" / "XAUUSD_m1.parquet"
H1_CACHE = MAIN / "yt_strategy_replications" / "data_cache" / "gold" / "XAUUSD_1h.parquet"
FTMO_M5 = MAIN / "data" / "ftmo_portfolio" / "cache" / "XAUUSD_m5_close.parquet"
PRIOR_SERIES = PRIOR / "results" / "step3_sleeve_series.csv"

REOPEN_ET = 18          # Globex reopen, exchange local clock
WINDOW_HOURS = 8        # inherited, never re-optimised

# ---- cost hypotheses (bps round-trip on notional) ---------------------------
# OLD : PropFirms/ftmo/program_2026-06/top10_test/framework.py:29 catalogue value
# MEAS: Multi_Asset/research/active/cost_denominator_2026-07/COST_AUDIT.md §3
COST_OLD_BPS = 3.50
COST_MEAS_BPS = 1.84

# ---- FTMO 2-step Standard (PropFirms/ftmo/rules.md:20-56) -------------------
FTMO_P1_TGT = 0.10
FTMO_P2_TGT = 0.05
FTMO_MAX_DD = 0.10      # static floor from initial balance (user-confirmed 2026-07-20)
FTMO_DAILY = 0.05       # equity-based, reset 00:00 Europe/Prague


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> pd.Timestamp:
    d = pd.Timestamp(year=year, month=month, day=1)
    off = (weekday - d.dayofweek) % 7
    return d + pd.Timedelta(days=off + 7 * (n - 1))


def us_dst(ts) -> np.ndarray:
    """True where US Eastern is on DST (2nd Sun Mar 02:00 -> 1st Sun Nov 02:00)."""
    ts = pd.DatetimeIndex(ts)
    out = np.zeros(len(ts), dtype=bool)
    for y in np.unique(ts.year):
        a = _nth_weekday(int(y), 3, 6, 2) + pd.Timedelta(hours=2)
        b = _nth_weekday(int(y), 11, 6, 1) + pd.Timedelta(hours=2)
        out |= (ts >= a) & (ts < b)
    return out


def eu_dst(ts) -> np.ndarray:
    """True where Europe/Prague is on CEST (last Sun Mar 01:00 UTC -> last Sun Oct 01:00 UTC)."""
    ts = pd.DatetimeIndex(ts)
    out = np.zeros(len(ts), dtype=bool)
    for y in np.unique(ts.year):
        mar = pd.Timestamp(year=int(y), month=3, day=31)
        mar -= pd.Timedelta(days=(mar.dayofweek + 1) % 7)
        oct_ = pd.Timestamp(year=int(y), month=10, day=31)
        oct_ -= pd.Timedelta(days=(oct_.dayofweek + 1) % 7)
        out |= (ts >= mar + pd.Timedelta(hours=1)) & (ts < oct_ + pd.Timedelta(hours=1))
    return out


def reopen_utc_hour(days: pd.DatetimeIndex) -> np.ndarray:
    """UTC hour of the 18:00 ET Globex reopen: 23 on US standard time, 22 on US DST."""
    return np.where(us_dst(days), 22, 23)


def load_m1() -> pd.DataFrame:
    d = pd.read_parquet(M1_CACHE)
    d = d.sort_values("ts").reset_index(drop=True)
    return d


def vol_target(win: pd.Series, lookback: int = 20, cap: float = 3.0) -> pd.Series:
    """Causal vol-target multiplier, identical to overnight_futures_2026-07/common.py.

    `rv` is shifted before the expanding median is taken, so every quantity entering
    the day-t multiplier is known at the close of day t-1 (signal at T-1, trade at T).
    """
    rv = win.rolling(lookback, min_periods=lookback).std().shift(1)
    target = rv.expanding(min_periods=lookback).median()
    return (target / rv).clip(upper=cap).fillna(0.0)


def obs_per_year(s: pd.Series) -> float:
    span = (s.index[-1] - s.index[0]).days / 365.25
    return len(s) / span if span > 0 else float("nan")


def sharpe(s: pd.Series) -> float:
    a = np.asarray(s, dtype=float)
    if a.size < 30 or a.std(ddof=1) == 0:
        return float("nan")
    return float(a.mean() / a.std(ddof=1) * np.sqrt(obs_per_year(s)))


def hac_t(s: pd.Series, lags: int = 6) -> tuple[float, float]:
    import statsmodels.api as sm
    a = np.asarray(s, dtype=float)
    m = sm.OLS(a, np.ones(len(a))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(m.params[0]), float(m.tvalues[0])
