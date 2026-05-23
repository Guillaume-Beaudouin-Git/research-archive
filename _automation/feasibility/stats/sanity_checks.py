"""
Niveau C — Cross-validation sanity checks.
Three checks: adjacent-asset replication, shuffle null (label permutation),
and OOS decade isolation (SR > 0.3 on each decade independently).
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from .backtest_wf import compute_pnl, vol_target_positions, walk_forward_backtest

TRADING_DAYS: int = 252


def _simple_sharpe(pnl: pd.DataFrame) -> float:
    """Portfolio Sharpe from a pnl DataFrame (sum across assets)."""
    port = pnl.sum(axis=1).dropna()
    if len(port) < 10 or port.std() == 0:
        return np.nan
    return float((port.mean() / port.std()) * np.sqrt(TRADING_DAYS))


def adjacent_asset_replication(
    signal_func: Callable[[pd.DataFrame], pd.DataFrame],
    prices_main: pd.DataFrame,
    prices_adjacent: pd.DataFrame,
    cost_per_side: float = 0.00085,
) -> dict:
    """
    Test whether a signal that passes on the main universe also works on an adjacent one.

    Parameters
    ----------
    signal_func : Callable
        Takes prices (date × asset) → signal (same shape). No execution lag pre-applied.
    prices_main : pd.DataFrame
        Primary universe prices (e.g. BTC + ETH + SOL).
    prices_adjacent : pd.DataFrame
        Complementary universe prices (e.g. top-5 altcoins excluding main assets).
    cost_per_side : float
        Transaction cost per side (default 0.085%).

    Returns
    -------
    dict
        sharpe_main, sharpe_adjacent, correlation (OOS P&L), verdict.
        Verdict PASS if sharpe_adjacent > 0.5 and ratio adjacent/main > 0.4.
    """
    MIN_ROWS = 12 * 21 + 5 * 21  # 12-month train + 5 test periods × 21 days

    def run_wf(prices: pd.DataFrame) -> float:
        if len(prices) < MIN_ROWS or prices.shape[1] < 1:
            return np.nan
        try:
            r = walk_forward_backtest(signal_func, prices, cost_per_side=cost_per_side)
            return float(r["aggregate"]["sharpe_mean"])
        except Exception:
            return np.nan

    sharpe_main = run_wf(prices_main)
    sharpe_adjacent = run_wf(prices_adjacent)

    # Correlation between OOS P&L series on the common date index
    corr = np.nan
    try:
        r_main = walk_forward_backtest(signal_func, prices_main, cost_per_side=cost_per_side)
        r_adj = walk_forward_backtest(signal_func, prices_adjacent, cost_per_side=cost_per_side)
        pnl_main = r_main["pnl_oos"].dropna()
        pnl_adj = r_adj["pnl_oos"].dropna()
        common = pnl_main.index.intersection(pnl_adj.index)
        if len(common) > 20:
            corr = float(pnl_main.loc[common].corr(pnl_adj.loc[common]))
    except Exception:
        pass

    verdict = (
        "PASS"
        if (
            not np.isnan(sharpe_adjacent)
            and sharpe_adjacent > 0.5
            and not np.isnan(sharpe_main)
            and sharpe_main > 0
            and sharpe_adjacent / max(abs(sharpe_main), 0.01) > 0.4
        )
        else "FAIL"
    )

    return {
        "sharpe_main": float(sharpe_main) if not np.isnan(sharpe_main) else np.nan,
        "sharpe_adjacent": float(sharpe_adjacent) if not np.isnan(sharpe_adjacent) else np.nan,
        "correlation": float(corr) if not np.isnan(corr) else np.nan,
        "verdict": verdict,
    }


def shuffle_null_test(
    signal_func: Callable[[pd.DataFrame], pd.DataFrame],
    prices: pd.DataFrame,
    n_shuffles: int = 50,
    cost_per_side: float = 0.00085,
) -> dict:
    """
    Permutation test: shuffle signal columns (assets) within each date row and compare Sharpe.

    Destroys cross-sectional ranking while preserving time-series structure.
    A genuine cross-sectional signal should have sharpe_real >> shuffled distribution.

    Parameters
    ----------
    signal_func : Callable
        Takes prices → signal (same shape). No execution lag pre-applied.
    prices : pd.DataFrame
        date × asset closing prices.
    n_shuffles : int
        Number of column-permutation shuffles (default 50).
    cost_per_side : float
        Transaction cost per side.

    Returns
    -------
    dict
        sharpe_real, sharpe_shuffle_mean, sharpe_shuffle_std,
        percentile_real (fraction of shuffled < real), verdict.
        Verdict PASS if percentile_real > 0.95.
    """
    # Compute real signal once (full sample)
    signal_real = signal_func(prices)
    pos_real = vol_target_positions(signal_real, prices)
    pnl_real = compute_pnl(pos_real, prices, cost_per_side=cost_per_side)
    sharpe_real = _simple_sharpe(pnl_real)

    shuffled_sharpes: list[float] = []
    for seed in range(n_shuffles):
        rng_s = np.random.default_rng(seed + 1000)
        sig_shuffled = signal_real.copy().values  # (n_dates, n_assets)
        for row_idx in range(sig_shuffled.shape[0]):
            row = sig_shuffled[row_idx]
            non_nan = ~np.isnan(row)
            if non_nan.sum() > 1:
                perm = row[non_nan].copy()
                rng_s.shuffle(perm)
                sig_shuffled[row_idx, non_nan] = perm

        sig_shuf_df = pd.DataFrame(sig_shuffled, index=signal_real.index, columns=signal_real.columns)
        pos_s = vol_target_positions(sig_shuf_df, prices)
        pnl_s = compute_pnl(pos_s, prices, cost_per_side=cost_per_side)
        sr_s = _simple_sharpe(pnl_s)
        if not np.isnan(sr_s):
            shuffled_sharpes.append(sr_s)

    if not shuffled_sharpes:
        return {
            "sharpe_real": float(sharpe_real),
            "sharpe_shuffle_mean": np.nan,
            "sharpe_shuffle_std": np.nan,
            "percentile_real": np.nan,
            "verdict": "FAIL",
        }

    percentile = float(np.mean([sharpe_real > s for s in shuffled_sharpes]))
    return {
        "sharpe_real": float(sharpe_real) if not np.isnan(sharpe_real) else np.nan,
        "sharpe_shuffle_mean": float(np.mean(shuffled_sharpes)),
        "sharpe_shuffle_std": float(np.std(shuffled_sharpes)),
        "percentile_real": percentile,
        "verdict": "PASS" if percentile > 0.95 else "FAIL",
    }


def oos_decade_check(
    signal_func: Callable[[pd.DataFrame], pd.DataFrame],
    prices: pd.DataFrame,
    cutoff_date: str,
    cost_per_side: float = 0.00085,
) -> dict:
    """
    Test whether the strategy holds up across distinct market regimes (pre / post cutoff).

    Runs a walk-forward (or simple split) backtest on each sub-period independently.
    Verdict PASS if sharpe > 0.3 on BOTH periods.

    Parameters
    ----------
    signal_func : Callable
        Takes prices → signal.
    prices : pd.DataFrame
        Full price history (date × asset).
    cutoff_date : str
        ISO date string splitting pre- and post-regime periods (e.g. '2023-01-01').
    cost_per_side : float
        Transaction cost per side.

    Returns
    -------
    dict
        sharpe_pre, sharpe_post, cutoff_date, verdict.
    """
    cutoff = pd.Timestamp(cutoff_date)
    prices_pre = prices.loc[prices.index < cutoff]
    prices_post = prices.loc[prices.index >= cutoff]

    def run_sub(p: pd.DataFrame) -> float:
        if len(p) < 60:
            return np.nan
        # Adaptive folds: try WF first; fall back to simple 70/30 split
        min_train = 12 * 21
        remaining = len(p) - min_train
        n_folds = max(2, min(5, remaining // (3 * 21)))
        if remaining >= n_folds * 20:
            try:
                r = walk_forward_backtest(
                    signal_func, p, n_folds=n_folds, cost_per_side=cost_per_side
                )
                return float(r["aggregate"]["sharpe_mean"])
            except Exception:
                pass
        # Simple split fallback
        n = len(p)
        split = int(0.6 * n)
        sig = signal_func(p)
        pos = vol_target_positions(sig.iloc[split:], p.iloc[split:])
        pnl = compute_pnl(pos, p.iloc[split:], cost_per_side=cost_per_side)
        return _simple_sharpe(pnl)

    sharpe_pre = run_sub(prices_pre)
    sharpe_post = run_sub(prices_post)

    verdict = (
        "PASS"
        if (
            not np.isnan(sharpe_pre)
            and not np.isnan(sharpe_post)
            and sharpe_pre > 0.3
            and sharpe_post > 0.3
        )
        else "FAIL"
    )

    return {
        "sharpe_pre": float(sharpe_pre) if not np.isnan(sharpe_pre) else np.nan,
        "sharpe_post": float(sharpe_post) if not np.isnan(sharpe_post) else np.nan,
        "cutoff_date": cutoff_date,
        "verdict": verdict,
    }
