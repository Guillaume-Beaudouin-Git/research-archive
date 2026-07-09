"""
Phase B — Dual vs Single cross-sectional momentum on commodity futures.

Implements the signals and monthly backtest frozen in
`PHASE_B_PREREGISTRATION_dual_momentum_2026-07-09.md`.

S_XS   : cross-sectional rank of the L-month total return (skip s). Long top tercile,
         short bottom tercile, risk-parity (inverse 63d vol) within leg, dollar-neutral.
S_DUAL : identical XS ranking, but an asset takes its position ONLY if it also passes its
         own absolute filter (long iff mom>0, short iff mom<0); otherwise flat (weight 0),
         WITHOUT renormalising → gross exposure shrinks in broad bear/bull regimes (the
         mechanism that is claimed to cut tail drawdowns).

Signal at month-end T-1, execute month-end T (no look-ahead): weight decided from prices
through month t is applied to the return of month t+1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252
MONTHS = 12
COST_RT = 0.00015          # 0.015% round-trip, CME Tier-1 futures (L11 / CLAUDE.md)


def _monthly_close(close: pd.DataFrame) -> pd.DataFrame:
    return close.resample("ME").last()


def _monthly_vol(close: pd.DataFrame, lookback_d: int = 63) -> pd.DataFrame:
    """63-day realised daily-log-ret vol, annualised, sampled at month-end."""
    lr = np.log(close / close.shift(1))
    vol_d = lr.rolling(lookback_d).std() * np.sqrt(TRADING_DAYS)
    return vol_d.resample("ME").last()


def momentum_signal(close_m: pd.DataFrame, L: int, s: int) -> pd.DataFrame:
    """L-month total return skipping the most-recent s months (month-end panel)."""
    return close_m.shift(s) / close_m.shift(s + L) - 1.0


def build_weights(
    mom: pd.DataFrame,
    vol_m: pd.DataFrame,
    dual: bool,
) -> pd.DataFrame:
    """
    Cross-sectional tercile long/short, risk-parity within leg, dollar-neutral.
    If dual=True, drop long positions with mom<=0 and short positions with mom>=0
    (flat, no renormalisation).
    Returns a (month x asset) weight frame (NaN → 0 exposure).
    """
    w = pd.DataFrame(0.0, index=mom.index, columns=mom.columns)
    inv_vol = 1.0 / vol_m.replace(0.0, np.nan)

    for t in mom.index:
        row = mom.loc[t]
        iv = inv_vol.loc[t]
        valid = row.notna() & iv.notna() & (iv > 0)
        n = int(valid.sum())
        if n < 6:                      # need enough names for a cross-section
            continue
        r = row[valid]
        k = n // 3                     # tercile size
        if k < 1:
            continue
        ranked = r.sort_values()
        shorts = ranked.index[:k]
        longs = ranked.index[-k:]

        wl = iv[longs].copy()
        ws = iv[shorts].copy()
        if dual:
            wl = wl[row[longs] > 0]    # long only if its own mom > 0
            ws = ws[row[shorts] < 0]   # short only if its own mom < 0
        if wl.sum() > 0:
            w.loc[t, wl.index] = (wl / wl.sum()).values          # long leg → +1 gross
        if ws.sum() > 0:
            w.loc[t, ws.index] = -(ws / ws.sum()).values         # short leg → -1 gross
    return w


def backtest(
    close: pd.DataFrame,
    L: int,
    s: int,
    dual: bool,
    cost_rt: float = COST_RT,
) -> dict:
    """
    Monthly dollar-neutral backtest. Weight at month t applied to return of month t+1.
    Returns net/gross monthly P&L series, per-leg P&L, turnover, and IC series.
    """
    close_m = _monthly_close(close)
    vol_m = _monthly_vol(close)
    mom = momentum_signal(close_m, L, s)

    w = build_weights(mom, vol_m, dual=dual)

    ret_next = close_m.pct_change().shift(-1)          # return of month t+1, placed at t
    gross = (w * ret_next).sum(axis=1)
    long_pnl = (w.clip(lower=0) * ret_next).sum(axis=1)
    short_pnl = (w.clip(upper=0) * ret_next).sum(axis=1)

    turnover = (w - w.shift(1)).abs().sum(axis=1)
    cost = turnover * (cost_rt / 2.0)                  # one-way = RT/2 per unit turnover
    net = gross - cost

    # cross-sectional IC: mom[t] vs realised return of month t+1
    ic = mom.corrwith(ret_next, axis=1, method="spearman")

    valid = net.dropna().index
    return {
        "net": net.loc[valid],
        "gross": gross.loc[valid],
        "long_pnl": long_pnl.loc[valid],
        "short_pnl": short_pnl.loc[valid],
        "turnover": turnover.loc[valid],
        "ic": ic.dropna(),
        "weights": w,
    }


# ── metrics ─────────────────────────────────────────────────────────────────────

def sharpe_m(r: pd.Series) -> float:
    r = r.dropna()
    if len(r) < 6 or r.std() == 0:
        return np.nan
    return float((r.mean() / r.std()) * np.sqrt(MONTHS))


def maxdd_unit_vol(r: pd.Series) -> float:
    """MaxDD of the return series standardised to unit vol (matched-vol, comparable)."""
    r = r.dropna()
    if len(r) < 6 or r.std() == 0:
        return np.nan
    z = r / r.std()
    eq = (1.0 + z * 0.02).cumprod()    # 2% monthly vol scaling just to form an equity curve
    return float(((eq - eq.cummax()) / eq.cummax()).min())


def hac_t_mean(x: pd.Series, lag: int = 2) -> float:
    """Newey-West HAC t-stat on the mean of a series (H0: mean = 0)."""
    x = x.dropna().values
    n = len(x)
    if n < 12:
        return np.nan
    mu = x.mean()
    e = x - mu
    gamma0 = (e @ e) / n
    var = gamma0
    for k in range(1, lag + 1):
        cov = (e[k:] @ e[:-k]) / n
        var += 2 * (1 - k / (lag + 1)) * cov
    se = np.sqrt(var / n)
    return float(mu / se) if se > 0 else np.nan
