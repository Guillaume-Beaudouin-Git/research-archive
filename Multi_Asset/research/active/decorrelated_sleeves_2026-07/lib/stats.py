"""Statistical toolkit — HAC t, Sharpe, Deflated Sharpe (Bailey-Lopez de Prado),
OU half-life, block bootstrap. All per-repo methodology (HAC lag-6, DSR for n_mod>1)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats as sps

TRADING_DAYS = 252.0


def sharpe(r: np.ndarray, ann: float = TRADING_DAYS) -> float:
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    if r.std(ddof=1) == 0 or len(r) < 3:
        return 0.0
    return r.mean() / r.std(ddof=1) * np.sqrt(ann)


def hac_tstat(r: np.ndarray, lags: int = 6) -> float:
    """Newey-West HAC t-stat of the mean of a daily P&L / return series."""
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    n = len(r)
    if n < 10 or r.std() == 0:
        return 0.0
    mu = r.mean()
    e = r - mu
    gamma0 = (e @ e) / n
    s = gamma0
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1.0)
        cov = (e[k:] @ e[:-k]) / n
        s += 2.0 * w * cov
    se = np.sqrt(max(s, 1e-16) / n)
    return mu / se


def ou_halflife(spread: np.ndarray) -> float:
    """Half-life of mean reversion from AR(1): d(spread)_t = a + b*spread_{t-1}. HL = -ln2/ln(1+b)."""
    s = pd.Series(spread).dropna().values
    if len(s) < 20:
        return np.nan
    lag = s[:-1]
    d = np.diff(s)
    X = np.column_stack([np.ones_like(lag), lag])
    beta, *_ = np.linalg.lstsq(X, d, rcond=None)
    b = beta[1]
    if b >= 0:
        return np.inf  # not mean-reverting
    return -np.log(2.0) / np.log(1.0 + b)


def psr(sr_obs: float, T: int, skew: float, kurt: float, sr_star: float = 0.0) -> float:
    """Probabilistic Sharpe Ratio (per-observation SR units). kurt = full (normal=3)."""
    denom = np.sqrt(max(1.0 - skew * sr_obs + (kurt - 1.0) / 4.0 * sr_obs ** 2, 1e-12))
    z = (sr_obs - sr_star) * np.sqrt(max(T - 1, 1)) / denom
    return float(sps.norm.cdf(z))


def deflated_sharpe(sr_trials, sr_obs: float, T: int, skew: float, kurt: float):
    """Bailey-Lopez de Prado DSR.
    sr_trials: array of per-observation SR across ALL trials (search space).
    sr_obs:    per-observation SR of the selected strategy.
    Returns (DSR, sr_star)."""
    sr_trials = np.asarray(sr_trials, float)
    sr_trials = sr_trials[~np.isnan(sr_trials)]
    N = max(len(sr_trials), 1)
    V = np.var(sr_trials, ddof=1) if N > 1 else max(sr_obs ** 2, 1e-8)
    euler = 0.5772156649
    zN = sps.norm.ppf(1.0 - 1.0 / N) if N > 1 else 0.0
    zNe = sps.norm.ppf(1.0 - 1.0 / (N * np.e)) if N > 1 else 0.0
    sr_star = np.sqrt(V) * ((1 - euler) * zN + euler * zNe)
    return psr(sr_obs, T, skew, kurt, sr_star), float(sr_star)


def block_bootstrap_p(r: np.ndarray, block: int = 10, n: int = 5000, seed: int = 7) -> float:
    """One-sided p-value that mean>0 via circular block bootstrap (Politis-Romano)."""
    rng = np.random.default_rng(seed)
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    T = len(r)
    if T < block * 3:
        return np.nan
    obs = r.mean()
    nb = int(np.ceil(T / block))
    idx0 = rng.integers(0, T, size=(n, nb))
    offs = np.arange(block)
    means = np.empty(n)
    for i in range(n):
        idx = (idx0[i][:, None] + offs).ravel()[:T] % T
        means[i] = r[idx].mean()
    centered = means - means.mean()
    return float((centered >= obs).mean())


def annualized_stats(pnl: pd.Series, ann: float = TRADING_DAYS) -> dict:
    """pnl = daily return series (fraction). Reports Sharpe, ann ret, vol, maxDD, skew, kurt."""
    r = pnl.dropna()
    if len(r) < 5:
        return dict(sharpe=0, ann_ret=0, ann_vol=0, maxdd=0, skew=0, kurt=3, n=len(r))
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    return dict(
        sharpe=sharpe(r.values, ann),
        ann_ret=(1 + r.mean()) ** ann - 1,
        ann_vol=r.std(ddof=1) * np.sqrt(ann),
        maxdd=float(dd),
        skew=float(sps.skew(r.values)),
        kurt=float(sps.kurtosis(r.values, fisher=False)),
        hac_t=hac_tstat(r.values),
        n=int(len(r)),
    )
