"""
Feature engineering following Parente et al. (2024) and Felizardo et al. (2022).

Key design choices:
- All features computed from PAST data only → zero look-ahead bias
- Returns used instead of raw prices for stationarity (Felizardo et al.)
- SHAP top-10 features from Parente et al. prioritised:
  Bollinger, EMA crossovers (4 pairs), RSI, ULTOSC, Z-Score, temporal
"""

import numpy as np
import pandas as pd


# ── Primitive helpers ──────────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()


def _zscore(series: pd.Series, window: int = 30) -> pd.Series:
    mu = series.rolling(window, min_periods=1).mean()
    sigma = series.rolling(window, min_periods=1).std()
    return (series - mu) / (sigma + 1e-9)


# ── Technical indicators ───────────────────────────────────────────────────────

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI, normalised to [0, 1]."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return (100 - 100 / (1 + rs)) / 100.0   # normalise to [0,1]


def bollinger(
    close: pd.Series, window: int = 20, n_std: float = 2.0
) -> pd.DataFrame:
    """
    Returns %B (position within bands) and band width.
    %B = (Price - Lower) / (Upper - Lower)
    Parente et al. found Bollinger the single most important feature.
    """
    sma = _sma(close, window)
    std = close.rolling(window, min_periods=1).std()
    upper = sma + n_std * std
    lower = sma - n_std * std
    pct_b = (close - lower) / (upper - lower + 1e-9)
    bb_width = (upper - lower) / (sma + 1e-9)
    return pd.DataFrame({"bollinger": pct_b, "bb_width": bb_width})


def ultimate_oscillator(
    high: pd.Series, low: pd.Series, close: pd.Series,
    p1: int = 7, p2: int = 14, p3: int = 28,
) -> pd.Series:
    """ULTOSC: triple-weighted buying pressure / true range ratio."""
    prev_close = close.shift(1)
    bp = close - pd.concat([low, prev_close], axis=1).min(axis=1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)

    def _avg(p: int) -> pd.Series:
        return bp.rolling(p, min_periods=1).sum() / (
            tr.rolling(p, min_periods=1).sum() + 1e-9
        )

    uo = 100.0 * (4 * _avg(p1) + 2 * _avg(p2) + _avg(p3)) / 7.0
    return uo / 100.0   # normalise to [0,1]


def ema_crossovers(close: pd.Series) -> pd.DataFrame:
    """
    4 EMA crossover signals (Parente et al.):
    (1,20), (20,50), (50,100), (1,50) — normalised difference.
    """
    spans = [1, 20, 50, 100]
    emas = {s: (close if s == 1 else _ema(close, s)) for s in spans}
    pairs = [(1, 20), (20, 50), (50, 100), (1, 50)]
    out = {}
    for fast, slow in pairs:
        out[f"ema_{fast}_{slow}"] = (emas[fast] - emas[slow]) / (close + 1e-9)
    return pd.DataFrame(out)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range, z-score normalised."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return _zscore(tr, window)


# ── Main feature extraction ────────────────────────────────────────────────────

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature matrix from raw OHLCV DataFrame.

    Args:
        df: DataFrame with columns Open, High, Low, Close, Volume
            and a DatetimeIndex.

    Returns:
        feat: DataFrame of shape (T, n_features), NaN rows dropped downstream.
    """
    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    feat = pd.DataFrame(index=df.index)

    # 1. Bollinger %B and width  ← #1 most important (Parente SHAP)
    bb = bollinger(close, window=20)
    feat["bollinger"] = bb["bollinger"]
    feat["bb_width"]  = bb["bb_width"]

    # 2. EMA crossovers (4 pairs) ← #2,4,6,8 (Parente SHAP)
    feat = feat.join(ema_crossovers(close))

    # 3. RSI  ← #3 (Parente SHAP)
    feat["rsi"] = rsi(close, period=14)

    # 4. ULTOSC  ← #9 (Parente SHAP)
    feat["ultosc"] = ultimate_oscillator(high, low, close)

    # 5. Z-score of close  ← #10 (Parente SHAP)
    feat["zscore_close"] = _zscore(close, window=30)
    feat["zscore_vol"]   = _zscore(vol,   window=30)

    # 6. Price returns — stationarity (Felizardo et al.)
    feat["ret_1"]  = close.pct_change(1)
    feat["ret_5"]  = close.pct_change(5)
    feat["ret_20"] = close.pct_change(20)

    # 7. Volatility
    feat["atr"] = atr(high, low, close)

    # 8. Temporal features  ← day-of-week & month top-5 (Parente SHAP)
    # Note: hour is omitted — always 0 on daily bars and adds no signal.
    feat["dayofweek"] = df.index.dayofweek / 6.0
    feat["month"]     = (df.index.month - 1) / 11.0

    # 9. Volume momentum
    feat["vol_ret"] = vol.pct_change(1).clip(-5, 5)

    return feat.replace([np.inf, -np.inf], np.nan)


def get_feature_names() -> list:
    """Return list of feature names (for SHAP plots etc.)."""
    return [
        "bollinger", "bb_width",
        "ema_1_20", "ema_20_50", "ema_50_100", "ema_1_50",
        "rsi", "ultosc",
        "zscore_close", "zscore_vol",
        "ret_1", "ret_5", "ret_20",
        "atr",
        "dayofweek", "month",
        "vol_ret",
    ]
    