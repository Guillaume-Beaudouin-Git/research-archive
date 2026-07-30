"""
Niveau B — Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).
Adjusts observed Sharpe for skewness, kurtosis, and number of independent trials
to produce a probability that the true Sharpe exceeds zero.

CALIBRATION OF THE TRIAL DISPERSION (2026-07)
---------------------------------------------
The deflation benchmark is E[max SR] over `n_trials` draws from the distribution
of the trials actually run, and it scales linearly with that distribution's
standard deviation σ_SR.

This module has always used the *sampling-noise* value of σ_SR implicitly, by
scaling the expected-max-of-n-normals by `se_sr_per` (the standard error of the
SR estimator, which shrinks like 1/sqrt(T)). That is the correct value under the
paper's null hypothesis, and it self-adjusts with the backtest length. It is
therefore NOT affected by the mis-calibration found in the repo-root `dsr.py`,
which hard-coded σ_SR = 1.0 in ANNUALISED units — a value equal to the sampling
noise of a 252-day backtest, hence ~3.6x too wide on a 13-year sample and
sufficient to make DSR >= 0.95 unreachable (required SR ~ 3.38 at n_trials=321).

What changed here: the dispersion is now an EXPLICIT parameter
(`std_sr_trials`, annualised) instead of an implicit side-effect, the value
actually used is reported in the output dict, and `estimate_std_sr_trials` lets
callers supply the empirically observed dispersion of a trial family — which is
what the paper's benchmark is really defined over, since it captures both
estimation noise and genuine heterogeneity between trials.

Keep `estimate_std_sr_trials` / `sampling_noise_floor_sr` numerically identical
to the repo-root `dsr.py` implementations; `tests/test_dsr.py` asserts they
agree and will fail loudly if the two copies drift apart again.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

TRADING_DAYS: int = 252
EULER_MASCHERONI: float = 0.5772156649015329
# Current n_tests for Algo_claude project — override per session as needed
ALGO_CLAUDE_N_TESTS: int = 274


def sampling_noise_floor_sr(n_obs: int, periods_per_year: int = TRADING_DAYS) -> float:
    """
    Pure-sampling-noise std-dev of the annualised Sharpe, sqrt(periods_per_year / T).

    Under H0 (true SR = 0, iid normal returns) the SR estimator has per-period
    standard deviation 1/sqrt(T). This is the smallest defensible trial
    dispersion: even an entirely worthless family of trials shows this much
    spread in measured Sharpes from estimation error alone.

    Mirror of `dsr.sampling_noise_floor_sr` at the repo root.
    """
    if n_obs < 2:
        raise ValueError(f"n_obs must be >= 2 to define a sampling floor, got {n_obs}")
    return math.sqrt(periods_per_year / float(n_obs))


def estimate_std_sr_trials(
    sharpes: Sequence[float],
    periods_per_year: int = TRADING_DAYS,
    n_obs: Optional[int] = None,
    apply_floor: bool = True,
) -> float:
    """
    Estimate the trial-Sharpe dispersion from the Sharpes observed in a family.

    WHY THE OBSERVED DISPERSION IS THE RIGHT QUANTITY
    -------------------------------------------------
    E[max SR] is the expected maximum of `n_trials` draws from the distribution
    of the trials you actually ran. That spread has two components, and the
    benchmark needs both:
      1. estimation noise — each Sharpe is measured with error
         ~ sqrt(periods_per_year / T), present even if every trial is worthless;
      2. genuine heterogeneity — a grid over lookbacks, thresholds and
         instruments spans real differences in true Sharpe.
    A fixed constant captures neither and (for any backtest longer than a year)
    grossly over-deflates. The empirical sd of the trial Sharpes captures both.

    WHY THE FLOOR IS A GUARD-RAIL
    -----------------------------
    The observed sd is itself an estimate and is biased DOWNWARDS exactly when
    it matters: few trials, survivorship-clipped families where losing variants
    were never written down, or near-degenerate grids. Each of those
    under-deflates and yields FALSE POSITIVES — the expensive error for a
    research gate. Clamping at sqrt(periods_per_year / T) forbids the estimator
    from claiming the trials cluster more tightly than measurement error allows.

    Mirror of `dsr.estimate_std_sr_trials` at the repo root.

    Args:
        sharpes:          Annualised Sharpes of the family's trials (incl. winner).
        periods_per_year: Annualisation factor matching `sharpes`.
        n_obs:            Backtest length T; required when `apply_floor` is True.
        apply_floor:      Clamp at the sampling-noise floor.

    Returns:
        Estimated annualised std-dev of the trial Sharpe distribution.
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
    return max(observed, sampling_noise_floor_sr(n_obs, periods_per_year))


