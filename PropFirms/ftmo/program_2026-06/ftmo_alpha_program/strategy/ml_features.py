"""
ml_features.py — causal technical feature library for Family-6 ML combo sprint
================================================================================

Strictly causal "green list" of price-derived features for the FTMO ML-combo
sprint. Every feature is computed only from CLOSED bars and lagged one bar
(known at t, applied to trade at t+1) — Hard rule L1.

Whitelist (9 features, indexed by "cluster intent"):

  1. trend_slope_fast   — EMA(5) slope    : recent direction
  2. trend_slope_slow   — EMA(20) slope   : multi-bar drift
  3. velocity_ifrsi     — Inverse-Fisher RSI(14) : bounded ∈ [-1,+1]
  4. accel_macd_hist    — MACD histogram(12,26,9): change of momentum
  5. regime_atr_pct     — ATR(14) percentile rank (252-bar): vol regime
  6. regime_rv          — Realised vol (20-bar std of log-returns)
  7. squeeze_bb_kc      — BB/KC width ratio: < 1 ⇒ squeeze (compression)
  8. strength_adx       — ADX(14): trend strength
  9. choppiness         — Choppiness Index(14): range vs trend

Optional:
 10. vwap_prox          — (close - intra-session VWAP) / VWAP (uses tick_volume)

NO non-causal indicators: no ZigZag/Fractals/Senkou-Chikou-Ichimoku, no
SAR/Supertrend computed on intra-bar high/low. ATR/ADX use confirmed bars only.

Data convention
---------------
Input: M1 CSV with columns [timestamp_utc, open, high, low, close, tick_volume,
spread] from data/panels/m5_indices/<SYM>_M1.csv. Resample causally to a working
freq (default 15min). Session filter applied (liquid hours, weekdays).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
PANEL = REPO / "data" / "panels" / "m5_indices"


# ────────────────────────────────────────────────────────────────────────────────
# Data loading + causal resample
# ────────────────────────────────────────────────────────────────────────────────

def load_m1(symbol: str) -> pd.DataFrame:
    """Load the M1 panel: OHLC + tick_volume + spread, UTC index, deduped."""
    p = PANEL / f"{symbol}_M1.csv"
    df = pd.read_csv(p)
    df["ts"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S",
                              errors="coerce")
    df = (df.dropna(subset=["ts"]).set_index("ts").sort_index()
            [["open", "high", "low", "close", "tick_volume", "spread"]])
    df = df[~df.index.duplicated(keep="first")]
    return df


def resample_session(df: pd.DataFrame, freq: str = "15min",
                     hours: tuple[int, int] = (7, 20)) -> pd.DataFrame:
    """Causal OHLC + spread mean + volume sum resample, then liquid-hours filter.

    Drops weekend bars and the 21–22 UTC rollover blow-out (per fx_data.py).
    """
    agg = {"open": "first", "high": "max", "low": "min", "close": "last",
           "tick_volume": "sum", "spread": "mean"}
    out = df.resample(freq, label="right", closed="right").agg(agg)
    out = out.dropna(subset=["close"])
    h = out.index.hour
    mask = (h >= hours[0]) & (h < hours[1]) & (out.index.dayofweek < 5)
    return out[mask]


# ────────────────────────────────────────────────────────────────────────────────
# Causal indicator helpers (Wilder-style smoothing, bounded RSI, robust to NaN)
# ────────────────────────────────────────────────────────────────────────────────

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _wilder(s: pd.Series, n: int) -> pd.Series:
    """Wilder smoothing (RMA) = EMA with alpha = 1/n."""
    return s.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([(high - low),
                    (high - prev_close).abs(),
                    (low - prev_close).abs()], axis=1).max(axis=1)
    return tr


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = -delta.clip(upper=0.0)
    rs_up = _wilder(up, n)
    rs_dn = _wilder(dn, n).replace(0.0, np.nan)
    rs = rs_up / rs_dn
    return 100.0 - 100.0 / (1.0 + rs)


def _inverse_fisher_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """IFISH(RSI): tanh((RSI-50)/10) — bounded ∈ (-1, 1), more discriminative."""
    rsi = _rsi(close, n)
    return np.tanh((rsi - 50.0) / 10.0)


def _macd_hist(close: pd.Series, fast: int = 12, slow: int = 26,
               signal: int = 9) -> pd.Series:
    macd = _ema(close, fast) - _ema(close, slow)
    sig = _ema(macd, signal)
    return macd - sig


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    return _wilder(_true_range(high, low, close), n)


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Standard Wilder ADX. Uses confirmed bars only."""
    up_move = high.diff()
    dn_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > dn_move) & (up_move > 0), up_move, 0.0),
                        index=high.index)
    minus_dm = pd.Series(np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0.0),
                         index=high.index)
    tr = _true_range(high, low, close)
    atr = _wilder(tr, n).replace(0.0, np.nan)
    plus_di = 100.0 * _wilder(plus_dm, n) / atr
    minus_di = 100.0 * _wilder(minus_dm, n) / atr
    dx = (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan) * 100.0
    return _wilder(dx, n)


