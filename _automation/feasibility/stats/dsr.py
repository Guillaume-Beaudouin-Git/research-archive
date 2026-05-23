"""
Niveau B — Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014).
Adjusts observed Sharpe for skewness, kurtosis, and number of independent trials
to produce a probability that the true Sharpe exceeds zero.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

TRADING_DAYS: int = 252
EULER_MASCHERONI: float = 0.5772156649015329
# Current n_tests for Algo_claude project — override per session as needed
ALGO_CLAUDE_N_TESTS: int = 274


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

    Returns
    -------
    dict
        sharpe_threshold  : float — SR cutoff adjusted for n_trials (annualised)
        psr               : float — Probabilistic SR (non-normality only, n_trials=1)
        dsr               : float — Deflated SR (PSR corrected for n_trials)
        verdict           : str   — 'PASS' if DSR > 0.95, else 'FAIL'
    """
    if n_observations < 2:
        return {"sharpe_threshold": np.nan, "psr": np.nan, "dsr": np.nan, "verdict": "FAIL"}

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
        sr_threshold_per = se_sr_per * e_max_std_normal

    # DSR: P(true SR > sr_threshold)
    z_dsr = (sr_per - sr_threshold_per) / se_sr_per
    dsr = float(scipy_stats.norm.cdf(z_dsr))

    # Report threshold in annualised terms for interpretability
    sr_threshold_ann = sr_threshold_per * math.sqrt(TRADING_DAYS)

    return {
        "sharpe_threshold": float(sr_threshold_ann),
        "psr": float(psr),
        "dsr": float(dsr),
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
