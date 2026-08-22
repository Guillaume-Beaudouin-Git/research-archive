"""
Module 2 — pin-bar / rejection-candle strategy with an EMA trend filter
(reimplementation of the gold H1 strategy from the "quant" YouTube video).

Pin-bar detection (per the video):
  * one wick >= wick_ratio (=2) x body,
  * body < body_max_frac (=0.33) of the candle range (high-low),
  * the opposite (smaller) wick <= body.
Bullish pin = long lower wick; bearish pin = long upper wick.

Trend filter (two EMAs): keep bullish pins only in an uptrend
(EMA50 > EMA200 and close > EMA50); bearish pins only in a downtrend
(EMA50 < EMA200 and close < EMA50).

Exit: ATR-based stop (atr_mult x ATR from entry), take-profit at rr:1, and a
50-bar time stop (~2 days on H1). Distances are returned in PRICE units for the
engine's price-distance mode, aligned to the signal bar.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import indicators as ind


def detect_pin_bars(df: pd.DataFrame, wick_ratio: float = 2.0,
                    body_max_frac: float = 0.33) -> pd.Series:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    rng = (h - l).replace(0.0, np.nan)
    body = (c - o).abs()
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    body_ok = body < body_max_frac * rng
    bull = body_ok & (lower >= wick_ratio * body) & (upper <= body)
    bear = body_ok & (upper >= wick_ratio * body) & (lower <= body)
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[bull.fillna(False)] = 1
    sig[bear.fillna(False)] = -1
    return sig


def apply_trend_filter(df: pd.DataFrame, pin: pd.Series, ema_fast: int = 50,
                       ema_slow: int = 200) -> pd.Series:
    c = df["close"]
    ef, es = ind.ema(c, ema_fast), ind.ema(c, ema_slow)
    up = (ef > es) & (c > ef)
    down = (ef < es) & (c < ef)
    out = pd.Series(0, index=df.index, dtype=int)
    out[(pin > 0) & up] = 1
    out[(pin < 0) & down] = -1
    return out


def atr_distances(df: pd.DataFrame, atr_n: int = 14, atr_mult: float = 1.5,
                  rr: float = 2.0):
    a = ind.atr(df["high"], df["low"], df["close"], atr_n)
    sl = (atr_mult * a).to_numpy(float)
    tp = (rr * atr_mult * a).to_numpy(float)
    return sl, tp


PARAMS = dict(wick_ratio=2.0, body_max_frac=0.33, ema_fast=50, ema_slow=200,
              atr_n=14, atr_mult=1.5, rr=2.0, max_hold=50)
