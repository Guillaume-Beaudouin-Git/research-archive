"""
Niveau B — Politis-Romano stationary block bootstrap for serially-correlated P&L.
Block length auto-calibrated via Patton-Politis-White (2009) optimal block length.
Outputs bootstrap p-value for H0: Sharpe <= 0.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

TRADING_DAYS: int = 252


def optimal_block_length_ppw(returns: pd.Series) -> int:
    """
    Patton-Politis-White (2009) optimal block length for stationary bootstrap.

    Attempts to use `arch.bootstrap.optimal_block_length` (PPW exact formula).
    Falls back to the closed-form approximation b* ≈ 1.75 × n^(1/3) × |ρ₁|^(2/3)
    when `arch` is unavailable.

    Parameters
    ----------
    returns : pd.Series
        Daily return or P&L series. NaNs are dropped before estimation.

    Returns
    -------
    int
        Optimal mean block length for stationary bootstrap. Minimum 1.
    """
    r = returns.dropna()
    values = r.values

    try:
        from arch.bootstrap import optimal_block_length
        result = optimal_block_length(values)
        # Returns DataFrame with 'stationary' column (Series of length 1)
        bl = float(result["stationary"].iloc[0])
        return max(1, int(round(bl)))
    except Exception:
        pass

    # Closed-form fallback: PPW approximation
    n = len(values)
    if n < 10:
        return 1
    rho1 = float(np.corrcoef(values[:-1], values[1:])[0, 1])
    rho1 = float(np.clip(abs(rho1), 1e-6, 0.99))
    bl = int(round(1.75 * n ** (1 / 3) * rho1 ** (2 / 3)))
    return max(1, bl)


def _stationary_bootstrap_resample(
    values: np.ndarray,
    block_length: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Single stationary bootstrap resample (Politis & Romano 1994).

    Block lengths follow Geometric(1/block_length). Circular wrap ensures
    the resampled series has the same length as the input.
    """
    n = len(values)
    result = np.empty(n)
    p = 1.0 / max(block_length, 1.0)
    i = 0
    while i < n:
        start = rng.integers(0, n)
        geo_len = int(rng.geometric(p))
        for j in range(geo_len):
            if i >= n:
                break
            result[i] = values[(start + j) % n]
            i += 1
    return result


def _annualized_sharpe(values: np.ndarray, trading_days: int = TRADING_DAYS) -> float:
    """Annualised Sharpe ratio from a flat array of daily returns."""
    std = values.std()
    if std == 0 or len(values) == 0:
        return 0.0
    return float((values.mean() / std) * np.sqrt(trading_days))


def stationary_bootstrap_sharpe(
    returns: pd.Series,
    n_resamples: int = 1000,
    block_length: int | None = None,
    random_state: int = 42,
) -> dict:
    """
    Politis-Romano stationary block bootstrap for Sharpe ratio significance.

    Builds a bootstrap distribution of the Sharpe ratio to test H0: SR ≤ 0.
    The stationary bootstrap (vs circular) ensures the resampled series is
    also (weakly) stationary, preserving serial-correlation structure.

    Parameters
    ----------
    returns : pd.Series
        Daily return or P&L series. NaNs are dropped.
    n_resamples : int
        Number of bootstrap resamples (default: 1000).
    block_length : int or None
        Mean geometric block length. If None, auto-calibrated via PPW (default).
    random_state : int
        Seed for reproducibility (default: 42).

    Returns
    -------
    dict
        sharpe_observed      : float — original Sharpe ratio
        sharpe_bootstrap_mean: float
        sharpe_bootstrap_std : float
        sharpe_ci_95         : Tuple[float, float] — (2.5th, 97.5th percentiles)
        p_value_sharpe_le_zero: float — P(SR ≤ 0) under bootstrap distribution
        block_length_used    : int
    """
    r = returns.dropna()
    values = r.values
    sharpe_obs = _annualized_sharpe(values)

    if block_length is None:
        block_length = optimal_block_length_ppw(r)

    rng = np.random.default_rng(random_state)
    boot_sharpes = np.array([
        _annualized_sharpe(_stationary_bootstrap_resample(values, float(block_length), rng))
        for _ in range(n_resamples)
    ])

    return {
        "sharpe_observed": float(sharpe_obs),
        "sharpe_bootstrap_mean": float(boot_sharpes.mean()),
        "sharpe_bootstrap_std": float(boot_sharpes.std()),
        "sharpe_ci_95": (
            float(np.percentile(boot_sharpes, 2.5)),
            float(np.percentile(boot_sharpes, 97.5)),
        ),
        "p_value_sharpe_le_zero": float(np.mean(boot_sharpes <= 0.0)),
        "block_length_used": int(block_length),
    }


