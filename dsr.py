"""
dsr.py

Deflated Sharpe Ratio (DSR) — Bailey & López de Prado (2014).

The DSR penalises the observed Sharpe Ratio for:
  1. Non-normality of returns (skewness, excess kurtosis)
  2. Multiple testing: the more strategy variants tried, the more likely
     one looks good by chance.

Reference:
  Bailey, D. H., & López de Prado, M. (2014).
  "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest
  Overfitting and Non-Normality."
  Journal of Portfolio Management, 40(5), 94-107.
  https://doi.org/10.3905/jpm.2014.40.5.094

Formula (eq. 4 in the paper):
  PSR(SR*) = Φ( (SR_hat - SR*) * sqrt(T-1) /
                sqrt(1 - γ_3*SR_hat + ((γ_4-1)/4)*SR_hat²) )

  DSR = PSR( E[max SR] )   where   E[max SR] ≈ expected maximum SR
        under the null given n_trials iid draws.

  E[max SR] ≈ ((1 - γ) * Φ⁻¹(1 - 1/n_trials) +
               γ       * Φ⁻¹(1 - 1/(n_trials*e))) * σ_SR + μ_SR

  with γ = Euler-Mascheroni constant (≈ 0.5772).

Usage:
    from dsr import deflated_sharpe_ratio
    dsr_value = deflated_sharpe_ratio(returns, n_trials=50, periods_per_year=365)
"""

import math
from typing import Union

import numpy as np
from scipy.stats import norm


# Euler-Mascheroni constant
_EULER_GAMMA = 0.5772156649015328


def _sharpe_ratio(returns: np.ndarray, periods_per_year: int = 365,
                  rf: float = 0.02) -> float:
    """
    Annualised Sharpe Ratio from a series of per-period returns.

    Args:
        returns:          Array of per-period returns (e.g. daily).
        periods_per_year: 365 for daily, 252 for business-day, 8760 for hourly.
        rf:               Annual risk-free rate (default 2%).

    Returns:
        Annualised Sharpe Ratio (float).
    """
    rf_per_period = rf / periods_per_year
    excess = returns - rf_per_period
    mean = excess.mean()
    std = excess.std(ddof=1)
    if std < 1e-12:
        return 0.0
    return float(mean / std * math.sqrt(periods_per_year))


def _moments(returns: np.ndarray) -> tuple[float, float, float, float]:
    """
    Return (mean, std, skewness, excess_kurtosis) of a returns array.
    Uses unbiased estimators where applicable.
    """
    n = len(returns)
    mean = returns.mean()
    std = returns.std(ddof=1)
    if std < 1e-12:
        return mean, std, 0.0, 0.0
    z = (returns - mean) / std
    skew = float((z ** 3).mean())
    kurt = float((z ** 4).mean()) - 3.0   # excess kurtosis
    return mean, std, skew, kurt


def _expected_max_sr(n_trials: int, mean_sr: float = 0.0,
                     std_sr: float = 1.0) -> float:
    """
    Expected maximum Sharpe Ratio across n_trials independent backtests
    (Bailey & López de Prado 2014, eq. 10).

    Uses the expected maximum of n_trials standard-normal draws, scaled
    by std_sr and shifted by mean_sr.

    Args:
        n_trials:  Number of strategy variants tested (M in the paper).
        mean_sr:   Mean SR of the distribution of tested strategies.
        std_sr:    Std-dev of SR distribution (default 1.0 — conservative).

    Returns:
        E[max SR] (float).
    """
    if n_trials <= 1:
        return mean_sr

    emax = (
        (1.0 - _EULER_GAMMA) * norm.ppf(1.0 - 1.0 / n_trials)
        + _EULER_GAMMA * norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    )
    return mean_sr + std_sr * emax


def probabilistic_sharpe_ratio(
    returns: np.ndarray,
    sr_benchmark: float,
    periods_per_year: int = 365,
    rf: float = 0.02,
) -> float:
    """
    Probabilistic Sharpe Ratio: probability that the true SR exceeds sr_benchmark,
    adjusted for non-normality (Bailey & López de Prado 2014, eq. 4).

    Args:
        returns:          Per-period return series.
        sr_benchmark:     Benchmark SR to test against (SR* in the paper).
        periods_per_year: Annualisation factor.
        rf:               Annual risk-free rate.

    Returns:
        PSR ∈ (0, 1) — probability that SR_hat > sr_benchmark in population.
    """
    n = len(returns)
    sr_hat = _sharpe_ratio(returns, periods_per_year, rf)
    _, _, skew, kurt_excess = _moments(returns)

    # Variance of SR estimator (eq. 4 denominator, annualised SR, per-period stats)
    # Note: SR_hat here is the per-period SR (before annualisation) for the formula.
    sr_hat_raw = sr_hat / math.sqrt(periods_per_year)   # de-annualise for the formula
    sr_bench_raw = sr_benchmark / math.sqrt(periods_per_year)

    var_sr = (1.0 - skew * sr_hat_raw
              + (kurt_excess / 4.0) * sr_hat_raw ** 2) / (n - 1)

    if var_sr <= 0:
        var_sr = 1e-12

    z = (sr_hat_raw - sr_bench_raw) / math.sqrt(var_sr)
    return float(norm.cdf(z))


def deflated_sharpe_ratio(
    returns: np.ndarray,
    n_trials: int,
    periods_per_year: int = 365,
    rf: float = 0.02,
    mean_sr_trials: float = 0.0,
    std_sr_trials: float = 1.0,
) -> dict:
    """
    Deflated Sharpe Ratio (DSR).

    Computes PSR against the expected maximum SR from n_trials independent
    strategy backtests, correcting for selection bias and non-normality.

    Args:
        returns:          Per-period return series (numpy array).
        n_trials:         Number of strategy variants / hyperparameter
                          combinations tried (including this one).
        periods_per_year: Annualisation factor (365 for daily).
        rf:               Annual risk-free rate (default 2%).
        mean_sr_trials:   Mean SR of the distribution of tried strategies
                          (default 0 — conservative / most common).
        std_sr_trials:    Std-dev of SR across tried strategies
                          (default 1.0 — conservative).

    Returns:
        dict with keys:
            sharpe          – observed annualised Sharpe Ratio
            sr_benchmark    – E[max SR] used as the benchmark
            dsr             – DSR = PSR(E[max SR]) ∈ (0, 1)
            skewness        – return skewness
            excess_kurtosis – excess kurtosis
            n_obs           – number of observations
            passed          – True if DSR >= 0.95 (conventional threshold)
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    n = len(returns)

    sr_hat = _sharpe_ratio(returns, periods_per_year, rf)
    _, _, skew, kurt_excess = _moments(returns)
    sr_benchmark = _expected_max_sr(n_trials, mean_sr_trials, std_sr_trials)
    dsr = probabilistic_sharpe_ratio(returns, sr_benchmark, periods_per_year, rf)

    return {
        "sharpe":          sr_hat,
        "sr_benchmark":    sr_benchmark,
        "dsr":             dsr,
        "skewness":        skew,
        "excess_kurtosis": kurt_excess,
        "n_obs":           n,
        "passed":          dsr >= 0.95,
    }
