"""
TSMOM v3 signal library.

Three progressive improvements over v2 (binary sign, 28d single lookback):

  C1 — Continuous signal (Zarattini 2025):
       signal = tanh(cumret_L / (rolling_vol_L × sqrt(L)))
       Maps t-stat to (-1, +1); clipped to [0, 1] for long-only.
       Strong trends → position near 1; weak trends → partial position.

  C2 — Multi-timeframe combination:
       Weighted average of continuous signals for L in [7, 14, 28, 60].
       Weights FIXED at [0.15, 0.25, 0.40, 0.20] — not optimized.

  C3 — Momentum volatility scaling (Barroso & Santa-Clara 2015):
       Scale the whole portfolio by TARGET_VOL / strategy_vol_21d.
       Automatically reduces exposure after volatile periods.
       Requires first-pass portfolio returns (two-step backtest).

All functions operate on pd.DataFrame (dates × assets).
No look-ahead: all signals use .shift(1) so value at T uses data ≤ T-1.
Long-only: signals clipped to [0, 1].
Weekly rebalance: weekly_lock() forward-fills on Monday.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Multi-timeframe weights — fixed, not optimized
MTF_LOOKBACKS: list[int]   = [7, 14, 28, 60]
MTF_WEIGHTS:   list[float] = [0.15, 0.25, 0.40, 0.20]

TRADING_DAYS: int = 365
VOL_LOOKBACK: int = 20
VOL_SCALAR_MIN: float = 0.1
VOL_SCALAR_MAX: float = 2.0
BSC_LOOKBACK:   int   = 21   # B&SC portfolio vol window
BSC_CAP:        float = 2.0  # max strategy vol scale factor


# ── Core signal functions ─────────────────────────────────────────────────────

def _asset_vol(log_ret: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """Rolling annualized vol. Shift(1) = no look-ahead."""
    return (
        log_ret.rolling(lookback).std().shift(1)
        * np.sqrt(TRADING_DAYS)
    ).replace(0, np.nan)


def binary_signal(log_ret: pd.DataFrame, lookback: int = 28) -> pd.DataFrame:
    """
    C0 baseline: sign(cumret_L) clipped to {0, 1}.
    Identical to TSMOM v2 signal.py logic (long-only).
    """
    cum = log_ret.rolling(lookback).sum().shift(1)
    sig = (cum > 0).astype(float)
    sig[cum.isna()] = np.nan
    return sig


def continuous_signal(log_ret: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """
    Zarattini 2025 continuous signal for one lookback window.
    t_stat = cumret / (rolling_vol_L × sqrt(L))
    signal  = tanh(t_stat), clipped to [0, 1] for long-only.
    """
    cum  = log_ret.rolling(lookback).sum().shift(1)
    vol  = log_ret.rolling(lookback).std().shift(1) * np.sqrt(lookback)
    vol  = vol.replace(0, np.nan)
    tstat = cum / vol
    sig   = np.tanh(tstat.fillna(0.0)).clip(lower=0.0)
    sig[cum.isna()] = np.nan
    return sig


def multi_tf_signal(
    log_ret: pd.DataFrame,
    lookbacks: list[int]   = MTF_LOOKBACKS,
    weights:   list[float] = MTF_WEIGHTS,
) -> pd.DataFrame:
    """
    C2: weighted average of continuous signals over multiple lookbacks.
    Weights are fixed constants — no in-sample fitting.
    Result is in [0, 1] (long-only, since each component is [0, 1]).
    """
    assert abs(sum(weights) - 1.0) < 1e-9, "weights must sum to 1.0"
    combined = None
    for lb, w in zip(lookbacks, weights):
        s = continuous_signal(log_ret, lb) * w
        combined = s if combined is None else combined.add(s, fill_value=0.0)
    return combined


# ── Position sizing ───────────────────────────────────────────────────────────

def vol_scalar(
    log_ret: pd.DataFrame,
    vol_target: float,
    lookback: int = VOL_LOOKBACK,
) -> pd.DataFrame:
    """
    Per-asset vol scalar: vol_target / realized_vol_L, clipped.
    Uses shift(1) — value at T based on data ≤ T-1.
    """
    rv = _asset_vol(log_ret, lookback).ffill().fillna(vol_target)
    return (vol_target / rv).clip(VOL_SCALAR_MIN, VOL_SCALAR_MAX)


def weekly_lock(df: pd.DataFrame) -> pd.DataFrame:
    """
    Propagate signal/position only on Mondays; forward-fill the rest.
    Models weekly rebalance at Monday open.
    """
    is_mon = df.index.dayofweek == 0
    locked = df.copy()
    locked[~is_mon] = np.nan
    return locked.ffill().fillna(0.0)


def build_positions(
    signal_df: pd.DataFrame,
    log_ret:   pd.DataFrame,
    vol_target: float,
) -> pd.DataFrame:
    """
    Position = signal × vol_scalar, Monday-locked.
    """
    vs   = vol_scalar(log_ret, vol_target)
    raw  = signal_df * vs
    return weekly_lock(raw)


# ── Barroso & Santa-Clara portfolio vol scaling ───────────────────────────────

def apply_bsc_scale(
    positions:   pd.DataFrame,
    log_ret:     pd.DataFrame,
    target_vol:  float = 0.15,
) -> pd.DataFrame:
    """
    Two-step Barroso & Santa-Clara (2015) momentum crash protection.

    Step 1: compute first-pass daily portfolio return (mean of per-asset).
    Step 2: rolling 21d std of portfolio returns → strategy_vol_21d[T].
    Step 3: scale = clip(target_vol / strategy_vol_21d[T], 0, BSC_CAP).
            Scale applied uniformly across all assets at time T.

    No look-ahead: strategy_vol at T uses returns [T-22, T-1] (shift 1).
    """
    arith = np.exp(log_ret) - 1
    held  = positions.shift(1).fillna(0.0)
    raw_port = (held * arith).mean(axis=1)

    strat_vol = (
        raw_port.rolling(BSC_LOOKBACK).std().shift(1) * np.sqrt(TRADING_DAYS)
    )
    strat_vol = strat_vol.replace(0, np.nan).fillna(target_vol)

    scale = (target_vol / strat_vol).clip(upper=BSC_CAP)

    return positions.mul(scale, axis=0)
