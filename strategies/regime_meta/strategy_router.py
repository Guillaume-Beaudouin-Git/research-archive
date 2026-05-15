"""
Strategy router — allocates positions based on current market regime.

BULL_TREND → TSMOM long-only (14-asset universe, vol_target=0.18)
BEAR_TREND → TSMOM short-only (BTC/ETH/SOL only, vol_target=0.12)
RANGE      → flat (0% exposure)
CRASH      → cash (0% exposure, immediate exit)
"""

import numpy as np
import pandas as pd

TSMOM_UNIVERSE = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD", "ARB-USD",
    "MATIC-USD", "OP-USD", "DOGE-USD", "ADA-USD", "DOT-USD",
    "UNI-USD", "LTC-USD", "BCH-USD",
]
SHORT_ASSETS  = ["BTC-USD", "ETH-USD", "SOL-USD"]

VOL_TARGET_BULL = 0.18
VOL_TARGET_BEAR = 0.12
VOL_LOOKBACK    = 20    # days for realized vol estimate
COST_PER_LEG    = 0.0017
VOL_SCALAR_MIN  = 0.1
VOL_SCALAR_MAX  = 2.0
GROSS_CAP       = 0.90
MOM_LOOKBACK    = 28   # days for TSMOM signal


def _tsmom_signal(log_ret: pd.DataFrame, assets: list) -> pd.DataFrame:
    """28d cumulative log return sign. +1 = long, -1 = short, 0 = no signal."""
    lr = log_ret[assets]
    mom = lr.rolling(MOM_LOOKBACK).sum()
    return np.sign(mom)


def _vol_scalar(log_ret: pd.DataFrame, assets: list,
                vol_target: float) -> pd.DataFrame:
    """Per-asset vol scalar: vol_target / realized_vol, clipped."""
    rv = log_ret[assets].rolling(VOL_LOOKBACK).std() * np.sqrt(365)
    rv = rv.replace(0, np.nan).ffill().fillna(vol_target)
    scalar = (vol_target / rv).clip(VOL_SCALAR_MIN, VOL_SCALAR_MAX)
    return scalar


def _monday_lock(df: pd.DataFrame) -> pd.DataFrame:
    """Keep values only on Monday; forward-fill the rest (weekly rebalance)."""
    is_mon = df.index.dayofweek == 0
    locked = df.copy()
    locked[~is_mon] = np.nan
    return locked.ffill().fillna(0.0)


def build_raw_positions(close: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Precompute BULL and BEAR raw positions (before regime routing).
    Returns (pos_bull, pos_bear) — Monday-locked, vol-scaled.
    """
    log_ret = np.log(close / close.shift(1)).clip(-1.0, 1.0)

    # BULL: long-only, full universe
    sig_bull  = _tsmom_signal(log_ret, TSMOM_UNIVERSE).clip(lower=0)  # long-only
    scl_bull  = _vol_scalar(log_ret, TSMOM_UNIVERSE, VOL_TARGET_BULL)
    raw_bull  = (sig_bull * scl_bull)
    pos_bull  = _monday_lock(raw_bull)

    # BEAR: short-only, BTC/ETH/SOL
    sig_bear  = -_tsmom_signal(log_ret, SHORT_ASSETS).clip(upper=0)   # short-only (negative)
    scl_bear  = _vol_scalar(log_ret, SHORT_ASSETS, VOL_TARGET_BEAR)
    raw_bear  = (sig_bear * scl_bear)
    pos_bear  = _monday_lock(raw_bear)
    # Put into full-universe DataFrame (zero for non-short assets)
    pos_bear_full = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for a in SHORT_ASSETS:
        if a in pos_bear.columns:
            pos_bear_full[a] = pos_bear[a]

    return pos_bull, pos_bear_full


def route_positions(pos_bull: pd.DataFrame,
                    pos_bear: pd.DataFrame,
                    regimes:  pd.Series,
                    close:    pd.DataFrame) -> pd.DataFrame:
    """
    Apply regime routing daily.
    - CRASH:      set to 0 immediately (overrides Monday rule)
    - BULL_TREND: use pos_bull (already Monday-locked)
    - BEAR_TREND: use pos_bear (already Monday-locked)
    - RANGE:      zero

    The regime series is aligned to the same index as close.
    State[T] = regime known at end of T-1 (already shifted in detector).
    """
    regimes_aligned = regimes.reindex(close.index).ffill().fillna("RANGE")

    # Build final positions
    positions = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    is_mon    = close.index.dayofweek == 0

    # Start with BULL positions everywhere, then mask by regime
    for dt in close.index:
        r = regimes_aligned.loc[dt]
        if r == "CRASH" or r == "RANGE":
            # positions[dt] stays 0
            pass
        elif r == "BULL_TREND":
            positions.loc[dt] = pos_bull.loc[dt]
        elif r == "BEAR_TREND":
            positions.loc[dt] = pos_bear.loc[dt]

    # Gross cap on each day
    gross_total = positions.abs().sum(axis=1)
    needs_cap   = gross_total > GROSS_CAP
    scale       = pd.Series(1.0, index=positions.index)
    scale[needs_cap] = GROSS_CAP / gross_total[needs_cap]
    positions   = positions.mul(scale, axis=0)

    return positions


def compute_pnl(close: pd.DataFrame,
                positions: pd.DataFrame,
                regimes: pd.Series) -> pd.Series:
    """
    MEAN convention P&L.
    Cost applied on:
      - Monday position changes (regular rebalance)
      - Any day where CRASH forces immediate exit
    """
    arith_ret = close.pct_change().fillna(0.0)
    held      = positions.shift(1).fillna(0.0)
    gross     = (held * arith_ret).mean(axis=1)

    # Turnover cost: Monday rebalance + CRASH exit days
    is_mon    = pd.Series(close.index.dayofweek == 0, index=close.index)
    regimes_a = regimes.reindex(close.index).ffill().fillna("RANGE")
    is_crash  = regimes_a == "CRASH"
    cost_days = (is_mon | is_crash).astype(float)

    turn      = positions.diff().abs()
    costs     = (turn * COST_PER_LEG * cost_days.values.reshape(-1, 1)).mean(axis=1)

    return gross - costs
