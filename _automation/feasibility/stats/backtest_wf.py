"""
Niveau B — Event-driven walk-forward backtest with transaction costs.
Expanding window, >= 5 folds, daily vol targeting, excess returns vs cash rate.
Outputs per-fold Sharpe, MaxDD, and aggregate WF positivity ratio.
"""
from __future__ import annotations

from typing import Callable, List, Tuple

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR: int = 252


def vol_target_positions(
    signal: pd.DataFrame,
    prices: pd.DataFrame,
    vol_target_annual: float = 0.10,
    vol_lookback: int = 28,
    vol_scalar_max: float = 3.0,
    vol_scalar_min: float = 0.0,
) -> pd.DataFrame:
    """
    Convert signal to dollar positions with daily vol targeting.

    Parameters
    ----------
    signal : pd.DataFrame
        date × asset raw signal (not yet shifted; values in [0, 1] for long-only).
        Must NOT have an execution-lag shift pre-applied — this function applies it.
    prices : pd.DataFrame
        date × asset closing prices, index aligned with signal.
    vol_target_annual : float
        Target annualised portfolio volatility (default: 10%).
    vol_lookback : int
        Rolling window for realised vol estimation in trading days (default: 28).
    vol_scalar_max : float
        Maximum vol scalar; caps leverage (default: 3.0).
    vol_scalar_min : float
        Minimum vol scalar; 0.0 prevents short side for long-only signals (default: 0.0).

    Returns
    -------
    pd.DataFrame
        date × asset position weights.
        position(t) = signal(t-1) × vol_scalar(t-1) — no look-ahead by construction.
        First `vol_lookback + 1` rows are NaN (insufficient vol history after shift).
    """
    log_returns = np.log(prices / prices.shift(1))
    realized_vol = log_returns.rolling(vol_lookback).std() * np.sqrt(TRADING_DAYS_PER_YEAR)
    vol_scalar = (vol_target_annual / realized_vol).clip(lower=vol_scalar_min, upper=vol_scalar_max)
    # Execution lag: position at t decided using signal and vol from t-1
    positions = signal.shift(1) * vol_scalar.shift(1)
    return positions


def compute_pnl(
    positions: pd.DataFrame,
    prices: pd.DataFrame,
    cost_per_side: float = 0.00085,
) -> pd.DataFrame:
    """
    Daily P&L from positions and prices, with round-trip transaction costs.

    Parameters
    ----------
    positions : pd.DataFrame
        date × asset position weights (output of vol_target_positions).
        Convention: positions(t) = position decided at t, held starting day t+1.
    prices : pd.DataFrame
        date × asset closing prices.
    cost_per_side : float
        Transaction cost per unit of position change, one side (default 0.085%,
        half of the 0.17% crypto round-trip cost from CLAUDE.md).

    Returns
    -------
    pd.DataFrame
        date × asset daily P&L in log-return scale.
        pnl(t) = position(t-1) × log_return(t) - cost_per_side × |position(t) - position(t-1)|
    """
    log_returns = np.log(prices / prices.shift(1))
    # Return: hold position decided on t-1, realised on day t
    pnl_gross = positions.shift(1) * log_returns
    # Cost: rebalance from position(t-1) to position(t) at open of day t
    turnover = positions.diff().abs()
    pnl_net = pnl_gross - cost_per_side * turnover
    return pnl_net


def walk_forward_split(
    dates: pd.DatetimeIndex,
    n_folds: int = 5,
    min_train_months: int = 12,
) -> List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]:
    """
    Expanding-window walk-forward splits.

    Parameters
    ----------
    dates : pd.DatetimeIndex
        Full sorted date index of the dataset.
    n_folds : int
        Number of walk-forward test folds (default: 5, CLAUDE.md minimum).
    min_train_months : int
        Minimum training period in months (default: 12). Assumes 21 trading days/month.

    Returns
    -------
    List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]]
        List of (train_dates, test_dates) tuples. Training set expands at each fold.
        Test windows are roughly equal size, covering the data after min_train.
    """
    n = len(dates)
    min_train_days = min_train_months * 21
    if n <= min_train_days:
        raise ValueError(
            f"Insufficient data: {n} rows < {min_train_days} min training days "
            f"({min_train_months} months × 21)."
        )
    remaining = n - min_train_days
    if remaining < n_folds:
        raise ValueError(
            f"Only {remaining} rows remain after min-train — not enough for {n_folds} folds."
        )
    test_size = remaining // n_folds
    splits: List[Tuple[pd.DatetimeIndex, pd.DatetimeIndex]] = []
    for fold in range(n_folds):
        train_end = min_train_days + fold * test_size
        test_start = train_end
        # Last fold absorbs any remainder
        test_end = n if fold == n_folds - 1 else train_end + test_size
        splits.append((dates[:train_end], dates[test_start:test_end]))
    return splits


