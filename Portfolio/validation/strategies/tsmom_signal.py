"""
Pure TSMOM v3 signal computation for CPCV proof-of-work (Strategy A).

All functions here are pure (no I/O). They replicate the logic from
Portfolio/reporting/generate_strategies.py::_run_tsmom_v3() but are
factored out for testability and reuse in CPCV backtest_fn factories.

Signal formula (CLAUDE.md §Strategy A)
---------------------------------------
  lr_lag  = log_return.shift(1)                     # T-1 data only
  cumret  = lr_lag.rolling(lookback).sum()
  vol_sig = lr_lag.rolling(lookback).std()
  signal  = tanh(cumret / (vol_sig × √lookback)).clip(lower=0)
  position = (signal × vol_scalar).where(Monday).ffill()
  position is shifted 1 before multiplying returns → trade at T, signal T-1

Design rationale for CPCV backtest_fn
--------------------------------------
Since TSMOM v3 has NO trainable parameters (lookback and vol_tgt are fixed
hyperparameters, not data-fitted), pre-computing the full returns series
and slicing test_idx is both correct and efficient:
  - No future data leaks into signal (lr.shift(1) construction)
  - No parameters are estimated from the training fold
  - Purge/embargo in CombinatorialPurgedCV prevents train/test contamination

For strategies WITH trainable parameters (e.g., LSTM, threshold optimisation),
the backtest_fn must retrain on train_idx and predict on test_idx.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from Portfolio.reporting.metrics import hac_sharpe_ratio, to_excess_returns

_LOOKBACK: int = 28
_VOL_LB: int = 20
_VOL_TGT: float = 0.18
_COST_RT: float = 0.0017
_CRYPTO_DAYS: int = 365


def compute_tsmom_returns(
    prices: pd.DataFrame,
    lookback: int = _LOOKBACK,
    vol_lb: int = _VOL_LB,
    vol_tgt: float = _VOL_TGT,
    cost_rt: float = _COST_RT,
    crypto_days: int = _CRYPTO_DAYS,
) -> pd.Series:
    """
    Full TSMOM v3 equal-weighted portfolio returns. Pure function (no I/O).

    Parameters
    ----------
    prices : pd.DataFrame
        Columns = asset tickers, index = date, values = adjusted close price.
    lookback : int
        Momentum and volatility lookback in bars (default 28).
    vol_lb : int
        Vol-targeting rolling window (default 20 bars).
    vol_tgt : float
        Annualised volatility target (default 0.18 = 18%).
    cost_rt : float
        Round-trip cost fraction (default 0.0017 = 0.17%).
    crypto_days : int
        Trading days per year for vol annualisation (default 365 for crypto).

    Returns
    -------
    pd.Series
        Daily net portfolio returns (arithmetic). Index = DatetimeIndex.
        Only dates where ≥ 2 assets have valid data are included.
    """
    net_per_asset: dict[str, pd.Series] = {}
    for col in prices.columns:
        px = prices[col].dropna()
        if len(px) < lookback + vol_lb + 2:
            continue

        lr = np.log(px / px.shift(1)).clip(-1.0, 1.0).dropna()
        arith = np.exp(lr) - 1.0

        lr_lag = lr.shift(1)
        cumret = lr_lag.rolling(lookback).sum()
        vol_sig = lr_lag.rolling(lookback).std()
        raw_sig = (cumret / (vol_sig * np.sqrt(lookback))).fillna(0.0)
        signal = np.tanh(raw_sig).clip(lower=0.0)

        vol_ann = lr_lag.rolling(vol_lb).std() * np.sqrt(crypto_days)
        vol_scalar = (vol_tgt / vol_ann).clip(0.1, 2.0)

        position = (signal * vol_scalar).where(lr.index.dayofweek == 0).ffill()
        gross = position.shift(1) * arith
        turnover = (position - position.shift(1)).abs().fillna(0.0)
        net_per_asset[col] = (gross - turnover * cost_rt).dropna()

    if not net_per_asset:
        return pd.Series(dtype=float)

    port = pd.DataFrame(net_per_asset)
    valid = port.notna().sum(axis=1) >= 2
    return port[valid].mean(axis=1).dropna()


def make_tsmom_backtest_fn(returns: pd.Series) -> Callable[[np.ndarray, np.ndarray], float]:
    """
    Factory for CPCV backtest_fn from pre-computed TSMOM returns.

    Since TSMOM v3 has no trainable parameters, the full returns series is
    computed once and backtest_fn slices test_idx for OOS Sharpe.

    Parameters
    ----------
    returns : pd.Series
        Pre-computed daily net portfolio returns (from compute_tsmom_returns).

    Returns
    -------
    Callable
        fn(train_idx, test_idx) → float OOS HAC Sharpe on test slice.
    """
    def fn(train_idx: np.ndarray, test_idx: np.ndarray) -> float:
        r_test = returns.iloc[test_idx]
        if len(r_test) < 10 or float(r_test.std()) == 0:
            return 0.0
        r_exc = to_excess_returns(r_test)
        sr, _, _ = hac_sharpe_ratio(r_exc)
        return float(sr) if not np.isnan(sr) else 0.0

    return fn
