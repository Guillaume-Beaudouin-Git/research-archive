"""Shared engine for the Treasury-auction event study.

Conventions frozen in PREREGISTRATION.md:
  * Close->Close log returns only. `ZN=F.Open` is FORBIDDEN (it is the 18:00 ET Globex
    open of the *previous* calendar day, L51/L52).
  * Futures price returns ARE excess returns (fully-collateralised future).
  * PRE  leg: short, close(t-k) -> close(t-1)   [k = 3 primary]
  * POST leg: long,  close(t-1) -> close(t+m)   [m = 2 primary]
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT.parents[3]
MEV = REPO / "Multi_Asset/research/active/month_end_vehicle_2026-07/data"

TICKER_FILE = {"ZN": "daily_ZNF.parquet", "ZB": "daily_ZBF.parquet",
               "ZF": "daily_ZFF.parquet", "TLT": "daily_TLT.parquet",
               "IEF": "daily_IEF.parquet"}

# --- cost model (PREREGISTRATION 6), in bps of notional, per S_V event (2 round trips)
COST_CENTRAL_BPS = 3.3
COST_STRESS_BPS = 6.1


def load_px(sym: str) -> pd.DataFrame:
    df = pd.read_parquet(MEV / TICKER_FILE[sym])
    df = df[["Close"]].rename(columns={"Close": "close"}).dropna()
    df.index = pd.DatetimeIndex(df.index).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df["ret"] = np.log(df["close"]).diff()
    return df


def load_auctions() -> pd.DataFrame:
    return pd.read_parquet(ROOT / "data" / "auctions.parquet")


def b1_active_days(idx: pd.DatetimeIndex, n_last: int = 3) -> pd.Series:
    """Boolean Series: True on the last `n_last` trading days of each calendar month."""
    s = pd.Series(idx, index=idx)
    ym = s.dt.to_period("M")
    rank_from_end = s.groupby(ym).rank(method="first", ascending=False)
    return (rank_from_end <= n_last).reindex(idx).fillna(False)


def b1_daily_series(px: pd.DataFrame, n_last: int = 3) -> pd.Series:
    """B1 = long the Treasury complex on the last `n_last` trading days of the month."""
    act = b1_active_days(px.index, n_last)
    return (px["ret"] * act.astype(float)).rename("B1")


def event_positions(px_index: pd.DatetimeIndex, auction_dates: pd.Series,
                    k: int = 3, m: int = 2,
                    require_announced: pd.Series | None = None,
                    entry_lag_check: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map each auction to its PRE / POST trading-day windows.

    Returns (events, positions):
      events    one row per usable auction with the integer index of t-k, t-1, t+m
      positions DataFrame indexed like px with columns pre/post/net (in {-1,0,+1})
    """
    idx = px_index
    loc = pd.Series(np.arange(len(idx)), index=idx)
    rows = []
    for i, d in enumerate(auction_dates):
        # t = first trading day >= auction date (auctions are business days;
        # this only bites on the 3 Friday/holiday-shifted cases)
        pos = idx.searchsorted(d, side="left")
        if pos >= len(idx) or pos - k < 0 or pos + m >= len(idx):
            continue
        if idx[pos] != d:
            continue  # auction date not a price bar -> drop, never interpolate
        ann_ok = True
        if entry_lag_check and require_announced is not None:
            # information must be public at the ENTRY close, i.e. at date(t-k)
            ann_ok = bool(require_announced.iloc[i] <= idx[pos - k])
        rows.append({"auction_date": d, "i_t": pos, "announced_ok": ann_ok})
    ev = pd.DataFrame(rows)
    if ev.empty:
        return ev, pd.DataFrame(index=idx)

    pre = np.zeros(len(idx))
    post = np.zeros(len(idx))
    for _, r in ev[ev.announced_ok].iterrows():
        t = int(r.i_t)
        pre[t - k + 1: t] += -1.0      # returns on t-k+1 ... t-1   (short)
        post[t: t + m + 1] += +1.0     # returns on t ... t+m       (long)
    P = pd.DataFrame({"pre": pre, "post": post}, index=idx)
    P["net"] = P["pre"] + P["post"]
    return ev, P


def event_returns(px: pd.DataFrame, ev: pd.DataFrame, k: int = 3, m: int = 2) -> pd.DataFrame:
    """Per-event P&L in bps for the PRE (short), POST (long) and combined V legs."""
    c = px["close"].to_numpy()
    out = []
    for _, r in ev[ev.announced_ok].iterrows():
        t = int(r.i_t)
        pre = -(np.log(c[t - 1]) - np.log(c[t - k])) * 1e4      # short
        post = +(np.log(c[t + m]) - np.log(c[t - 1])) * 1e4     # long
        out.append({"auction_date": r.auction_date, "i_t": t,
                    "pre_bps": pre, "post_bps": post, "v_bps": pre + post})
    return pd.DataFrame(out)


def hac_t(x: np.ndarray, lags: int = 6) -> tuple[float, float]:
    """(mean, HAC Newey-West t-stat) of a series against a constant."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 10:
        return float(np.nan), float(np.nan)
    res = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(res.params[0]), float(res.tvalues[0])


def block_bootstrap_p(x: np.ndarray, block: int = 3, n_boot: int = 40000,
                      seed: int = 0) -> tuple[float, tuple[float, float]]:
    """Circular block bootstrap: two-sided p-value for mean != 0, and 95% CI."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return float(np.nan), (np.nan, np.nan)
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n, size=(n_boot, nb))
    offs = np.arange(block)
    idx = (starts[:, :, None] + offs[None, None, :]).reshape(n_boot, -1) % n
    means = x[idx[:, :n]].mean(axis=1)
    obs = x.mean()
    centred = means - obs
    p = float((np.abs(centred) >= abs(obs)).mean())
    ci = (float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))
    return p, ci


def ann_sharpe_per_event(x: np.ndarray, events_per_year: float) -> float:
    """L47: annualise a per-event Sharpe by sqrt(obs/year), never sqrt(252)."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float(np.nan)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(events_per_year))


def ann_sharpe_daily(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 30 or r.std(ddof=1) == 0:
        return float(np.nan)
    return float(r.mean() / r.std(ddof=1) * np.sqrt(252.0))


def max_dd(cum: np.ndarray) -> float:
    peak = np.maximum.accumulate(cum)
    return float(np.min(cum - peak))


REGIMES = {
    "pre-QE 2000-2008": ("2000-01-01", "2008-12-15"),
    "QE/ZIRP 2009-2021": ("2008-12-16", "2021-12-31"),
    "QT 2022-2026": ("2022-01-01", "2026-12-31"),
}
