"""
Forex/backtest/walk_forward.py
================================
Expanding-window walk-forward validation with configurable fold splits.

wf_splits(index, n_folds, min_is_years) -> list[tuple[slice, slice]]
    Generate IS/OOS slices for expanding-window WF.

wf_run(signal, returns, backtest_fn, n_folds, min_is_years) -> pd.DataFrame
    Run backtest_fn on each WF fold, collect per-fold metrics.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd


def wf_splits(
    index:         pd.DatetimeIndex,
    n_folds:       int   = 5,
    min_is_years:  float = 5.0,
    oos_months:    int   = 18,
) -> list[tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """
    Expanding-window IS/OOS splits for walk-forward validation.

    Parameters
    ----------
    index         : full time series DatetimeIndex.
    n_folds       : number of folds (minimum 5 per project rules).
    min_is_years  : minimum IS period for first fold.
    oos_months    : OOS window per fold in months.

    Returns
    -------
    list of (is_index, oos_index) pairs.
    """
    total_months = len(index)
    min_is = int(min_is_years * 12)

    # Ensure we have enough data
    needed = min_is + n_folds * oos_months
    if total_months < needed:
        raise ValueError(
            f"Insufficient data: {total_months} months, need {needed} "
            f"for {n_folds} folds with {min_is_years:.0f}Y IS + {oos_months}M OOS each."
        )

    splits = []
    for fold in range(n_folds):
        is_end   = min_is + fold * oos_months
        oos_end  = is_end + oos_months
        oos_end  = min(oos_end, total_months)
        splits.append((index[:is_end], index[is_end:oos_end]))
        if oos_end >= total_months:
            break

    return splits


def wf_run(
    signal:       pd.DataFrame,
    returns:      pd.DataFrame,
    backtest_fn:  Callable[[pd.DataFrame, pd.DataFrame], dict[str, Any]],
    n_folds:      int   = 5,
    min_is_years: float = 5.0,
    oos_months:   int   = 18,
) -> pd.DataFrame:
    """
    Walk-forward backtest loop.

    For each fold:
      - IS: train / parameter calibration (backtest_fn returns metrics dict)
      - OOS: out-of-sample evaluation (same backtest_fn)
      - Record IS and OOS metrics per fold

    Parameters
    ----------
    signal, returns : full (T × N) DataFrames aligned.
    backtest_fn     : callable(signal_slice, returns_slice) → metrics dict.

    Returns
    -------
    pd.DataFrame : one row per fold, columns = IS/OOS metrics.
    """
    idx    = signal.index.intersection(returns.index)
    splits = wf_splits(pd.DatetimeIndex(idx), n_folds, min_is_years, oos_months)

    rows = []
    for i, (is_idx, oos_idx) in enumerate(splits):
        row = {"fold": i + 1,
               "is_start": is_idx[0], "is_end": is_idx[-1],
               "oos_start": oos_idx[0] if len(oos_idx) else None,
               "oos_end":   oos_idx[-1] if len(oos_idx) else None}

        is_metrics  = backtest_fn(signal.loc[is_idx],  returns.loc[is_idx])
        oos_metrics = backtest_fn(signal.loc[oos_idx], returns.loc[oos_idx]) if len(oos_idx) else {}

        row.update({f"is_{k}":  v for k, v in is_metrics.items()})
        row.update({f"oos_{k}": v for k, v in oos_metrics.items()})
        rows.append(row)

    return pd.DataFrame(rows)
