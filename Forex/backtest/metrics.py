"""
Forex/backtest/metrics.py
=========================
Core performance metrics for FX carry strategy backtests.

Public API
----------
ic_summary(ic_series, maxlags) -> dict
    IC mean, std, t_HAC, n. Used for feasibility gates.

sharpe_hac(returns, ann_factor, maxlags) -> float
    Annualised Sharpe ratio with Newey-West HAC SE.

max_drawdown(returns) -> float
    Maximum peak-to-trough drawdown (negative value).

calmar(returns, ann_factor) -> float
    Annualised return / |MaxDD|.

wf_score(fold_sharpes) -> float
    Fraction of walk-forward folds with positive Sharpe.

perf_summary(returns, ann_factor, maxlags) -> dict
    Full metrics dict: Sharpe, MaxDD, Calmar, Ann_ret, WF n/a.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# IC statistics
# ─────────────────────────────────────────────────────────────────────────────

def ic_tstat_hac(ic_series: pd.Series, maxlags: int = 6) -> float:
    """
    Newey-West HAC t-stat for the mean of a cross-sectional IC series.

    Regresses IC on a constant; returns the HAC t-value of the intercept.
    This properly accounts for serial correlation in the IC time series.

    Parameters
    ----------
    ic_series : time series of per-period cross-sectional IC values.
    maxlags   : Newey-West lag truncation (default 6, as per project methodology).

    Returns
    -------
    float : HAC t-statistic (positive = positive IC, significant if |t| > 1.65/2.5).
    """
    import statsmodels.api as sm

    y = ic_series.dropna().values
    if len(y) < 12:
        return np.nan
    X = np.ones((len(y), 1))
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags}, use_t=True)
    return float(res.tvalues[0])


def ic_summary(ic_series: pd.Series, maxlags: int = 6) -> dict:
    """
    Summarise an IC time series with HAC t-stat.

    Returns
    -------
    dict with keys: ic_mean, ic_std, t_hac_lag6, ic_n, ic_min, ic_max, ir
    """
    s = ic_series.dropna()
    n = len(s)
    if n == 0:
        return {"ic_mean": np.nan, "ic_std": np.nan, "t_hac_lag6": np.nan,
                "ic_n": 0, "ic_min": np.nan, "ic_max": np.nan, "ir": np.nan}
    mean = float(s.mean())
    std  = float(s.std(ddof=1)) if n > 1 else np.nan
    t    = ic_tstat_hac(s, maxlags)
    ir   = mean / std if std and std > 0 else np.nan
    return {
        "ic_mean":    round(mean, 5),
        "ic_std":     round(std, 5),
        "t_hac_lag6": round(float(t), 3),
        "ic_n":       int(n),
        "ic_min":     round(float(s.min()), 4),
        "ic_max":     round(float(s.max()), 4),
        "ir":         round(float(ir), 3),
    }


def cross_sectional_ic(
    signal:  pd.DataFrame,
    fwd_ret: pd.DataFrame,
    min_obs: int = 5,
) -> pd.Series:
    """
    Per-period Spearman rank correlation between signal and forward return.

    Parameters
    ----------
    signal  : signal values, (T × N) DataFrame. Signal at T-1 (pre-shifted).
    fwd_ret : forward returns, (T × N) DataFrame. Return at T.
    min_obs : minimum non-NaN cross-section size to compute IC (default 5).

    Returns
    -------
    pd.Series : IC per time period, index = dates.
    """
    from scipy import stats

    common_cols = signal.columns.intersection(fwd_ret.columns)
    sig = signal[common_cols]
    ret = fwd_ret[common_cols]
    idx = sig.index.intersection(ret.index)

    ics = {}
    for t in idx:
        s = sig.loc[t].astype(float)
        r = ret.loc[t].astype(float)
        mask = s.notna() & r.notna()
        if mask.sum() < min_obs:
            continue
        rho, _ = stats.spearmanr(s[mask], r[mask])
        if np.isfinite(rho):
            ics[t] = rho

    return pd.Series(ics, name="ic").sort_index()


# ─────────────────────────────────────────────────────────────────────────────
# Return-based metrics
# ─────────────────────────────────────────────────────────────────────────────

def max_drawdown(returns: pd.Series) -> float:
    """Maximum peak-to-trough drawdown (negative float)."""
    equity = (1 + returns.fillna(0)).cumprod()
    return float((equity / equity.cummax() - 1).min())


def sharpe_hac(
    returns:    pd.Series,
    ann_factor: int = 12,
    maxlags:    int = 6,
) -> float:
    """
    Annualised Sharpe ratio with Newey-West HAC standard error.

    sr_hac = mean(r) / HAC_SE(r) * sqrt(ann_factor)

    Parameters
    ----------
    ann_factor : 12 for monthly, 52 for weekly, 252 for daily.

    Returns
    -------
    float
    """
    import statsmodels.api as sm

    r = returns.dropna()
    if len(r) < 12:
        return np.nan
    X = np.ones((len(r), 1))
    res = sm.OLS(r.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    mean_r    = float(res.params[0])
    hac_se    = float(res.bse[0])
    if hac_se == 0:
        return np.nan
    return float(mean_r / hac_se * np.sqrt(ann_factor))


def calmar(returns: pd.Series, ann_factor: int = 12) -> float:
    """Annualised return / |MaxDD|."""
    ann_ret = float(returns.mean() * ann_factor)
    mdd     = max_drawdown(returns)
    return ann_ret / abs(mdd) if mdd != 0 else np.nan


def wf_score(fold_sharpes: list[float]) -> float:
    """Fraction of WF folds with positive Sharpe."""
    if not fold_sharpes:
        return np.nan
    return sum(s > 0 for s in fold_sharpes) / len(fold_sharpes)


def perf_summary(
    returns:    pd.Series,
    ann_factor: int = 12,
    maxlags:    int = 6,
) -> dict:
    """
    Full performance metrics dict.

    Returns
    -------
    dict : sharpe_hac, max_dd, calmar, ann_ret_pct, n_periods, hit_rate
    """
    r = returns.dropna()
    return {
        "sharpe_hac":  round(sharpe_hac(r, ann_factor, maxlags), 3),
        "max_dd":      round(max_drawdown(r), 4),
        "calmar":      round(calmar(r, ann_factor), 3),
        "ann_ret_pct": round(float(r.mean() * ann_factor * 100), 2),
        "n_periods":   int(len(r)),
        "hit_rate":    round(float((r > 0).mean()), 3),
    }
