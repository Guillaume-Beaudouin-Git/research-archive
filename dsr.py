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

CALIBRATION OF σ_SR (`std_sr_trials`) — READ THIS BEFORE USING
--------------------------------------------------------------
σ_SR is the *cross-sectional standard deviation of the Sharpe Ratios of the
competing trials*, and it scales the whole deflation benchmark linearly.
It is expressed here in ANNUALISED Sharpe units (same units as the observed
Sharpe returned by `_sharpe_ratio`), because `probabilistic_sharpe_ratio`
de-annualises the benchmark internally.

Until 2026-07 this module carried a silent default `std_sr_trials = 1.0`.
That value is NOT conservative-but-harmless: σ_SR = 1.0 annualised is exactly
the pure sampling noise of a backtest that is ONE YEAR long
(sqrt(periods_per_year / T) = 1.0 when T = periods_per_year). Applied to a
13-year backtest (T ≈ 3276) it overstates the trial dispersion by ~3.6x, and
the deflation benchmark with it. Measured consequence at n_trials = 321:

    required observed Sharpe for DSR >= 0.95, T = 3276, normal returns
        std_sr_trials = 1.0    ->  SR >= 3.38     <-- unreachable
        std_sr_trials = 0.277  ->  SR >= 1.27     <-- honest sampling floor

The project constitution (CLAUDE.md, lesson L21) puts the realistic post-cost
band at SR 0.3-1.2 (cross-sectional daily), 0.8-2.0 (single-instrument
day-trade), 1.5-4.0 (delta-neutral crypto). A gate demanding SR >= 3.38 admits
no true positive from any of those families: it is a 100% type-II-error filter.

There is therefore no silent default any more. See `estimate_std_sr_trials`
and `sampling_noise_floor_sr`.

Usage:
    from dsr import deflated_sharpe_ratio, estimate_std_sr_trials

    sd = estimate_std_sr_trials(family_sharpes, periods_per_year=365, n_obs=len(returns))
    out = deflated_sharpe_ratio(returns, n_trials=50, periods_per_year=365,
                                std_sr_trials=sd)

NOTE ON `rf` (flagged 2026-07, deliberately NOT changed):
    `_sharpe_ratio` subtracts a risk-free rate with default `rf=0.02`. The
    project constitution requires returns to be EXCESS returns already. Passing
    excess returns while leaving `rf=0.02` subtracts the cash rate twice
    (~0.1 Sharpe at 1%/day vol). Pass `rf=0.0` when your series is already in
    excess terms. The default is left untouched here to avoid silently moving
    every historical number produced by this module.
