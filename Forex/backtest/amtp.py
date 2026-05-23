"""
Forex/backtest/amtp.py
======================
Approximate Multiple-Testing Penalty (AMTP) for Sharpe ratio significance.

Uses Benjamini-Hochberg FDR (recommended for financial applications per Harvey,
Liu & Zhu 2016) and Bonferroni as a conservative upper bound.

Note: this is named "AMTP" per project convention (honest about limitations:
it approximates the true multiple-testing adjustment, not a certified DSR).

Public API
----------
bonferroni_t_threshold(n_tests, alpha) -> float
    Bonferroni-corrected t-stat threshold.

bh_t_threshold(n_tests, rank, alpha) -> float
    Benjamini-Hochberg FDR threshold for test at given rank (1 = best test).

sharpe_t_stat(sharpe, n_periods) -> float
    Annualised Sharpe t-stat: SR × sqrt(n_periods).
    n_periods should be in ANNUAL units (e.g., 21 for 21-year backtest).

amtp_summary(sharpe, n_periods, n_tests_total) -> dict
    Full AMTP analysis: Bonferroni/BH thresholds, pass/fail per method.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


# ─────────────────────────────────────────────────────────────────────────────

def bonferroni_t_threshold(n_tests: int, alpha: float = 0.05) -> float:
    """
    Bonferroni-corrected one-tailed t threshold.

    t* = Phi_inv(1 - alpha/n_tests)
    """
    p_adj = alpha / n_tests
    return float(stats.norm.ppf(1 - p_adj))


def bh_t_threshold(n_tests: int, rank: int = 1, alpha: float = 0.05) -> float:
    """
    Benjamini-Hochberg FDR threshold for the test at ``rank`` position.

    When rank=1 (best strategy), equivalent to Bonferroni.
    When k tests survive, rank = k allows more lenient threshold.

    t* = Phi_inv(1 - rank * alpha / n_tests)
    """
    p_adj = rank * alpha / n_tests
    p_adj = max(p_adj, 1e-10)
    return float(stats.norm.ppf(1 - p_adj))


def sharpe_t_stat(sharpe: float, n_periods: float) -> float:
    """
    Annualised Sharpe t-stat = SR × sqrt(n_annual_periods).

    Parameters
    ----------
    sharpe    : annualised Sharpe ratio.
    n_periods : number of ANNUAL periods (e.g., 21 for 21Y backtest).
                If using monthly data, pass n_months / 12.
    """
    return float(sharpe * np.sqrt(n_periods))


def amtp_summary(
    sharpe:        float,
    n_periods:     float,
    n_tests_total: int,
    alpha:         float = 0.05,
    label:         str   = "Strategy",
) -> dict:
    """
    Full AMTP analysis for a single strategy.

    Parameters
    ----------
    sharpe        : annualised Sharpe of the backtest.
    n_periods     : number of ANNUAL periods.
    n_tests_total : total tests run across all strategies (denominator).
    alpha         : FDR target (default 5%).

    Returns
    -------
    dict with keys:
        sharpe, t_stat, n_periods, n_tests_total,
        bonferroni_threshold, bh_threshold_rank1,
        pass_bonferroni, pass_bh_rank1, pass_naive,
        interpretation
    """
    t = sharpe_t_stat(sharpe, n_periods)
    t_bonf = bonferroni_t_threshold(n_tests_total, alpha)
    t_bh   = bh_t_threshold(n_tests_total, rank=1, alpha=alpha)
    t_naive = stats.norm.ppf(1 - alpha)

    interpretation = (
        "STRONG (passes Bonferroni)" if t > t_bonf else
        "MODERATE (passes BH FDR, fails Bonferroni)" if t > t_bh else
        "WEAK (passes naive, fails FDR)" if t > t_naive else
        "FAIL (does not reach significance at any threshold)"
    )

    return {
        "label":                 label,
        "sharpe":                round(sharpe, 3),
        "t_stat":                round(t, 3),
        "n_periods_annual":      round(n_periods, 1),
        "n_tests_total":         n_tests_total,
        "bonferroni_threshold":  round(t_bonf, 3),
        "bh_threshold_rank1":    round(t_bh, 3),
        "naive_threshold":       round(t_naive, 3),
        "pass_bonferroni":       bool(t > t_bonf),
        "pass_bh_rank1":         bool(t > t_bh),
        "pass_naive":            bool(t > t_naive),
        "interpretation":        interpretation,
    }