def compute_sharpe_stats(returns: pd.Series) -> dict:
    """
    Compute Sharpe, skewness, kurtosis, and observation count from a return series.

    Parameters
    ----------
    returns : pd.Series
        Daily P&L or log-return series. NaNs are dropped.

    Returns
    -------
    dict
        sharpe       : float — annualised Sharpe (sqrt(252) annualisation)
        skewness     : float — sample skewness (third standardised moment)
        kurtosis     : float — raw kurtosis (= excess kurtosis + 3; normal = 3.0)
        n_observations: int  — number of valid daily observations
    """
    r = returns.dropna()
    n = len(r)
    if n < 10 or r.std() == 0:
        return {
            "sharpe": np.nan,
            "skewness": np.nan,
            "kurtosis": np.nan,
            "n_observations": n,
        }
    sharpe = float((r.mean() / r.std()) * math.sqrt(TRADING_DAYS))
    skew = float(r.skew())          # pandas: sample skewness
    excess_kurt = float(r.kurt())   # pandas: excess kurtosis (normal = 0)
    raw_kurtosis = excess_kurt + 3.0  # Bailey-LdP formula uses raw kurtosis (normal = 3)
    return {
        "sharpe": sharpe,
        "skewness": skew,
        "kurtosis": raw_kurtosis,
        "n_observations": n,
    }