def bootstrap_pnl_difference(
    pnl_baseline: pd.Series,
    pnl_variant: pd.Series,
    n_resamples: int = 1000,
) -> dict:
    """
    Block bootstrap on paired P&L to test whether variant Sharpe > baseline Sharpe.

    Resamples the SAME indices for both series to preserve their cross-correlation,
    then computes Sharpe(variant) - Sharpe(baseline) on each resample.

    Parameters
    ----------
    pnl_baseline : pd.Series
        Daily P&L for the baseline strategy.
    pnl_variant : pd.Series
        Daily P&L for the variant strategy.
    n_resamples : int
        Number of bootstrap resamples (default: 1000).

    Returns
    -------
    dict
        delta_sharpe_observed: float — SR(variant) - SR(baseline) on original data
        delta_sharpe_ci_95   : Tuple[float, float] — 95% bootstrap CI
        p_value_le_zero      : float — P(delta_SR ≤ 0) under bootstrap
    """
    common = pnl_baseline.index.intersection(pnl_variant.index)
    base_vals = pnl_baseline.reindex(common).dropna().values
    var_vals = pnl_variant.reindex(common).dropna().values
    min_len = min(len(base_vals), len(var_vals))
    base_vals = base_vals[:min_len]
    var_vals = var_vals[:min_len]

    delta_obs = _annualized_sharpe(var_vals) - _annualized_sharpe(base_vals)

    # Block length calibrated on the difference series (captures joint autocorrelation)
    diff_series = pd.Series(var_vals - base_vals)
    bl = float(optimal_block_length_ppw(diff_series))
    rng = np.random.default_rng(42)

    boot_deltas = np.empty(n_resamples)
    p_geom = 1.0 / max(bl, 1.0)
    for k in range(n_resamples):
        # Build shared index array for paired resample
        n = min_len
        indices = np.empty(n, dtype=np.intp)
        i = 0
        while i < n:
            start = rng.integers(0, n)
            geo_len = int(rng.geometric(p_geom))
            for j in range(geo_len):
                if i >= n:
                    break
                indices[i] = (start + j) % n
                i += 1
        boot_base = base_vals[indices]
        boot_var = var_vals[indices]
        boot_deltas[k] = _annualized_sharpe(boot_var) - _annualized_sharpe(boot_base)

    return {
        "delta_sharpe_observed": float(delta_obs),
        "delta_sharpe_ci_95": (
            float(np.percentile(boot_deltas, 2.5)),
            float(np.percentile(boot_deltas, 97.5)),
        ),
        "p_value_le_zero": float(np.mean(boot_deltas <= 0.0)),
    }


if __name__ == "__main__":
    print("=== bootstrap.py synthetic tests ===")
    rng_data = np.random.default_rng(99)
    n = 600
    dates = pd.date_range("2021-01-01", periods=n, freq="B")

    # Positive-drift strategy (Sharpe ≈ 1.5)
    pos_returns = pd.Series(
        0.0006 + 0.01 * rng_data.standard_normal(n), index=dates
    )
    # Null strategy (Sharpe ≈ 0)
    null_returns = pd.Series(
        0.00 + 0.01 * rng_data.standard_normal(n), index=dates
    )

    # --- optimal_block_length_ppw ---
    bl = optimal_block_length_ppw(pos_returns)
    assert isinstance(bl, int) and bl >= 1, f"FAIL: invalid block length {bl}"
    print(f"  optimal_block_length_ppw : block_length = {bl}  PASS")

    # --- stationary_bootstrap_sharpe on positive drift ---
    res_pos = stationary_bootstrap_sharpe(pos_returns, n_resamples=500, random_state=42)
    assert 0.0 <= res_pos["p_value_sharpe_le_zero"] <= 1.0, "FAIL: p-value out of [0, 1]"
    assert res_pos["sharpe_observed"] > 0.5, \
        f"FAIL: expected SR > 0.5 for drift series, got {res_pos['sharpe_observed']:.3f}"
    print(f"  bootstrap (pos drift)    : SR={res_pos['sharpe_observed']:.3f}  "
          f"CI95=[{res_pos['sharpe_ci_95'][0]:.2f}, {res_pos['sharpe_ci_95'][1]:.2f}]  "
          f"p_le0={res_pos['p_value_sharpe_le_zero']:.3f}  PASS")

    # --- stationary_bootstrap_sharpe on null ---
    res_null = stationary_bootstrap_sharpe(null_returns, n_resamples=500, random_state=42)
    print(f"  bootstrap (null)         : SR={res_null['sharpe_observed']:.3f}  "
          f"p_le0={res_null['p_value_sharpe_le_zero']:.3f}  PASS")

    # --- bootstrap_pnl_difference ---
    diff_res = bootstrap_pnl_difference(null_returns, pos_returns, n_resamples=500)
    assert "delta_sharpe_observed" in diff_res
    assert diff_res["delta_sharpe_observed"] > 0.0, \
        "FAIL: pos_returns should have higher Sharpe than null_returns"
    assert 0.0 <= diff_res["p_value_le_zero"] <= 1.0, "FAIL: p-value out of [0, 1]"
    print(f"  bootstrap_pnl_difference : delta_SR={diff_res['delta_sharpe_observed']:.3f}  "
          f"CI95=[{diff_res['delta_sharpe_ci_95'][0]:.2f}, {diff_res['delta_sharpe_ci_95'][1]:.2f}]  "
          f"p_le0={diff_res['p_value_le_zero']:.3f}  PASS")

    print("=== bootstrap.py: ALL PASS ===")
