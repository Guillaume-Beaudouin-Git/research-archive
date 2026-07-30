"""Shared plumbing for the overnight-drift -> CME futures transfer study.

Read-only against the repo's canonical stores. Nothing here fits, selects or
optimises a window: the windows are inherited from the archived CFD studies.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "results"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "yt_strategy_replications"))

ACCOUNT_USD = 15_000.0          # EUR 13,000 x 1.1522
EURUSD = 1.1522

# ---------------------------------------------------------------- sleeve specs
# start_utc_winter: window start in UTC when US is on STANDARD time.
# exchange_tz_offset_winter: exchange local time = UTC + offset (CT = -6 winter).
# In US summer the exchange clock shifts +1h vs UTC, so an exchange-anchored
# window starts one UTC hour EARLIER.
SLEEVES = {
    "GOLD": dict(cfd="XAUUSD", fut="GC=F", micro="MGC", start_utc_winter=23, hours=8,
                 sample_start="2007-01-01"),
    "SILVER": dict(cfd="XAGUSD", fut="SI=F", micro="SIL", start_utc_winter=23, hours=8,
                   sample_start="2014-01-01"),   # regime patch, inherited from the report
    "WTI": dict(cfd="USOIL", fut="CL=F", micro="MCL", start_utc_winter=23, hours=8,
                sample_start="2013-01-01"),
    "SOYBEAN": dict(cfd="SOYBEAN", fut="ZS=F", micro="MZS", start_utc_winter=1, hours=6,
                    sample_start="2017-12-01"),
}

# --------------------------------------------------------------- contract specs
# size, tick_value_usd, overnight_margin_usd  (margins: emini-watch live table
# refreshed 2026-07-30 11:42 UTC; MZS from CME micro-ag specs)
CONTRACTS = {
    "MGC": dict(size=10, unit="oz", tick_val=1.00, margin=2308.0, px_col="GC"),
    "SIL": dict(size=1000, unit="oz", tick_val=5.00, margin=6469.0, px_col="SI"),
    "MCL": dict(size=100, unit="bbl", tick_val=1.00, margin=840.0, px_col="CL"),
    "MZS": dict(size=500, unit="bu", tick_val=0.625, margin=210.0, px_col="ZS"),
}
REF_PX = {"GC": 4070.90, "SI": 58.164, "CL": 73.52, "ZS": 1195.0, "PL": 1576.40}
NOTIONAL = {"MGC": 10 * REF_PX["GC"], "SIL": 1000 * REF_PX["SI"],
            "MCL": 100 * REF_PX["CL"], "MZS": 500 * REF_PX["ZS"] / 100.0}

COMMISSION_PER_SIDE = 0.85      # IBKR retail fixed, all-in
COMMISSION_TIERED = 0.50


# ------------------------------------------------------------------ US DST flag
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> pd.Timestamp:
    d = pd.Timestamp(year=year, month=month, day=1)
    offset = (weekday - d.dayofweek) % 7
    return d + pd.Timedelta(days=offset + 7 * (n - 1))


def us_dst(ts: pd.DatetimeIndex) -> np.ndarray:
    """True where US Eastern is on DST (2nd Sun Mar 02:00 -> 1st Sun Nov 02:00)."""
    ts = pd.DatetimeIndex(ts)
    out = np.zeros(len(ts), dtype=bool)
    for y in np.unique(ts.year):
        start = _nth_weekday(int(y), 3, 6, 2) + pd.Timedelta(hours=2)
        end = _nth_weekday(int(y), 11, 6, 1) + pd.Timedelta(hours=2)
        out |= (ts >= start) & (ts < end)
    return out


# ------------------------------------------------------------------- H1 loading
def load_h1(cfd: str) -> pd.DataFrame:
    """Canonical true-UTC M1 -> H1 (left-labelled bars, so close(bar h) = price at h+1)."""
    cache = REPO / "yt_strategy_replications" / "data_cache" / "gold" / f"{cfd}_1h.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
    else:
        src = REPO / "data" / "deep_history_utc" / f"{cfd}_M1.csv"
        d = pd.read_csv(src, usecols=["timestamp_utc", "open", "high", "low", "close",
                                      "tick_volume", "spread"])
        d.index = pd.to_datetime(d["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
        d = d.drop(columns=["timestamp_utc"]).astype("float64")
        df = (d.resample("1h").agg({"open": "first", "high": "max", "low": "min",
                                    "close": "last", "tick_volume": "sum", "spread": "mean"})
              .dropna(subset=["close"]))
    return df


# ------------------------------------------------------- window return machinery
def window_returns(h1: pd.DataFrame, start_utc_winter: int, hours: int,
                   anchor: str = "utc") -> pd.Series:
    """Per-day log return of the overnight window, indexed by the entry date.

    anchor='utc'      : window start fixed at `start_utc_winter` UTC all year (legacy spec A).
    anchor='exchange' : window start fixed in EXCHANGE local time, i.e. one UTC hour
                        earlier during US DST (spec B).

    Bars are left-labelled, so the hourly log return stamped at hour h is
    log(P(h+1)/P(h)). Summing hours [s, s+hours-1] gives log(P(s+hours)/P(s)).
    Complete windows only (every hour present), as in the source studies.
    """
    lr = np.log(h1["close"] / h1["close"].shift(1))
    idx = lr.index
    dst = us_dst(idx)
    start = np.full(len(idx), start_utc_winter, dtype=int)
    if anchor == "exchange":
        start = np.where(dst, (start_utc_winter - 1) % 24, start_utc_winter)
    elif anchor != "utc":
        raise ValueError(anchor)

    hour = idx.hour.to_numpy()
    # offset of this bar within the window that starts at `start`
    off = (hour - start) % 24
    inwin = off < hours
    aday = (idx - pd.to_timedelta(start, unit="h")).normalize()

    df = pd.DataFrame({"lr": lr.to_numpy(), "aday": aday, "inwin": inwin}).dropna(subset=["lr"])
    df = df[df["inwin"]]
    g = df.groupby("aday")["lr"]
    return g.sum()[g.count() == hours]


def vol_target(win: pd.Series, lookback: int = 20, cap: float = 3.0) -> pd.Series:
    """Causal vol-target multiplier, identical to the source studies."""
    rv = win.rolling(lookback, min_periods=lookback).std().shift(1)
    target = rv.expanding(min_periods=lookback).median()
    return (target / rv).clip(upper=cap).fillna(0.0)


def net_series(win: pd.Series, rt_bps: float, cap: float = 3.0) -> pd.Series:
    pos = vol_target(win, cap=cap)
    return (pos * win - pos.abs() * rt_bps * 1e-4).dropna()


def obs_per_year(s: pd.Series) -> float:
    span = (s.index[-1] - s.index[0]).days / 365.25
    return len(s) / span if span > 0 else float("nan")


def sharpe(s: pd.Series) -> float:
    a = np.asarray(s, dtype=float)
    if a.size < 30 or a.std(ddof=1) == 0:
        return float("nan")
    return float(a.mean() / a.std(ddof=1) * np.sqrt(obs_per_year(s)))


def max_dd(s: pd.Series) -> float:
    eq = (1 + pd.Series(np.asarray(s, dtype=float))).cumprod()
    return float((eq / eq.cummax() - 1).min())


def cagr(s: pd.Series) -> float:
    span = (s.index[-1] - s.index[0]).days / 365.25
    tot = float((1 + pd.Series(np.asarray(s, dtype=float))).prod())
    return tot ** (1 / span) - 1 if span > 0 else float("nan")


def hac_t(s: pd.Series, lags: int = 6) -> tuple[float, float]:
    import statsmodels.api as sm
    a = np.asarray(s, dtype=float)
    m = sm.OLS(a, np.ones(len(a))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(m.params[0]), float(m.tvalues[0])


def block_bootstrap_diff(a: pd.Series, b: pd.Series, n_boot: int = 5000,
                         mean_block: int = 10, seed: int = 7) -> dict:
    """Paired stationary block bootstrap on Sharpe(a) - Sharpe(b) over common dates.

    Politis-Romano geometric block lengths. One-sided p that the observed
    difference could arise with zero true difference (centred resampling).
    """
    common = a.index.intersection(b.index)
    x = np.asarray(a.reindex(common), dtype=float)
    y = np.asarray(b.reindex(common), dtype=float)
    n = len(x)
    if n < 60:
        return dict(n=n, obs=float("nan"), p=float("nan"))

    def sr(v):
        sd = v.std(ddof=1)
        return v.mean() / sd if sd > 0 else 0.0

    obs = sr(x) - sr(y)
    rng = np.random.default_rng(seed)
    p_geom = 1.0 / mean_block
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = np.empty(n, dtype=int)
        j = 0
        while j < n:
            s = rng.integers(0, n)
            L = min(rng.geometric(p_geom), n - j)
            idx[j:j + L] = (s + np.arange(L)) % n
            j += L
        diffs[i] = sr(x[idx]) - sr(y[idx])
    centred = diffs - diffs.mean()
    p = float((np.abs(centred) >= abs(obs)).mean())
    return dict(n=n, obs=float(obs), p=p,
                ci=[float(np.percentile(diffs, 5)), float(np.percentile(diffs, 95))])
