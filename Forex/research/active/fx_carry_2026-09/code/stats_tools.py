"""
Shared statistics: excess Sharpe, HAC t-stat, block bootstrap CI,
walk-forward, minimum detectable effect (L65: power factor 1.40).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.api as sm

TRADING_DAYS_PER_YEAR = 260


def load_rf_daily(index: pd.DatetimeIndex) -> pd.Series:
    """US DTB3 as daily risk-free, %/yr -> daily decimal, ffilled onto index."""
    import sys
    sys.path.insert(0, "<HOME>/Desktop/Algo_claude/.worktrees/fx-carry/Forex/research/active/fx_carry_2026-09/code")
    from rates import load_rates_monthly
    rates = load_rates_monthly()
    rf_m = rates["USD"].dropna() / 100.0 / TRADING_DAYS_PER_YEAR
    rf_m.index = rf_m.index + pd.offsets.MonthBegin(1)
    if getattr(index, "tz", None) is not None and rf_m.index.tz is None:
        rf_m.index = rf_m.index.tz_localize(index.tz)
    rf_daily = rf_m.reindex(index, method="ffill").bfill()
    return rf_daily


def excess_returns(net_pnl: pd.Series, rf_daily: pd.Series) -> pd.Series:
    return net_pnl - rf_daily.reindex(net_pnl.index).fillna(0.0)


def sharpe(ret: pd.Series) -> float:
    r = ret.dropna()
    if r.std() == 0 or len(r) < 2:
        return 0.0
    return r.mean() / r.std() * np.sqrt(TRADING_DAYS_PER_YEAR)


def hac_tstat(ret: pd.Series, lags: int = 6) -> tuple[float, float]:
    """Return (mean_daily, HAC t-stat) via OLS on a constant."""
    r = ret.dropna()
    if len(r) < 30:
        return (float(r.mean()) if len(r) else 0.0, np.nan)
    X = np.ones((len(r), 1))
    model = sm.OLS(r.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(model.params[0]), float(model.tvalues[0])


def block_bootstrap_sharpe_ci(
    ret: pd.Series, n_boot: int = 2000, block: int = 10, seed: int = 7
) -> tuple[float, float, np.ndarray]:
    """Vectorized Politis-Romano-style moving block bootstrap: draw
    n_blocks block-start indices per replication (all replications at
    once), gather via fancy indexing (no Python-level per-block loop)."""
    r = ret.dropna().values
    n = len(r)
    if n < block * 3:
        return (np.nan, np.nan, np.array([]))
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block, size=(n_boot, n_blocks))  # (n_boot, n_blocks)
    offsets = np.arange(block)
    idx = starts[:, :, None] + offsets[None, None, :]  # (n_boot, n_blocks, block)
    idx = idx.reshape(n_boot, n_blocks * block)[:, :n]  # (n_boot, n)
    samples = r[idx]  # (n_boot, n)
    mu = samples.mean(axis=1)
    sd = samples.std(axis=1)
    sharpes = np.where(sd == 0, 0.0, mu / sd * np.sqrt(TRADING_DAYS_PER_YEAR))
    lo, hi = np.percentile(sharpes, [2.5, 97.5])
    return float(lo), float(hi), sharpes


def walk_forward(ret: pd.Series, n_folds: int = 5) -> list[float]:
    r = ret.dropna()
    n = len(r)
    edges = np.linspace(0, n, n_folds + 1).astype(int)
    out = []
    for i in range(n_folds):
        seg = r.iloc[edges[i] : edges[i + 1]]
        out.append(sharpe(seg))
    return out


def mde_sharpe(n_obs: int, power_factor: float = 1.40, alpha: float = 0.05) -> float:
    """L65: minimum detectable Sharpe with power, factor 1.40 over the
    naive z-based MDE (z_alpha + z_power, power_factor bakes in the
    conventional 80% power inflation vs a bare significance threshold)."""
    from scipy.stats import norm
    z_alpha = norm.ppf(1 - alpha / 2)
    years = n_obs / TRADING_DAYS_PER_YEAR
    return power_factor * z_alpha / np.sqrt(years)