def deflated_sharpe_ratio(
    sharpe_observed: float,
    n_observations: int,
    skewness: float,
    kurtosis: float,
    n_trials: int = 1,
    std_sr_trials: Optional[float] = None,
) -> dict:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014, JPM).

    Corrects the observed Sharpe for (1) non-normality of returns and
    (2) selection bias from testing multiple strategies (n_trials > 1).

    The correction uses the formula from equations (3) and (8) of the paper:
    "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest
    Overfitting, and Non-Normality" (Bailey & Lopez de Prado, JPM 2014).

    Parameters
    ----------
    sharpe_observed : float
        Observed annualised Sharpe ratio (sqrt(252) convention).
    n_observations : int
        Number of daily return observations (T in the paper — NOT years).
    skewness : float
        Sample skewness γ̃₁ of the daily return series.
    kurtosis : float
        Raw (not excess) kurtosis γ̃₂ of the daily return series.
        For scipy.stats.kurtosis (which returns excess), add 3.
        For a normal distribution, raw kurtosis = 3.
    n_trials : int
        Number of independent strategies tested (AMTP / selection-bias angle).
        Use the project's current n_tests counter. Default: 1 (no correction).
    std_sr_trials : float, optional
        ANNUALISED std-dev of the Sharpe distribution across the tried
        strategies. If None (default), the sampling-noise value implied by the
        SR estimator's own standard error is used — the paper's null hypothesis,
        and the historical behaviour of this module. Supply the empirical
        dispersion via `estimate_std_sr_trials` when the trial family was
        genuinely heterogeneous, since the noise value is a LOWER bound and
        therefore under-deflates in that case.

    Returns
    -------
    dict
        sharpe_threshold     : float — SR cutoff adjusted for n_trials (annualised)
        psr                  : float — Probabilistic SR (non-normality only, n_trials=1)
        dsr                  : float — Deflated SR (PSR corrected for n_trials)
        std_sr_trials        : float — annualised trial dispersion actually used
        std_sr_trials_source : str   — 'declared' or 'sampling_noise'
        verdict              : str   — 'PASS' if DSR > 0.95, else 'FAIL'
    """
    if n_observations < 2:
        return {
            "sharpe_threshold": np.nan,
            "psr": np.nan,
            "dsr": np.nan,
            "std_sr_trials": np.nan,
            "std_sr_trials_source": "undefined",
            "verdict": "FAIL",
        }

    if std_sr_trials is not None:
        std_sr_trials = float(std_sr_trials)
        if not (std_sr_trials > 0.0) or not math.isfinite(std_sr_trials):
            raise ValueError(
                f"std_sr_trials must be a finite positive annualised Sharpe std-dev, "
                f"got {std_sr_trials!r}"
            )

    # Work in per-period (daily) scale for the Bailey-LdP formulas
    sr_per = sharpe_observed / math.sqrt(TRADING_DAYS)

    # Variance of SR estimator: σ²(SR̂) = [1 - γ₁×SR + (γ₂-1)/4 × SR²] / (T-1)
    # (Bailey-LdP 2014, eq. 3). Uses raw kurtosis (γ₂); normal case: γ₁=0, γ₂=3 → 1 + SR²/2.
    inner = (
        1.0
        - skewness * sr_per
        + (kurtosis - 1.0) / 4.0 * sr_per ** 2
    )
    # Guard against degenerate distributions
    inner = max(inner, 1e-8)
    se_sr_per = math.sqrt(inner / (n_observations - 1))

    # PSR: P(true SR > 0) — non-normality correction only (no multiple-testing)
    z_psr = (sr_per - 0.0) / se_sr_per
    psr = float(scipy_stats.norm.cdf(z_psr))

    # Trial dispersion, in PER-PERIOD Sharpe units to match sr_per / se_sr_per.
    # Default = se_sr_per, the SR estimator's own standard error: this is the
    # dispersion implied by the paper's null (all trials truly worthless) and it
    # scales like 1/sqrt(T), so it self-corrects with backtest length. An
    # explicit std_sr_trials arrives ANNUALISED and is de-annualised here.
    if std_sr_trials is None:
        std_sr_per = se_sr_per
        std_sr_source = "sampling_noise"
    else:
        std_sr_per = std_sr_trials / math.sqrt(TRADING_DAYS)
        std_sr_source = "declared"

    # SR threshold: expected maximum Sharpe from n_trials IID random strategies
    # (Bailey-LdP 2014, eq. 8 — expected max of n standard normals, Euler-Mascheroni approx)
    if n_trials <= 1:
        sr_threshold_per = 0.0
    else:
        # E[max of n IID N(0,1)] ≈ (1-γ)×Φ⁻¹(1-1/n) + γ×Φ⁻¹(1-1/(n×e))
        z1 = scipy_stats.norm.ppf(1.0 - 1.0 / n_trials)
        z2 = scipy_stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
        e_max_std_normal = (1.0 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2
        # Scale to SR units
        sr_threshold_per = std_sr_per * e_max_std_normal

    # DSR: P(true SR > sr_threshold)
    z_dsr = (sr_per - sr_threshold_per) / se_sr_per
    dsr = float(scipy_stats.norm.cdf(z_dsr))

    # Report threshold in annualised terms for interpretability
    sr_threshold_ann = sr_threshold_per * math.sqrt(TRADING_DAYS)

    return {
        "sharpe_threshold": float(sr_threshold_ann),
        "psr": float(psr),
        "dsr": float(dsr),
        "std_sr_trials": float(std_sr_per * math.sqrt(TRADING_DAYS)),
        "std_sr_trials_source": std_sr_source,
        "verdict": "PASS" if dsr > 0.95 else "FAIL",
    }


if __name__ == "__main__":
    print("=== dsr.py synthetic tests ===")
    rng = np.random.default_rng(7)
    n = 756  # ~3 years of daily returns

    # --- Case 1: High-Sharpe strategy (drift = 0.20%, vol = 1%) ---
    high_sr_rets = pd.Series(0.0020 + 0.010 * rng.standard_normal(n))
    s_high = compute_sharpe_stats(high_sr_rets)
    assert not np.isnan(s_high["sharpe"]), "FAIL: sharpe is NaN for valid series"
    print(f"  compute_sharpe_stats (high SR):")
    print(f"    SR = {s_high['sharpe']:.3f}  skew = {s_high['skewness']:.3f}"
          f"  kurt(raw) = {s_high['kurtosis']:.3f}  n = {s_high['n_observations']}")

    dsr_high_1 = deflated_sharpe_ratio(
        s_high["sharpe"], s_high["n_observations"],
        s_high["skewness"], s_high["kurtosis"],
        n_trials=1,
    )
    print(f"  DSR (high SR, n_trials=1) : PSR={dsr_high_1['psr']:.4f}  "
          f"DSR={dsr_high_1['dsr']:.4f}  threshold={dsr_high_1['sharpe_threshold']:.3f}  "
          f"verdict={dsr_high_1['verdict']}")
    assert dsr_high_1["verdict"] == "PASS", \
        f"FAIL: high-SR strategy (SR≈{s_high['sharpe']:.2f}) should PASS DSR"

    # --- Case 2: High-SR, but with many trials (n_trials=274) ---
    dsr_high_274 = deflated_sharpe_ratio(
        s_high["sharpe"], s_high["n_observations"],
        s_high["skewness"], s_high["kurtosis"],
        n_trials=ALGO_CLAUDE_N_TESTS,
    )
    print(f"  DSR (high SR, n_trials={ALGO_CLAUDE_N_TESTS}) : PSR={dsr_high_274['psr']:.4f}  "
          f"DSR={dsr_high_274['dsr']:.4f}  threshold={dsr_high_274['sharpe_threshold']:.3f}  "
          f"verdict={dsr_high_274['verdict']}")
    # Very high SR should still PASS even with n_trials=274

    # --- Case 3: Low-Sharpe strategy (drift = 0.01%, vol = 1%) with n_trials=274 ---
    low_sr_rets = pd.Series(0.0001 + 0.010 * rng.standard_normal(n))
    s_low = compute_sharpe_stats(low_sr_rets)
    dsr_low = deflated_sharpe_ratio(
        s_low["sharpe"], s_low["n_observations"],
        s_low["skewness"], s_low["kurtosis"],
        n_trials=ALGO_CLAUDE_N_TESTS,
    )
    print(f"  DSR (low SR≈{s_low['sharpe']:.2f}, n_trials={ALGO_CLAUDE_N_TESTS}) : "
          f"DSR={dsr_low['dsr']:.4f}  threshold={dsr_low['sharpe_threshold']:.3f}  "
          f"verdict={dsr_low['verdict']}")
    assert dsr_low["verdict"] == "FAIL", \
        f"FAIL: low-SR strategy should FAIL DSR with {ALGO_CLAUDE_N_TESTS} trials"

    # --- Case 4: SR=0 (pure noise) ---
    zero_sr_rets = pd.Series(0.010 * rng.standard_normal(n))
    s_zero = compute_sharpe_stats(zero_sr_rets)
    dsr_zero = deflated_sharpe_ratio(
        s_zero["sharpe"], s_zero["n_observations"],
        s_zero["skewness"], s_zero["kurtosis"],
        n_trials=1,
    )
    print(f"  DSR (noise SR≈{s_zero['sharpe']:.2f}, n_trials=1) : "
          f"PSR={dsr_zero['psr']:.4f}  DSR={dsr_zero['dsr']:.4f}  "
          f"verdict={dsr_zero['verdict']}")
    assert dsr_zero["psr"] < 0.70, \
        f"FAIL: noise strategy PSR should be near 0.5, got {dsr_zero['psr']:.4f}"

    print("=== dsr.py: ALL PASS ===")
