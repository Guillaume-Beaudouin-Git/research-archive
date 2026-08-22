"""
Performance and statistical-significance metrics shared across all modules.

Methodology choices (aligned with the project constitution in CLAUDE.md):
- Sharpe is computed on a REGULARLY SAMPLED return series (daily realized P&L)
  and annualised by sqrt(trading_days_per_year). We never annualise a per-trade
  series by sqrt(252) (lesson L47).
- Significance uses HAC / Newey-West standard errors (lag 6 default) because
  trade P&L clusters in time (lesson L12b, methodology toolkit).
- Multiple testing is penalised explicitly via the Deflated Sharpe Ratio
  (Bailey & Lopez de Prado, 2014) and a stationary block bootstrap p-value
  (Politis-Romano) instead of an i.i.d. bootstrap.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as sstats
from scipy.stats import norm
import statsmodels.api as sm

EULER_MASCHERONI = 0.5772156649015329


def max_drawdown(equity) -> tuple[float, np.ndarray]:
    """Return (max_drawdown, drawdown_series). Drawdown is <= 0."""
    equity = np.asarray(equity, dtype=float)
    if equity.size == 0:
        return float("nan"), np.array([])
    running_max = np.maximum.accumulate(equity)
    dd = equity / running_max - 1.0
    return float(dd.min()), dd


def sharpe_ratio(returns, periods_per_year: float, rf_per_period: float = 0.0) -> float:
    """Annualised Sharpe of a regularly sampled return series."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:
        return float("nan")
    excess = r - rf_per_period
    sd = excess.std(ddof=1)
    if sd == 0:
        return float("nan")
    return float(excess.mean() / sd * np.sqrt(periods_per_year))


def sortino_ratio(returns, periods_per_year: float, rf_per_period: float = 0.0) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:
        return float("nan")
    excess = r - rf_per_period
    downside = excess[excess < 0]
    dd = np.sqrt((downside ** 2).mean()) if downside.size else 0.0
    if dd == 0:
        return float("nan")
    return float(excess.mean() / dd * np.sqrt(periods_per_year))


def profit_factor(trade_returns) -> float:
    r = np.asarray(trade_returns, dtype=float)
    gains = r[r > 0].sum()
    losses = -r[r < 0].sum()
    if losses == 0:
        return float("inf") if gains > 0 else float("nan")
    return float(gains / losses)


def win_rate(trade_returns) -> float:
    r = np.asarray(trade_returns, dtype=float)
    return float((r > 0).mean()) if r.size else float("nan")


def expectancy(trade_returns) -> float:
    r = np.asarray(trade_returns, dtype=float)
    return float(r.mean()) if r.size else float("nan")


def cagr(total_return: float, years: float) -> float:
    if years <= 0 or (1 + total_return) <= 0:
        return float("nan")
    return float((1 + total_return) ** (1 / years) - 1)


def hac_tstat(returns, lags: int = 6) -> tuple[float, float]:
    """Newey-West t-stat for H0: mean(returns) = 0. Returns (mean, t_stat)."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 10 or r.std() == 0:
        return float("nan"), float("nan")
    X = np.ones((r.size, 1))
    model = sm.OLS(r, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(model.params[0]), float(model.tvalues[0])


def deflated_sharpe_ratio(returns, n_trials: int, sr_benchmark: float = 0.0,
                          periods_per_year: float | None = None) -> dict:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).

    Operates on the per-observation Sharpe of `returns`. `n_trials` is the number
    of independent strategy configurations searched (drives the deflation
    benchmark SR0 = expected max Sharpe under the null). DSR is the probability
    that the true Sharpe exceeds the benchmark after correcting for skew,
    kurtosis, sample length and selection.
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    T = r.size
    if T < 10 or r.std(ddof=1) == 0:
        return {"dsr": float("nan")}
    sr = r.mean() / r.std(ddof=1)  # per-observation Sharpe
    g3 = float(sstats.skew(r))
    g4 = float(sstats.kurtosis(r, fisher=False))  # non-excess kurtosis
    n_trials = max(int(n_trials), 2)
    sr_trial_std = 1.0 / np.sqrt(T)  # under H0, std of the SR estimate
    sr0 = sr_trial_std * (
        (1 - EULER_MASCHERONI) * norm.ppf(1 - 1.0 / n_trials)
        + EULER_MASCHERONI * norm.ppf(1 - 1.0 / (n_trials * np.e))
    ) + sr_benchmark
    denom = 1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2
    if denom <= 0:
        return {"dsr": float("nan"), "sr_per_obs": sr, "sr0_per_obs": sr0}
    dsr = float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / np.sqrt(denom)))
    out = {
        "dsr": dsr,
        "sr_per_obs": float(sr),
        "sr0_per_obs": float(sr0),
        "skew": g3,
        "kurtosis": g4,
        "n_obs": int(T),
        "n_trials": int(n_trials),
    }
    if periods_per_year:
        out["sr_annual"] = float(sr * np.sqrt(periods_per_year))
        out["sr0_annual"] = float(sr0 * np.sqrt(periods_per_year))
    return out


def stationary_bootstrap_pvalue(returns, n_boot: int = 2000, mean_block: int = 20,
                                seed: int = 0) -> float:
    """
    Politis-Romano stationary bootstrap p-value for H0: mean <= 0 vs H1: mean > 0.
    Blocks of geometric length (mean = mean_block) preserve autocorrelation, which
    an i.i.d. bootstrap would destroy (methodology toolkit: i.i.d. forbidden when
    trades cluster).
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = r.size
    if n < 20:
        return float("nan")
    rng = np.random.default_rng(seed)
    obs = r.mean()
    centered = r - obs  # impose the null
    p = 1.0 / mean_block
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = np.empty(n, dtype=np.int64)
        i = rng.integers(0, n)
        for k in range(n):
            idx[k] = i
            if rng.random() < p:
                i = rng.integers(0, n)
            else:
                i = i + 1 if i + 1 < n else 0
        boots[b] = centered[idx].mean()
    return float((boots >= obs).mean())


def fold_metrics(daily_returns, n_folds: int = 5, periods_per_year: float = 365.0) -> dict:
    """
    Split a daily return series into n_folds equal-time segments and report the
    Sharpe of each. For rule-based strategies with no fitted parameters every
    segment is effectively out-of-sample, so the fraction of positive folds is a
    walk-forward consistency score (CLAUDE.md gate: WF > 50% / 60%).
    """
    r = np.asarray(daily_returns, dtype=float)
    n = r.size
    if n < n_folds * 5:
        return {"wf_score": float("nan"), "fold_sharpes": []}
    bounds = np.linspace(0, n, n_folds + 1).astype(int)
    sharpes = []
    for k in range(n_folds):
        seg = r[bounds[k]:bounds[k + 1]]
        sharpes.append(sharpe_ratio(seg, periods_per_year))
    sharpes = [s for s in sharpes]
    positive = [s for s in sharpes if not np.isnan(s) and s > 0]
    valid = [s for s in sharpes if not np.isnan(s)]
    wf = len(positive) / len(valid) if valid else float("nan")
    return {"wf_score": wf, "fold_sharpes": [round(s, 3) for s in sharpes]}
