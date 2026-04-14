"""
Labeling algorithm — revised from Parente et al. (2024).

Key changes vs original:
    - use_trend_confirm=False by default: removed EMA trend confirmation.
      The original required BOTH a positive return AND an upward EMA trend
      to label Buy. This double filter made labels too clean (circular bias).
    - alpha lowered from 3.8% to 1.5%: less aggressive filtering means
      the model must predict on more bars, giving a more realistic win rate.
    - beta lowered from 26.4% to 15%: still filters black swans.

Label scheme: Buy (2) / Hold (1) / Sell (0)
"""

import numpy as np
import pandas as pd
from typing import Tuple

from config import Config

# Label constants
SELL, HOLD, BUY = 0, 1, 2
LABEL_NAMES = {SELL: "Sell", HOLD: "Hold", BUY: "Buy"}


def compute_labels(df: pd.DataFrame, config: Config) -> pd.Series:
    """
    Vectorised labeling.

    Return formula (Parente et al., Definition 2):
        R(k) = [(1 - f) * Close_{t+k}  -  (1 + f) * Open_t] / Open_t

    Label rules:
        alpha < |R(k)| < beta  AND  R > 0  →  Buy
        alpha < |R(k)| < beta  AND  R < 0  →  Sell
        Otherwise                           →  Hold

    If config.use_trend_confirm=True, additionally requires:
        EMA trend at t+k > EMA trend at t  for Buy
        EMA trend at t+k < EMA trend at t  for Sell
    """
    close = df["Close"].values.astype(np.float64)
    open_ = df["Open"].values.astype(np.float64)
    n     = len(df)
    k     = config.forward_window
    f     = config.fee
    alpha = config.alpha
    beta  = config.beta

    # Forward return (vectorised)
    future_close = np.full(n, np.nan)
    future_close[: n - k] = close[k:]

    ret     = ((1 - f) * future_close - (1 + f) * open_) / (open_ + 1e-9)
    abs_ret = np.abs(ret)
    in_band = (abs_ret > alpha) & (abs_ret < beta)

    labels = np.ones(n, dtype=np.int64)   # Hold by default

    if config.use_trend_confirm:
        # Original Parente et al. — requires EMA trend alignment
        ema_close = (
            pd.Series(close)
            .ewm(span=config.back_window, adjust=False)
            .mean()
            .values
        )
        future_ema = np.full(n, np.nan)
        future_ema[: n - k] = ema_close[k:]
        trend = future_ema - ema_close

        labels[in_band & (ret > 0) & (trend > 0)] = BUY
        labels[in_band & (ret < 0) & (trend < 0)] = SELL
    else:
        # Revised — only requires return direction, no trend double-filter
        labels[in_band & (ret > 0)] = BUY
        labels[in_band & (ret < 0)] = SELL

    # Last k rows have no valid forward return
    labels[n - k:] = HOLD

    return pd.Series(labels, index=df.index, name="label")


def calibrate_thresholds(
    df: pd.DataFrame,
    alpha_pct: float = 50,     # revised: 50th pct instead of 85th
    beta_pct: float = 99.0,
) -> Tuple[float, float]:
    """
    Derive alpha/beta from empirical return distribution.
    Lower alpha_pct = more Buy/Sell labels = more realistic training.
    """
    pct_chg = ((df["Close"] - df["Open"]) / df["Open"]).abs()
    alpha   = float(np.nanpercentile(pct_chg, alpha_pct))
    beta    = float(np.nanpercentile(pct_chg, beta_pct))
    return alpha, beta


def undersample_hold(
    X: np.ndarray,
    y: np.ndarray,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Undersample Hold majority class to match Buy + Sell count.
    Applied ONLY to training split.
    """
    rng          = np.random.default_rng(seed)
    hold_idx     = np.where(y == HOLD)[0]
    non_hold_idx = np.where(y != HOLD)[0]

    n_keep    = len(non_hold_idx)
    hold_keep = rng.choice(
        hold_idx,
        size=min(n_keep, len(hold_idx)),
        replace=False,
    )
    all_idx = np.sort(np.concatenate([hold_keep, non_hold_idx]))
    return X[all_idx], y[all_idx]


def label_distribution(y: np.ndarray) -> dict:
    return {LABEL_NAMES[v]: int((y == v).sum()) for v in [SELL, HOLD, BUY]}