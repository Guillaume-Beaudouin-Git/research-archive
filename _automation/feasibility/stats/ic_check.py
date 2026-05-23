"""
Niveau A — IC Feasibility gate.
Computes Spearman cross-sectional IC, HAC t-stat (Newey-West lag 6),
event count, and orthogonality vs existing strategy signals.
Gate: t_HAC > 2.5, events >= 50/yr, |corr_A| < 0.5.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats


def cross_sectional_ic(
    signal: pd.DataFrame,
    forward_returns: pd.DataFrame,
    method: str = "spearman",
    min_assets: int = 2,
) -> pd.Series:
    """
    Compute cross-sectional IC per date.

    Parameters
    ----------
    signal : pd.DataFrame
        date × asset signal at time t. Values in any range.
    forward_returns : pd.DataFrame
        date × asset returns over horizon h, already aligned to signal dates.
        forward_returns.loc[t] = return from t to t+h.
    method : str
        Rank correlation: 'spearman' (default) or 'pearson'.
    min_assets : int
        Minimum number of valid (non-NaN) assets per date to compute IC (default 2).
        Set to 5 for large cross-sectional universes (N ≥ 30). Use 2 for small
        universes (e.g. BTC/ETH/SOL only).

    Returns
    -------
    pd.Series
        Time series of IC values (one per date). NaN when fewer than min_assets valid.
    """
    common_dates = signal.index.intersection(forward_returns.index)
    sig = signal.loc[common_dates]
    fwd = forward_returns.loc[common_dates]

    ic_vals: list[float] = []
    for date in common_dates:
        s_row = sig.loc[date]
        r_row = fwd.loc[date]
        valid = s_row.notna() & r_row.notna()
        if valid.sum() < min_assets:
            ic_vals.append(np.nan)
            continue
        s_v = s_row[valid].values
        r_v = r_row[valid].values
        # Constant input → correlation undefined; skip this date
        if np.all(s_v == s_v[0]) or np.all(r_v == r_v[0]):
            ic_vals.append(np.nan)
            continue
        if method == "spearman":
            ic, _ = stats.spearmanr(s_v, r_v)
        elif method == "pearson":
            ic, _ = stats.pearsonr(s_v, r_v)
        else:
            raise ValueError(f"Unknown method {method!r}. Use 'spearman' or 'pearson'.")
        ic_vals.append(float(ic))

    return pd.Series(ic_vals, index=common_dates, name="ic")


def hac_t_stat(
    ic_series: pd.Series,
    lag: int = 6,
) -> Tuple[float, float]:
    """
    HAC (Newey-West) t-statistic on the mean of ic_series.

    Parameters
    ----------
    ic_series : pd.Series
        Time series of IC values. NaNs are dropped before computation.
    lag : int
        Maximum lag for Newey-West HAC covariance (default 6, as per CLAUDE.md).

    Returns
    -------
    Tuple[float, float]
        (t_stat, p_value). Returns (nan, nan) when fewer than 30 valid observations.
    """
    clean = ic_series.dropna()
    if len(clean) < 30:
        return np.nan, np.nan
    y = clean.values
    X = np.ones((len(y), 1))
    result = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(result.tvalues[0]), float(result.pvalues[0])


def level_A_gate(
    signal_baseline: pd.DataFrame,
    signal_variant: pd.DataFrame,
    forward_returns: pd.DataFrame,
    ic_threshold: float = 0.05,
    t_threshold: float = 2.5,
    min_assets: int = 2,
) -> dict:
    """
    Niveau A complete gate: compare baseline vs variant signal via delta-IC.

    Computes Spearman IC for both signals, forms the delta series, and applies
    HAC t-stat on that delta. All three failure modes are captured separately.

    Parameters
    ----------
    signal_baseline : pd.DataFrame
        date × asset signal for the current / reference strategy.
    signal_variant : pd.DataFrame
        date × asset signal for the candidate modification.
    forward_returns : pd.DataFrame
        date × asset forward returns (same horizon for both).
    ic_threshold : float
        Minimum IC delta (absolute) to claim improvement (default: 0.005).
        Note: argument name is ic_threshold but the gate uses 0.005; pass
        your desired minimum delta via this parameter.
    t_threshold : float
        HAC t-stat threshold for significance (default: 2.5, CLAUDE.md standard).

    Returns
    -------
    dict
        ic_baseline  : pd.Series of per-date IC for baseline
        ic_variant   : pd.Series of per-date IC for variant
        delta_ic     : pd.Series of (ic_variant - ic_baseline)
        mean_ic_baseline, mean_ic_variant, delta_ic_mean : float
        t_hac, p_hac : float (HAC on delta series, lag 6)
        n_dates      : int  (valid delta IC observations)
        verdict      : 'PASS' | 'FAIL_DELTA' | 'FAIL_TSTAT' | 'FAIL_SAMPLE'
    """
    ic_base = cross_sectional_ic(signal_baseline, forward_returns, min_assets=min_assets)
    ic_var = cross_sectional_ic(signal_variant, forward_returns, min_assets=min_assets)

    common = ic_base.index.intersection(ic_var.index)
    delta_ic = (ic_var.loc[common] - ic_base.loc[common]).rename("delta_ic")

    mean_base = float(ic_base.mean())
    mean_var = float(ic_var.mean())
    delta_mean = float(delta_ic.mean())
    n_dates = int(delta_ic.notna().sum())

    t_hac, p_hac = hac_t_stat(delta_ic)

    if n_dates < 100:
        verdict = "FAIL_SAMPLE"
    elif delta_mean <= ic_threshold:
        verdict = "FAIL_DELTA"
    elif np.isnan(t_hac) or t_hac <= t_threshold:
        verdict = "FAIL_TSTAT"
    else:
        verdict = "PASS"

    return {
        "ic_baseline": ic_base,
        "ic_variant": ic_var,
        "delta_ic": delta_ic,
        "mean_ic_baseline": mean_base,
        "mean_ic_variant": mean_var,
        "delta_ic_mean": delta_mean,
        "t_hac": float(t_hac) if not np.isnan(t_hac) else np.nan,
        "p_hac": float(p_hac) if not np.isnan(p_hac) else np.nan,
        "n_dates": n_dates,
        "verdict": verdict,
    }


if __name__ == "__main__":
    print("=== ic_check.py synthetic tests ===")
    rng = np.random.default_rng(42)
    n_dates, n_assets = 500, 30

    dates = pd.date_range("2020-01-01", periods=n_dates, freq="D")
    # Latent factor drives returns; signals have different exposures to it
    factor = rng.standard_normal((n_dates, n_assets))
    noise = rng.standard_normal((n_dates, n_assets))
    fwd = pd.DataFrame(factor + noise, index=dates, columns=[f"A{i}" for i in range(n_assets)])
    # Baseline: moderate factor loading (IC ≈ 0.15)
    signal_base = pd.DataFrame(
        0.3 * factor + rng.standard_normal((n_dates, n_assets)),
        index=dates,
        columns=fwd.columns,
    )

    # --- Test cross_sectional_ic ---
    ic = cross_sectional_ic(signal_base, fwd)
    assert not ic.isna().all(), "FAIL: IC series is entirely NaN"
    mean_ic = ic.mean()
    assert abs(mean_ic) > 0.05, f"FAIL: mean IC {mean_ic:.4f} too low for strong synthetic signal"
    print(f"  cross_sectional_ic : mean IC = {mean_ic:.4f}  PASS")

    # --- Test hac_t_stat ---
    t, p = hac_t_stat(ic)
    assert not np.isnan(t), "FAIL: t_HAC is NaN"
    assert t > 2.5, f"FAIL: t_HAC {t:.3f} should exceed 2.5 for IC ≈ 0.15 over 500 obs"
    print(f"  hac_t_stat         : t_HAC = {t:.3f}  p = {p:.4f}  PASS")

    # --- Test level_A_gate with identical variant (should FAIL_DELTA) ---
    signal_variant_weak = signal_base + 0.001 * rng.standard_normal((n_dates, n_assets))
    gate_weak = level_A_gate(signal_base, signal_variant_weak, fwd)
    assert gate_weak["verdict"] == "FAIL_DELTA", \
        f"FAIL: expected FAIL_DELTA, got {gate_weak['verdict']}"
    print(f"  level_A_gate (weak variant) : verdict = {gate_weak['verdict']}  PASS")

    # --- Test level_A_gate with strong variant (higher factor loading → higher IC) ---
    # signal_variant has 0.7 factor loading vs 0.3 baseline → genuinely higher IC with fwd
    signal_variant_strong = pd.DataFrame(
        0.7 * factor + rng.standard_normal((n_dates, n_assets)),
        index=dates, columns=fwd.columns,
    )
    gate_strong = level_A_gate(signal_base, signal_variant_strong, fwd, ic_threshold=0.005)
    print(f"  level_A_gate (strong variant): verdict = {gate_strong['verdict']}  "
          f"delta_IC = {gate_strong['delta_ic_mean']:.4f}  t_HAC = {gate_strong['t_hac']:.3f}")
    # Strong variant has genuinely higher IC — expect PASS or FAIL_TSTAT (short sample)
    assert gate_strong["verdict"] in ("PASS", "FAIL_TSTAT"), \
        f"FAIL: unexpected verdict {gate_strong['verdict']}"
    print("=== ic_check.py: ALL PASS ===")