def _choppiness(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    """Choppiness Index ∈ [0, 100]. > 61.8 ≈ chop, < 38.2 ≈ trend (Dreiss)."""
    tr = _true_range(high, low, close)
    atr_sum = tr.rolling(n).sum()
    hh = high.rolling(n).max()
    ll = low.rolling(n).min()
    rng = (hh - ll).replace(0.0, np.nan)
    return 100.0 * np.log10(atr_sum / rng) / np.log10(n)


def _bb_kc_squeeze(close: pd.Series, high: pd.Series, low: pd.Series,
                   n: int = 20, bb_k: float = 2.0, kc_k: float = 1.5) -> pd.Series:
    """BB-width / KC-width ratio. < 1 ⇒ Bollingers inside Keltners ⇒ squeeze."""
    mid = close.rolling(n).mean()
    bb_std = close.rolling(n).std(ddof=0)
    bb_width = 2.0 * bb_k * bb_std
    atr = _atr(high, low, close, n)
    kc_width = 2.0 * kc_k * atr
    return bb_width / kc_width.replace(0.0, np.nan)


def _intrasession_vwap(close: pd.Series, high: pd.Series, low: pd.Series,
                       volume: pd.Series) -> pd.Series:
    """Causal intra-session VWAP using typical price × volume; resets each day."""
    typ = (high + low + close) / 3.0
    day = close.index.normalize()
    pv = (typ * volume).groupby(day).cumsum()
    vv = volume.groupby(day).cumsum().replace(0.0, np.nan)
    return pv / vv


# ────────────────────────────────────────────────────────────────────────────────
# Public API: build the feature matrix
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureSpec:
    """Knobs for the feature library — defaults are the pre-registered values."""
    rsi_n: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_sig: int = 9
    atr_n: int = 14
    atr_pct_window: int = 252      # bars (≈ 1 session at M15 ~ 4*13=52, so 252 ≈ 5 days)
    rv_n: int = 20
    bb_n: int = 20
    adx_n: int = 14
    chop_n: int = 14
    ema_fast: int = 5
    ema_slow: int = 20


FEATURE_NAMES = [
    "trend_slope_fast",
    "trend_slope_slow",
    "velocity_ifrsi",
    "accel_macd_hist",
    "regime_atr_pct",
    "regime_rv",
    "squeeze_bb_kc",
    "strength_adx",
    "choppiness",
    "vwap_prox",          # optional 10th — gated by tick_volume availability
]


def build_features(bars: pd.DataFrame, spec: FeatureSpec | None = None,
                   include_vwap: bool = True) -> pd.DataFrame:
    """Compute the causal feature library on resampled bars (closed-bar values).

    Returns a DataFrame aligned on `bars.index` with one column per feature in
    FEATURE_NAMES. All values are CLOSED-bar values, then shifted by 1 at the end
    via `as_known_at()` (caller responsibility, kept explicit).
    """
    spec = spec or FeatureSpec()
    close = bars["close"]
    high = bars["high"]
    low = bars["low"]
    vol = bars["tick_volume"] if "tick_volume" in bars.columns else None
    logp = np.log(close)

    f: dict[str, pd.Series] = {}

    # 1-2: EMA slopes (log-price, units = log-return/bar)
    ema_f = _ema(logp, spec.ema_fast)
    ema_s = _ema(logp, spec.ema_slow)
    f["trend_slope_fast"] = ema_f - ema_f.shift(spec.ema_fast)
    f["trend_slope_slow"] = ema_s - ema_s.shift(spec.ema_slow)

    # 3: Inverse-Fisher RSI (bounded ∈ (-1,1))
    f["velocity_ifrsi"] = _inverse_fisher_rsi(close, spec.rsi_n)

    # 4: MACD histogram (log-price → unit ≈ log-return)
    f["accel_macd_hist"] = _macd_hist(logp, spec.macd_fast, spec.macd_slow, spec.macd_sig)

    # 5: ATR percentile rank (vol regime, ∈ [0,1])
    atr = _atr(high, low, close, spec.atr_n) / close
    f["regime_atr_pct"] = atr.rolling(spec.atr_pct_window, min_periods=spec.atr_pct_window // 2)\
        .apply(lambda x: (x.rank(pct=True).iloc[-1]) if len(x) else np.nan, raw=False)

    # 6: Realised vol (20-bar std of log-returns)
    f["regime_rv"] = logp.diff().rolling(spec.rv_n).std(ddof=0)

    # 7: BB/KC squeeze ratio
    f["squeeze_bb_kc"] = _bb_kc_squeeze(close, high, low, spec.bb_n)

    # 8: ADX (Wilder)
    f["strength_adx"] = _adx(high, low, close, spec.adx_n)

    # 9: Choppiness
    f["choppiness"] = _choppiness(high, low, close, spec.chop_n)

    # 10: VWAP proximity (optional, gated)
    if include_vwap and vol is not None:
        vwap = _intrasession_vwap(close, high, low, vol)
        f["vwap_prox"] = (close - vwap) / vwap
    else:
        f["vwap_prox"] = pd.Series(np.nan, index=bars.index)

    feat = pd.DataFrame(f, index=bars.index)
    return feat


def as_known_at(features: pd.DataFrame) -> pd.DataFrame:
    """Lag by 1 bar: feature value at bar t becomes 'known at t+1' (causal L1)."""
    return features.shift(1)


# ────────────────────────────────────────────────────────────────────────────────
# Label builders (causal, intraday-flat)
# ────────────────────────────────────────────────────────────────────────────────

def forward_log_return(bars: pd.DataFrame, h_bars: int = 1,
                       intraday_flat: bool = True) -> pd.Series:
    """Forward log-return over h_bars, dropped if it crosses a session boundary."""
    logp = np.log(bars["close"])
    fwd = logp.shift(-h_bars) - logp
    if intraday_flat:
        norm = bars.index.normalize()
        same_day = pd.Series(norm).shift(-h_bars).values == norm
        fwd = fwd.where(same_day, np.nan)
    return fwd.rename(f"y_fwd_{h_bars}")


def triple_barrier_label(bars: pd.DataFrame, h_bars: int = 4,
                         tp_k: float = 1.0, sl_k: float = 1.0,
                         atr_n: int = 14) -> pd.DataFrame:
    """Triple-barrier label (López de Prado AFML ch.3) — causal, intraday-flat.

    Upper barrier = entry + tp_k * ATR ; lower barrier = entry - sl_k * ATR ;
    vertical barrier = entry + h_bars (forced exit). Returns columns:
      y_dir ∈ {-1, 0, +1} : barrier hit (sign of vertical exit if neither)
      y_ret               : realised log-return on the path until barrier hit
    """
    close = bars["close"]
    atr = _atr(bars["high"], bars["low"], close, atr_n)
    norm = bars.index.normalize()

    # Vectorised loop over bars: O(N * h)
    n = len(bars)
    y_dir = np.zeros(n, dtype=np.int8)
    y_ret = np.full(n, np.nan, dtype=np.float64)
    close_v = close.values
    atr_v = atr.values
    norm_v = norm.values

    for i in range(n - 1):
        tp = close_v[i] + tp_k * atr_v[i]
        sl = close_v[i] - sl_k * atr_v[i]
        if np.isnan(tp) or np.isnan(sl):
            continue
        end = min(i + h_bars, n - 1)
        # session boundary: cap at end-of-session
        for j in range(i + 1, end + 1):
            if norm_v[j] != norm_v[i]:
                end = j - 1
                break
        if end <= i:
            continue
        # walk path
        hit = 0
        ret = np.log(close_v[end] / close_v[i])
        for j in range(i + 1, end + 1):
            if close_v[j] >= tp:
                hit = +1
                ret = np.log(tp / close_v[i])
                break
            if close_v[j] <= sl:
                hit = -1
                ret = np.log(sl / close_v[i])
                break
        if hit == 0:
            hit = int(np.sign(ret)) if ret != 0 else 0
        y_dir[i] = hit
        y_ret[i] = ret

    return pd.DataFrame({"y_dir": y_dir, "y_ret": y_ret}, index=bars.index)


# ────────────────────────────────────────────────────────────────────────────────
# Convenience: full pipeline (load → resample → features → label)
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class InstrumentSpec:
    symbol: str
    hours: tuple[int, int]
    freq: str = "15min"
    label_h: int = 1


DEFAULT_UNIVERSE = [
    InstrumentSpec("EURUSD", hours=(7, 20),  freq="15min", label_h=1),
    InstrumentSpec("XAUUSD", hours=(7, 20),  freq="15min", label_h=1),
    InstrumentSpec("US500",  hours=(13, 21), freq="15min", label_h=1),
    InstrumentSpec("GER40",  hours=(7, 20),  freq="15min", label_h=1),
]


def build_panel(spec: InstrumentSpec, start: str | None = None,
                end: str | None = None,
                feature_spec: FeatureSpec | None = None) -> pd.DataFrame:
    """Load 1-min → resample to spec.freq + session filter → features (closed bars
    lagged) → forward-return label. Returns a tidy DataFrame:
      cols = FEATURE_NAMES ∪ {"y_fwd_h", "close", "spread"}
    """
    df = load_m1(spec.symbol)
    if start:
        df = df.loc[start:]
    if end:
        df = df.loc[:end]
    bars = resample_session(df, freq=spec.freq, hours=spec.hours)
    feat = as_known_at(build_features(bars, feature_spec))
    y = forward_log_return(bars, h_bars=spec.label_h)
    out = pd.concat([feat, y, bars[["close", "spread"]]], axis=1)
    return out.dropna(subset=["close"])