def _fold_metrics(pnl: pd.Series) -> dict:
    """Compute Sharpe and MaxDD from a single-fold daily P&L series."""
    r = pnl.dropna()
    if len(r) < 10 or r.std() == 0:
        return {"sharpe": np.nan, "max_dd": np.nan, "n_days": len(r)}
    sharpe = float((r.mean() / r.std()) * np.sqrt(TRADING_DAYS_PER_YEAR))
    equity = (1 + r).cumprod()
    max_dd = float(((equity - equity.cummax()) / equity.cummax()).min())
    return {"sharpe": sharpe, "max_dd": max_dd, "n_days": len(r)}


def walk_forward_backtest(
    signal_func: Callable[[pd.DataFrame], pd.DataFrame],
    prices: pd.DataFrame,
    n_folds: int = 5,
    cost_per_side: float = 0.00085,
    vol_target_annual: float = 0.10,
) -> dict:
    """
    Run expanding-window walk-forward backtest.

    Parameters
    ----------
    signal_func : Callable[[pd.DataFrame], pd.DataFrame]
        Takes prices (date × asset) → signal (same shape, same index).
        Must be deterministic and contain no look-ahead internally.
        Called with prices up to the end of each test fold to avoid forward leakage
        of any fitted parameters (e.g. vol scaling, rolling stats).
    prices : pd.DataFrame
        date × asset closing prices for the full sample.
    n_folds : int
        Number of walk-forward folds (default 5; CLAUDE.md minimum).
    cost_per_side : float
        Transaction cost per side (default 0.085% for crypto).
    vol_target_annual : float
        Target annualised vol for position sizing (default 10%).

    Returns
    -------
    dict
        per_fold : list[dict] — {fold, start, end, sharpe, max_dd, n_days}
        aggregate : dict — {sharpe_mean, sharpe_pct_positive, max_dd_worst, total_return}
        pnl_oos  : pd.Series — concatenated OOS portfolio P&L (daily, log-return scale)
    """
    splits = walk_forward_split(prices.index, n_folds=n_folds)
    per_fold: list[dict] = []
    oos_pieces: list[pd.Series] = []

    for idx, (train_dates, test_dates) in enumerate(splits):
        # Feed only data up to end of test window to prevent any future leakage
        prices_sub = prices.loc[: test_dates[-1]]
        signal_full = signal_func(prices_sub)
        signal_test = signal_full.reindex(test_dates)
        prices_test = prices.reindex(test_dates)

        positions = vol_target_positions(
            signal_test, prices_test, vol_target_annual=vol_target_annual
        )
        pnl_df = compute_pnl(positions, prices_test, cost_per_side=cost_per_side)
        pnl_port = pnl_df.sum(axis=1)  # equal-weighted portfolio across assets

        metrics = _fold_metrics(pnl_port)
        per_fold.append({
            "fold": idx + 1,
            "start": str(test_dates[0].date()),
            "end": str(test_dates[-1].date()),
            **metrics,
        })
        oos_pieces.append(pnl_port)

    pnl_oos = pd.concat(oos_pieces).sort_index()

    valid_sharpes = [f["sharpe"] for f in per_fold if not np.isnan(f.get("sharpe", np.nan))]
    valid_maxdds = [f["max_dd"] for f in per_fold if not np.isnan(f.get("max_dd", np.nan))]
    r_oos = pnl_oos.dropna()
    total_return = float((1 + r_oos).prod() - 1) if len(r_oos) > 0 else np.nan

    return {
        "per_fold": per_fold,
        "aggregate": {
            "sharpe_mean": float(np.mean(valid_sharpes)) if valid_sharpes else np.nan,
            "sharpe_pct_positive": float(np.mean([s > 0 for s in valid_sharpes])) if valid_sharpes else np.nan,
            "max_dd_worst": float(min(valid_maxdds)) if valid_maxdds else np.nan,
            "total_return": total_return,
        },
        "pnl_oos": pnl_oos,
    }


