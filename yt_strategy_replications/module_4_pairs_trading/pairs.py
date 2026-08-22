"""
Module 4 — pairs-trading / mean-reversion engine and diagnostics.

The video selects a pair by full-sample correlation, runs a cointegration/ADF
check on the *whole* history, then trades a z-score of the price ratio on that
same history. That is selection + look-ahead. This module provides the honest
machinery: causal (rolling) hedge ratios, out-of-sample z-scores, dollar-neutral
P&L with costs, and stability diagnostics (per-period cointegration, rolling ADF,
hedge-ratio drift).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, coint


def daily_corr(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().corr()


def engle_granger(p1: pd.Series, p2: pd.Series) -> tuple[float, float, float]:
    """OLS p1 ~ a + b·p2 on levels; ADF on residual. Returns (beta, adf_p, coint_p)."""
    d = pd.concat([p1, p2], axis=1).dropna()
    y, x = d.iloc[:, 0].to_numpy(), sm.add_constant(d.iloc[:, 1].to_numpy())
    beta = sm.OLS(y, x).fit().params
    resid = y - x @ beta
    adf_p = adfuller(resid, autolag="AIC")[1]
    coint_p = coint(d.iloc[:, 0], d.iloc[:, 1])[1]
    return float(beta[1]), float(adf_p), float(coint_p)


def rolling_hedge_ratio(p1: pd.Series, p2: pd.Series, win: int = 252,
                        use_log: bool = True) -> pd.Series:
    """Causal hedge ratio = trailing cov(l1,l2)/var(l2) over `win` (OOS at each t)."""
    l1 = np.log(p1) if use_log else p1
    l2 = np.log(p2) if use_log else p2
    cov = l1.rolling(win, min_periods=win).cov(l2)
    var = l2.rolling(win, min_periods=win).var()
    return cov / var


def spread_zscore(p1: pd.Series, p2: pd.Series, beta: pd.Series, z_win: int = 60,
                  use_log: bool = True) -> pd.Series:
    l1 = np.log(p1) if use_log else p1
    l2 = np.log(p2) if use_log else p2
    spread = l1 - beta * l2
    m = spread.rolling(z_win, min_periods=z_win).mean()
    s = spread.rolling(z_win, min_periods=z_win).std(ddof=0)
    return (spread - m) / s


def video_ratio_zscore(p1: pd.Series, p2: pd.Series, fast: int = 5, slow: int = 20) -> pd.Series:
    """The video's literal signal: z = (MA_fast(ratio) - MA_slow(ratio)) / std_slow(ratio)."""
    ratio = p1 / p2
    z = (ratio.rolling(fast, min_periods=fast).mean()
         - ratio.rolling(slow, min_periods=slow).mean()) / ratio.rolling(slow, min_periods=slow).std(ddof=0)
    return z


def backtest_spread(p1: pd.Series, p2: pd.Series, z: pd.Series, beta: pd.Series,
                    *, entry: float = 2.0, exit_band: float = 0.5,
                    cost_bps_leg: float = 5.0) -> pd.DataFrame:
    """
    Dollar-neutral spread reversion. State machine: enter long-spread when
    z < -entry, short-spread when z > +entry, flat when |z| < exit_band.
    Signal at close t, P&L over t->t+1 (1-bar lag). Costs charged on leg turnover.
    """
    d = pd.concat([p1, p2], axis=1).dropna()
    d.columns = ["p1", "p2"]
    z = z.reindex(d.index)
    beta = beta.reindex(d.index)
    r1, r2 = d.p1.pct_change(), d.p2.pct_change()

    zz = z.to_numpy()
    bb = beta.to_numpy()
    pos = np.zeros(len(d))
    cur = 0
    for i in range(len(d)):
        if np.isnan(zz[i]) or np.isnan(bb[i]):
            cur = 0
            pos[i] = 0
            continue
        if cur == 0:
            if zz[i] > entry:
                cur = -1
            elif zz[i] < -entry:
                cur = 1
        elif abs(zz[i]) < exit_band:
            cur = 0
        pos[i] = cur
    pos = pd.Series(pos, index=d.index)

    w = 1.0 / (1.0 + beta.abs())              # dollar-neutral normalisation
    spread_ret = w * (r1 - beta * r2)         # return of long-spread, per unit capital
    gross = pos.shift(1) * spread_ret
    turn = pos.diff().abs().fillna(pos.abs())  # legs traded
    cost = turn * (2 * cost_bps_leg * 1e-4)
    net = gross - cost
    out = pd.DataFrame({"z": z, "pos": pos, "gross": gross, "net": net}).dropna(subset=["gross"])
    return out


def per_period_coint(p1: pd.Series, p2: pd.Series, freq: str = "YS") -> pd.DataFrame:
    """Cointegration p-value computed within each calendar period (instability check)."""
    d = pd.concat([p1, p2], axis=1).dropna()
    d.columns = ["p1", "p2"]
    rows = []
    for label, g in d.groupby(pd.Grouper(freq=freq)):
        if len(g) < 60:
            continue
        try:
            cp = coint(g.p1, g.p2)[1]
            corr = g.p1.pct_change().corr(g.p2.pct_change())
        except Exception:
            cp = np.nan
            corr = np.nan
        rows.append({"period": label.year, "n": len(g), "coint_p": cp, "ret_corr": corr})
    return pd.DataFrame(rows)