"""

import math
import warnings
from typing import Optional, Sequence, Union

import numpy as np
from scipy.stats import norm


# Euler-Mascheroni constant
_EULER_GAMMA = 0.5772156649015328


class DSRCalibrationWarning(UserWarning):
    """Raised when a DSR is computed without an explicitly declared trial dispersion."""


def sampling_noise_floor_sr(n_obs: int, periods_per_year: int = 365) -> float:
    """
    Pure-sampling-noise standard deviation of the annualised Sharpe Ratio.

    Under H0 (true SR = 0, iid normal returns) the SR estimator has
    per-period standard deviation 1/sqrt(T), i.e. annualised

        sd(SR_annual) = sqrt(periods_per_year / T)

    This is the SMALLEST defensible value of `std_sr_trials`: even a family of
    trials that are all genuinely worthless will show at least this much
    dispersion in their measured Sharpes, purely from estimation error. It is
    the value implicitly used by `_automation/feasibility/stats/dsr.py` and by
    `yt_strategy_replications/engine/stats.py`.

    Args:
        n_obs:            Number of return observations T in the backtest.
        periods_per_year: Annualisation factor (365 daily crypto, 252 business).

    Returns:
        Annualised Sharpe standard deviation under the null (float).
    """
    if n_obs < 2:
        raise ValueError(f"n_obs must be >= 2 to define a sampling floor, got {n_obs}")
    return math.sqrt(periods_per_year / float(n_obs))


def estimate_std_sr_trials(
    sharpes: Sequence[float],
    periods_per_year: int = 365,
    n_obs: Optional[int] = None,
    apply_floor: bool = True,
) -> float:
    """
    Estimate `std_sr_trials` from the Sharpe Ratios actually observed across the
    trials of a strategy family.

    WHY THE OBSERVED DISPERSION IS THE RIGHT QUANTITY
    -------------------------------------------------
    Bailey & Lopez de Prado's E[max SR] is the expected maximum of `n_trials`
    draws from *the distribution of the trials you actually ran*. That
    distribution's spread has two components and you want BOTH:

      1. Estimation noise — every trial's Sharpe is measured with error
         ~ sqrt(periods_per_year / T), even if all trials are truly worthless.
      2. Genuine heterogeneity — the trials are not the same strategy. A grid
         over lookbacks, thresholds and instruments spans real differences in
         true Sharpe, which widens the distribution beyond pure noise.

    Using only component (1) under-deflates when the search was genuinely
    diverse (you understate how lucky the winner could get). Using an arbitrary
    constant such as 1.0 ignores both and, for any backtest longer than one
    year, massively OVER-deflates. The empirical standard deviation of the
    trial Sharpes is the one number that captures (1) and (2) jointly, which is
    exactly what the paper's benchmark is defined over.

    WHY THE FLOOR IS A GUARD-RAIL
    -----------------------------
    The observed dispersion is itself an estimate, and it is biased DOWNWARDS in
    the common failure modes:
      - few trials (`len(sharpes)` small) — the sample sd is noisy and, with
        n < ~10, frequently lands well below the truth;
      - a pre-filtered / survivorship-clipped family, where the losers were
        discarded before anyone wrote the Sharpes down;
      - a near-degenerate grid where every variant is nearly the same strategy.
    Each of those understates the deflation and produces FALSE POSITIVES, which
    is the expensive error for a research gate. Clamping at the sampling-noise
    floor sqrt(periods_per_year / T) makes the estimator never claim the trials
    are more tightly clustered than pure measurement error would allow.

    Args:
        sharpes:          Annualised Sharpe Ratios of the trials in the family
                          (include the winner). Non-finite values are dropped.
        periods_per_year: Annualisation factor, must match `sharpes`' convention.
        n_obs:            Backtest length T, used for the floor. Required when
                          `apply_floor` is True.
        apply_floor:      Clamp the result at `sampling_noise_floor_sr`.

    Returns:
        Estimated annualised std-dev of the trial Sharpe distribution (float).

    Raises:
        ValueError: fewer than 2 usable Sharpes, or floor requested without n_obs.
    """
    arr = np.asarray(list(sharpes), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        raise ValueError(
            f"need >= 2 finite trial Sharpes to estimate a dispersion, got {arr.size}. "
            "With a single trial there is no selection bias to deflate (use n_trials=1), "
            "or supply std_sr_trials explicitly."
        )

    observed = float(arr.std(ddof=1))

    if not apply_floor:
        return observed

    if n_obs is None:
        raise ValueError("n_obs is required when apply_floor=True (needed for the noise floor)")

    floor = sampling_noise_floor_sr(n_obs, periods_per_year)
    return max(observed, floor)


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


def _expected_max_sr(n_trials: int, mean_sr: float, std_sr: float) -> float:
    """
    Expected maximum Sharpe Ratio across n_trials independent backtests
    (Bailey & López de Prado 2014, eq. 10).

    Uses the expected maximum of n_trials standard-normal draws, scaled
    by std_sr and shifted by mean_sr.

    Both `mean_sr` and `std_sr` are ANNUALISED Sharpe units, and so is the
    returned benchmark. Neither has a default: `std_sr` in particular used to
    default to 1.0, which silently hard-coded a one-year-backtest noise level
    into every call (see module docstring).

    Args:
        n_trials:  Number of strategy variants tested (M in the paper).
        mean_sr:   Mean SR of the distribution of tested strategies (annualised).
        std_sr:    Std-dev of SR across tested strategies (annualised).

    Returns:
        E[max SR], annualised (float).
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

    # Bailey-LdP eq. 3 uses RAW kurtosis γ₄: var = [1 - γ₃·SR + (γ₄-1)/4·SR²]/(T-1).
    # `_moments` returns EXCESS kurtosis, so γ₄ - 1 = kurt_excess + 2.
    # (Before 2026-07 this line used kurt_excess/4, i.e. γ₄-3 instead of γ₄-1 —
    #  it dropped the +2/4 = 0.5·SR² term that survives even for normal returns,
    #  understating the SR estimator variance and inflating PSR/DSR. Both the
    #  other implementations in this repo already use the (γ₄-1)/4 form.)
    var_sr = (1.0 - skew * sr_hat_raw
              + ((kurt_excess + 2.0) / 4.0) * sr_hat_raw ** 2) / (n - 1)

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
    std_sr_trials: Optional[float] = None,
) -> dict:
    """
    Deflated Sharpe Ratio (DSR).

    Computes PSR against the expected maximum SR from n_trials independent
    strategy backtests, correcting for selection bias and non-normality.

    Args:
        returns:          Per-period return series (numpy array). Should already
                          be EXCESS returns; if so pass rf=0.0 (see module note).
        n_trials:         Number of strategy variants / hyperparameter
                          combinations tried (including this one).
        periods_per_year: Annualisation factor (365 for daily).
        rf:               Annual risk-free rate (default 2%).
        mean_sr_trials:   Mean SR of the distribution of tried strategies,
                          ANNUALISED (default 0 — the H0 of the paper).
        std_sr_trials:    Std-dev of SR across tried strategies, ANNUALISED.
                          NO SILENT DEFAULT. Either:
                            * a positive float you have declared — normally
                              `estimate_std_sr_trials(family_sharpes, ...)`; or
                            * None, which falls back to the sampling-noise floor
                              sqrt(periods_per_year / T) and emits a
                              DSRCalibrationWarning.
                          The fallback is not arbitrary — it is the exact
                          dispersion implied by the paper's null hypothesis — but
                          it is a LOWER bound, so it under-deflates whenever the
                          trials were genuinely heterogeneous. Declare the real
                          dispersion whenever you can.

    Returns:
        dict with keys:
            sharpe                 – observed annualised Sharpe Ratio
            sr_benchmark           – E[max SR] used as the benchmark (annualised)
            dsr                    – DSR = PSR(E[max SR]) ∈ (0, 1)
            skewness               – return skewness
            excess_kurtosis        – excess kurtosis
            n_obs                  – number of observations
            n_trials               – trials used for the deflation
            std_sr_trials          – the dispersion actually used (annualised)
            std_sr_trials_source   – 'declared' or 'sampling_noise_floor'
            passed                 – True if DSR >= 0.95 (conventional threshold)

    Raises:
        ValueError: if std_sr_trials is supplied but not strictly positive.
    """
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    n = len(returns)

    if std_sr_trials is None:
        std_sr_trials = sampling_noise_floor_sr(n, periods_per_year)
        std_sr_source = "sampling_noise_floor"
        warnings.warn(
            f"deflated_sharpe_ratio: std_sr_trials was not declared; falling back to the "
            f"sampling-noise floor sqrt({periods_per_year}/{n}) = {std_sr_trials:.4f} "
            f"(annualised Sharpe units). This is a LOWER bound on the true trial "
            f"dispersion and therefore UNDER-deflates if your trials were heterogeneous. "
            f"Pass std_sr_trials=estimate_std_sr_trials(family_sharpes, "
            f"periods_per_year={periods_per_year}, n_obs={n}) instead.",
            DSRCalibrationWarning,
            stacklevel=2,
        )
    else:
        std_sr_trials = float(std_sr_trials)
        if not (std_sr_trials > 0.0) or not math.isfinite(std_sr_trials):
            raise ValueError(
                f"std_sr_trials must be a finite positive annualised Sharpe std-dev, "
                f"got {std_sr_trials!r}"
            )
        std_sr_source = "declared"

    sr_hat = _sharpe_ratio(returns, periods_per_year, rf)
    _, _, skew, kurt_excess = _moments(returns)
    sr_benchmark = _expected_max_sr(n_trials, mean_sr_trials, std_sr_trials)
    dsr = probabilistic_sharpe_ratio(returns, sr_benchmark, periods_per_year, rf)

    return {
        "sharpe":               sr_hat,
        "sr_benchmark":         sr_benchmark,
        "dsr":                  dsr,
        "skewness":             skew,
        "excess_kurtosis":      kurt_excess,
        "n_obs":                n,
        "n_trials":             n_trials,
        "std_sr_trials":        float(std_sr_trials),
        "std_sr_trials_source": std_sr_source,
        "passed":               dsr >= 0.95,
    }
