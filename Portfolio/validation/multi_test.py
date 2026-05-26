"""
Multiple-testing corrections for portfolio-level strategy validation.

Implements:
  - deflated_sharpe(): Bailey-López de Prado (2014) DSR p-value
  - harvey_liu_bhy(): Benjamini-Hochberg-Yekutieli FDR at portfolio level

Relationship to Portfolio/reporting/metrics.py
----------------------------------------------
metrics.compute_psr_dsr() computes DSR as a single-strategy point estimate.
deflated_sharpe() here accepts a non-annualised SR_observed + n_trials and
is the per-path building block for CPCV. Both delegate the SE formula to
_sr_se_per_period() and _expected_max_std_normal() from metrics.py, which
prevents formula drift between the two modules.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import stats as scipy_stats

from Portfolio.reporting.metrics import (
    TRADING_DAYS,
    _expected_max_std_normal,
    _sr_se_per_period,
)


def deflated_sharpe(
    sr_observed: float,
    n_trials: int,
    T: int,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> float:
    """
    Bailey-López de Prado (2014) Deflated Sharpe Ratio p-value.

    Parameters
    ----------
    sr_observed : float
        Non-annualised per-period SR (= mean(r) / std(r) on daily returns).
        De-annualise before passing: sr_daily = sr_annual / sqrt(252).
    n_trials : int
        Total independent strategies tested (selection-bias correction).
        Pass project n_tests counter for honest reporting.
    T : int
        Number of observations used to estimate sr_observed.
    skew : float
        Return distribution skewness (default 0 = Gaussian).
    kurt : float
        Raw kurtosis (NOT excess; Gaussian = 3.0).

    Returns
    -------
    float
        DSR p-value ∈ [0, 1]. DSR > 0.95 → PASS (PROPFIRM_PASS gate).

    Formula
    -------
    SE_SR   = sqrt[(1 − skew×SR + (kurt−1)/4 × SR²) / (T−1)]
    SR*     = SE_SR × E[max of n_trials IID N(0,1)]
    DSR     = Φ[(SR_obs − SR*) / SE_SR]
    """
    se = _sr_se_per_period(sr_observed, skew, kurt, T)
    if se <= 0:
        return 1.0 if sr_observed > 0 else 0.0
    e_max = _expected_max_std_normal(n_trials)
    sr_threshold = se * e_max
    return float(scipy_stats.norm.cdf((sr_observed - sr_threshold) / se))


def harvey_liu_bhy(
    pvalues: Sequence[float],
    alpha: float = 0.05,
) -> dict:
    """
    Apply Benjamini-Hochberg-Yekutieli (BHY) FDR correction at portfolio level.

    BHY is preferred over BH when p-values may be positively correlated —
    the case for CPCV paths that share overlapping data. BHY controls FDR
    under arbitrary dependence at the cost of being more conservative than BH.

    Parameters
    ----------
    pvalues : sequence of float
        One p-value per strategy / path tested.
    alpha : float
        Target false discovery rate (default 5%).

    Returns
    -------
    dict
        {
          "reject"   : np.ndarray[bool] — True = reject H0 at BHY-alpha,
          "qvalues"  : np.ndarray[float] — BHY-adjusted p-values,
          "n_reject" : int,
          "alpha"    : float,
        }
    """
    from statsmodels.stats.multitest import multipletests

    pvals = np.array(pvalues, dtype=float)
    reject, qvalues, _, _ = multipletests(pvals, alpha=alpha, method="fdr_by")
    return {
        "reject": reject,
        "qvalues": qvalues,
        "n_reject": int(reject.sum()),
        "alpha": alpha,
    }
