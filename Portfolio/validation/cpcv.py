"""
Combinatorial Purged Cross-Validation (CPCV) via skfolio.

Reference: López de Prado, M. (2018). Advances in Financial Machine Learning.
           Chapter 12: Backtesting Through Cross-Validation.

Key design decisions
--------------------
- Uses skfolio.model_selection.CombinatorialPurgedCV (BSD-3, production-grade).
- purge_size defaults to label horizon inferred from returns frequency.
- embargo_pct=0.01 (1% of T) follows LdP AFML ch.7 recommendation.
- n_folds / n_test_folds auto-selected via optimal_folds_number when None.

skfolio split() API note
------------------------
cv.split(X) yields (train_idx: np.ndarray, test_list: list[np.ndarray]).
Each test_list contains n_test_folds arrays (one per test fold in the
combination). We concatenate them into a single test_idx for backtest_fn.
test_idx is sorted but may be non-contiguous (purge gaps between chunks).

Relationship to Portfolio/reporting/metrics.py
----------------------------------------------
This module does NOT compute PSR/DSR itself; those are in multi_test.py.
hac_sharpe_ratio() and to_excess_returns() from metrics.py can be used inside
backtest_fn if callers want HAC-corrected per-path Sharpes.
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np
import pandas as pd

TRADING_DAYS: int = 252


def _infer_purge_size(returns: pd.Series) -> int:
    """Infer purge_size from returns frequency: daily→1, weekly→5, monthly→21."""
    if len(returns) < 2:
        return 1
    gaps = pd.Series(returns.index).diff().dt.days
    median_gap = float(gaps.median())
    if math.isnan(median_gap) or median_gap <= 1.5:
        return 1
    if median_gap <= 5.5:
        return 5
    return 21


def run_cpcv(
    returns: pd.Series | pd.DataFrame,
    backtest_fn: Callable[[np.ndarray, np.ndarray], float],
    n_folds: int | None = None,
    n_test_folds: int | None = None,
    target_n_paths: int = 30,
    target_train_size: int = 252,
    purge_size: int | None = None,
    embargo_pct: float = 0.01,
    verbose: bool = True,
) -> dict:
    """
    Run Combinatorial Purged Cross-Validation on a backtest function.

    Parameters
    ----------
    returns : pd.Series or pd.DataFrame
        Daily return series (total returns, NOT excess). If DataFrame, columns
        are assets; backtest_fn receives the full index arrays.
    backtest_fn : Callable[[train_idx, test_idx], float]
        Accepts two integer-position arrays into ``returns`` and returns the
        out-of-sample Sharpe ratio for that path. Must be self-contained.
        For non-parametric strategies (TSMOM, fixed-parameter), pre-compute
        returns on the full series and slice test_idx inside the fn.
    n_folds : int, optional
        k in CombinatorialPurgedCV(n_folds=k). Auto via optimal_folds_number.
    n_test_folds : int, optional
        p (must be ≥ 2 per skfolio constraint). Auto if None.
    target_n_paths : int
        Minimum paths sought during auto-fold selection (default 30).
    target_train_size : int
        Minimum training observations sought (default 252).
    purge_size : int, optional
        Bars purged at each train/test boundary (= label horizon).
        Inferred from returns frequency if None.
    embargo_pct : float
        Fraction of T added as embargo after each test fold (default 1%).
    verbose : bool
        Print progress to stdout.

    Returns
    -------
    dict
        {
          "sharpes"      : np.ndarray — per-path OOS Sharpe ratios,
          "mean"         : float,
          "std"          : float,
          "median"       : float,
          "ci_5_95"      : tuple[float, float] — 5th/95th percentiles,
          "n_paths"      : int,
          "n_folds"      : int,
          "n_test_folds" : int,
          "purge_size"   : int,
          "embargo_size" : int,
          "config"       : dict,
        }

    Notes
    -----
    - CPCV paths are correlated (each bar appears C(k-1,p-1) times in test sets).
      The per-path Sharpe distribution is NOT IID — use as an overfitting
      diagnostic, not a frequentist CI.
    - L15 (CLAUDE.md): for SR > 1.0 strategies, distribution width matters
      more than the mean. Inspect the full histogram before concluding.
    - Caveat from session deep-research: CPCV should not be applied to
      Strategy C (NQ ORB, ~250 trades/3.5yr) — insufficient sample for
      30+ paths with adequate train size. Apply only to Strategy A (N≥1500).
    """
    from skfolio.model_selection import CombinatorialPurgedCV, optimal_folds_number

    T = len(returns)
    src_for_infer = returns.iloc[:, 0] if isinstance(returns, pd.DataFrame) else returns

    if purge_size is None:
        purge_size = _infer_purge_size(src_for_infer)

    embargo_size = max(1, int(embargo_pct * T))

    if n_folds is None or n_test_folds is None:
        _k, _p = optimal_folds_number(
            n_observations=T,
            target_train_size=target_train_size,
            target_n_test_paths=target_n_paths,
        )
        if n_folds is None:
            n_folds = _k
        if n_test_folds is None:
            n_test_folds = _p

    cv = CombinatorialPurgedCV(
        n_folds=n_folds,
        n_test_folds=n_test_folds,
        purged_size=purge_size,
        embargo_size=embargo_size,
    )

    X_dummy = np.arange(T).reshape(-1, 1)
    splits = list(cv.split(X_dummy))
    n_splits = len(splits)

    sharpes: list[float] = []
    for i, (train_idx, test_list) in enumerate(splits):
        test_idx = np.sort(
            np.concatenate(test_list) if isinstance(test_list, list) else test_list
        )
        if verbose:
            print(
                f"  CPCV {i + 1:>3}/{n_splits} "
                f"train={len(train_idx):>4} test={len(test_idx):>4}",
                end="\r",
                flush=True,
            )
        sr = backtest_fn(train_idx, test_idx)
        sharpes.append(float(sr) if not math.isnan(float(sr)) else 0.0)

    if verbose:
        print(f"  CPCV {n_splits}/{n_splits} complete.{' ' * 20}")

    arr = np.array(sharpes)
    return {
        "sharpes": arr,
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "median": float(np.median(arr)),
        "ci_5_95": (float(np.percentile(arr, 5)), float(np.percentile(arr, 95))),
        "n_paths": len(arr),
        "n_folds": n_folds,
        "n_test_folds": n_test_folds,
        "purge_size": purge_size,
        "embargo_size": embargo_size,
        "config": {
            "T": T,
            "target_n_paths": target_n_paths,
            "target_train_size": target_train_size,
            "embargo_pct": embargo_pct,
        },
    }