if __name__ == "__main__":
    print("=== backtest_wf.py synthetic tests ===")
    rng = np.random.default_rng(42)
    n_dates, n_assets = 1200, 8

    dates = pd.date_range("2019-01-01", periods=n_dates, freq="B")
    prices = pd.DataFrame(
        np.cumprod(1 + 0.0003 + 0.012 * rng.standard_normal((n_dates, n_assets)), axis=0) * 100,
        index=dates,
        columns=[f"A{i}" for i in range(n_assets)],
    )
    signal = pd.DataFrame(
        rng.uniform(0.0, 1.0, (n_dates, n_assets)),
        index=dates,
        columns=prices.columns,
    )

    # --- vol_target_positions ---
    pos = vol_target_positions(signal, prices)
    assert pos.shape == signal.shape, "FAIL: positions shape mismatch"
    # First vol_lookback+1 rows should be NaN due to rolling std + shift
    assert pos.iloc[:29].isna().all().all(), "FAIL: warm-up rows should all be NaN"
    assert not pos.iloc[40:].isna().all().all(), "FAIL: positions should not be all-NaN post warm-up"
    print(f"  vol_target_positions: PASS  mean_pos = {pos.stack().dropna().mean():.4f}")

    # --- compute_pnl ---
    pnl = compute_pnl(pos, prices)
    assert pnl.shape == pos.shape, "FAIL: pnl shape mismatch"
    port_pnl = pnl.sum(axis=1).dropna()
    print(f"  compute_pnl: PASS  ann_Sharpe ≈ {(port_pnl.mean()/port_pnl.std()*np.sqrt(252)):.3f}")

    # --- walk_forward_split ---
    splits = walk_forward_split(dates, n_folds=5, min_train_months=12)
    assert len(splits) == 5, f"FAIL: expected 5 folds, got {len(splits)}"
    for i, (tr, te) in enumerate(splits):
        assert len(tr) >= 12 * 21, f"FAIL: fold {i} train set too small ({len(tr)} rows)"
        assert len(te) > 0, f"FAIL: fold {i} test set is empty"
        if i > 0:
            assert len(splits[i][0]) > len(splits[i-1][0]), "FAIL: train set not expanding"
    print(f"  walk_forward_split : PASS  5 folds, test sizes = {[len(te) for _, te in splits]}")

    # --- walk_forward_backtest ---
    def momentum_signal(p: pd.DataFrame) -> pd.DataFrame:
        log_r = np.log(p / p.shift(1))
        raw = np.tanh(log_r.rolling(20).sum().shift(1) / (log_r.rolling(20).std().shift(1) * np.sqrt(20) + 1e-8))
        return raw.clip(lower=0.0)

    result = walk_forward_backtest(momentum_signal, prices)
    assert set(result.keys()) == {"per_fold", "aggregate", "pnl_oos"}
    assert len(result["per_fold"]) == 5, "FAIL: expected 5 folds"
    assert isinstance(result["pnl_oos"], pd.Series), "FAIL: pnl_oos must be pd.Series"

    agg = result["aggregate"]
    print(f"  walk_forward_backtest: PASS")
    print(f"    sharpe_mean = {agg['sharpe_mean']:.3f}  "
          f"pct_positive = {agg['sharpe_pct_positive']:.0%}  "
          f"max_dd_worst = {agg['max_dd_worst']:.2%}")
    for f in result["per_fold"]:
        print(f"    fold {f['fold']} [{f['start']} → {f['end']}]: "
              f"SR={f['sharpe']:.3f}  DD={f['max_dd']:.2%}")

    print("=== backtest_wf.py: ALL PASS ===")
