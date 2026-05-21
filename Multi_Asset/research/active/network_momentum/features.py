"""
features.py — Momentum feature engineering for Network Momentum (Strategy E)
=============================================================================
Implements the 8 features from Pu et al. (2023) Table 1:
  - 5 normalised return features (1d, 21d, 63d, 126d, 252d lookback)
  - 3 normalised MACD features (8/24, 16/48, 32/96 fast/slow pairs)

Vol normalization: EWMA stdev with halflife=60 days.
Winsorization: per-feature EWMA mean ± 5σ, halflife=252 days.

Output: 3D numpy array F of shape (T, N, 8) aligned to returns index.

Usage:
    from Multi_Asset.research.active.network_momentum.features import build_features
    F, feature_names = build_features(returns)
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "r_norm_1d",
    "r_norm_21d",
    "r_norm_63d",
    "r_norm_126d",
    "r_norm_252d",
    "macd_8_24",
    "macd_16_48",
    "macd_32_96",
]

VOL_HALFLIFE    = 60    # EWMA vol halflife (days)
WINS_HALFLIFE   = 252   # Winsorization EWMA halflife (days)
WINS_SIGMA      = 5.0   # Winsorize at ±5 sigma


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ewma_vol(returns: pd.DataFrame, halflife: int = VOL_HALFLIFE) -> pd.DataFrame:
    """EWMA annualized volatility per asset."""
    var = returns.ewm(halflife=halflife, min_periods=halflife // 2).var()
    return np.sqrt(var * 252)


def _norm_return(
    prices: pd.DataFrame,
    lookback: int,
    vol: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalised lookback return: r_t / (sigma_t × sqrt(lookback/252))
    """
    r = np.log(prices / prices.shift(lookback))
    scale = vol * np.sqrt(lookback / 252)
    return r / scale.replace(0, np.nan)


def _macd(
    prices: pd.DataFrame,
    fast: int,
    slow: int,
    vol: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalized MACD: (EMA_fast - EMA_slow) / (sigma × sqrt(slow/252))
    EWMA prices with span = 2 × halflife - 1 (standard EWM span convention).
    """
    ema_fast = prices.ewm(span=fast,  adjust=False, min_periods=fast  // 2).mean()
    ema_slow = prices.ewm(span=slow,  adjust=False, min_periods=slow  // 2).mean()
    macd_raw = ema_fast - ema_slow
    scale    = vol * prices * np.sqrt(slow / 252)   # price-scaled volatility
    return macd_raw / scale.replace(0, np.nan)


def _winsorize_panel(
    feat: pd.DataFrame,
    halflife: int = WINS_HALFLIFE,
    n_sigma: float = WINS_SIGMA,
) -> pd.DataFrame:
    """
    Winsorize each feature column using expanding EWMA mean ± n_sigma * EWMA std.
    Computed cross-sectionally per feature across all assets at each time point,
    then per-series to match paper specification.
    """
    # Per-asset EWMA mean and std for winsorization
    ewm_mean = feat.ewm(halflife=halflife, min_periods=halflife // 4).mean()
    ewm_std  = feat.ewm(halflife=halflife, min_periods=halflife // 4).std()

    lower = ewm_mean - n_sigma * ewm_std
    upper = ewm_mean + n_sigma * ewm_std

    return feat.clip(lower=lower, upper=upper, axis=0)


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def build_features(
    returns: pd.DataFrame,
    prices:  pd.DataFrame | None = None,
) -> Tuple[np.ndarray, List[str]]:
    """
    Build the 8 momentum features for each asset on each day.

    Parameters
    ----------
    returns : pd.DataFrame (T × N) — daily log excess returns (from universe.py)
    prices  : pd.DataFrame (T × N) — raw prices. If None, reconstructed from returns.

    Returns
    -------
    F    : np.ndarray, shape (T, N, 8), float32, NaN where insufficient history
    feature_names : list of 8 strings
    """
    T, N = returns.shape
    idx  = returns.index
    cols = returns.columns

    # Reconstruct prices from returns if not provided
    # price[t] = exp(cumsum(returns)), anchored at 1.0
    if prices is None:
        prices = np.exp(returns.fillna(0).cumsum()) * 1.0
        prices = pd.DataFrame(prices, index=idx, columns=cols)

    # Align prices to returns index
    prices = prices.reindex(idx).ffill()

    # EWMA vol (annualized)
    vol = _ewma_vol(returns)

    # Feature matrices (T × N each)
    feats: dict[str, pd.DataFrame] = {}

    feats["r_norm_1d"]   = _norm_return(prices, 1,   vol)
    feats["r_norm_21d"]  = _norm_return(prices, 21,  vol)
    feats["r_norm_63d"]  = _norm_return(prices, 63,  vol)
    feats["r_norm_126d"] = _norm_return(prices, 126, vol)
    feats["r_norm_252d"] = _norm_return(prices, 252, vol)
    feats["macd_8_24"]   = _macd(prices, fast=8,  slow=24, vol=vol)
    feats["macd_16_48"]  = _macd(prices, fast=16, slow=48, vol=vol)
    feats["macd_32_96"]  = _macd(prices, fast=32, slow=96, vol=vol)

    # Winsorize each feature
    for name in FEATURE_NAMES:
        feats[name] = _winsorize_panel(feats[name])

    # Stack into (T, N, 8) tensor
    F = np.stack(
        [feats[name].values for name in FEATURE_NAMES],
        axis=2
    ).astype(np.float32)

    return F, FEATURE_NAMES


if __name__ == "__main__":
    import logging, sys, os
    from pathlib import Path
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    repo = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(repo))
    os.chdir(repo)

    from Multi_Asset.research.active.network_momentum.universe import load_universe
    ret, meta = load_universe()
    F, names = build_features(ret, prices=meta["prices"].reindex(ret.index).ffill())

    print(f"\nFeature tensor shape: {F.shape}  (T={F.shape[0]}, N={F.shape[1]}, F=8)")
    print(f"Feature names: {names}")
    print(f"NaN fraction per feature:")
    for i, name in enumerate(names):
        nan_frac = np.isnan(F[:, :, i]).mean()
        print(f"  {name}: {nan_frac:.3f}")
    print(f"\nSample features at t=-1 (last day), first 5 assets:")
    sample = pd.DataFrame(F[-1, :5, :], columns=names,
                          index=ret.columns[:5])
    print(sample.round(3).to_string())
