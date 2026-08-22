"""
Module 1 — the five "scalping" strategies described in the YouTube video,
reimplemented faithfully on 5-minute bars.

The video gives loose verbal rules; every non-specified parameter is documented
here as an explicit assumption so the replication is auditable. Signals are
returned as a state series at the CLOSE of each bar (+1 long / -1 short / 0 flat);
the 1-bar execution lag and intrabar SL/TP are handled centrally by engine.backtest
(signal at T-1, trade at T).
"""
from __future__ import annotations

import pandas as pd

from engine import indicators as ind

# Round-trip cost for crypto (commission + spread + slippage), per CLAUDE.md.
COST_RT = 0.0017
BREAKOUT = 20  # "close higher than the close 20 bars ago" (video, repeated for S3)


def s1_momentum_breakout(df: pd.DataFrame, fast: int = 20, slow: int = 50,
                         atr_n: int = 14, vol_ma: int = 50) -> pd.Series:
    """Momentum breakout + volatility-expansion filter.
    Long: fast SMA > slow SMA, ATR rising (vol expansion), close > close[-20],
    green candle. Short = mirror. (Video example: Ford 5m. SMA lengths not stated
    -> assume 20/50.)"""
    c, o = df["close"], df["open"]
    fast_ma, slow_ma = ind.sma(c, fast), ind.sma(c, slow)
    atr = ind.atr(df["high"], df["low"], c, atr_n)
    vol_expand = atr > atr.rolling(vol_ma, min_periods=vol_ma).mean()
    long_sig = (fast_ma > slow_ma) & vol_expand & (c > c.shift(BREAKOUT)) & (c > o)
    short_sig = (fast_ma < slow_ma) & vol_expand & (c < c.shift(BREAKOUT)) & (c < o)
    return long_sig.astype(int) - short_sig.astype(int)


def s2_sma_cross(df: pd.DataFrame, fast: int = 50, slow: int = 100) -> pd.Series:
    """Trend-state strategy: long while SMA50 > SMA100, short while below.
    Re-enters after each SL/TP exit (explains the high trade count in the video)."""
    c = df["close"]
    f, s = ind.sma(c, fast), ind.sma(c, slow)
    return (f > s).astype(int) - (f < s).astype(int)


def s3_ema_sma_zscore(df: pd.DataFrame, ema_n: int = 10, sma_n: int = 50,
                      z_n: int = 20, z_max: float = 2.0) -> pd.Series:
    """EMA10 > SMA50, close > close[-20], and z-score(close,20) <= 2 (don't chase
    over-extended moves). Short = mirror with z >= -2."""
    c = df["close"]
    e, s = ind.ema(c, ema_n), ind.sma(c, sma_n)
    z = ind.zscore(c, z_n)
    long_sig = (e > s) & (c > c.shift(BREAKOUT)) & (z <= z_max)
    short_sig = (e < s) & (c < c.shift(BREAKOUT)) & (z >= -z_max)
    return long_sig.astype(int) - short_sig.astype(int)


def s4_body_fraction_breakout(df: pd.DataFrame, bf_n: int = 10, bf_min: float = 0.1,
                              sma_n: int = 100) -> pd.Series:
    """Trend-following breakout that demands real (non-wicky) bodies.
    SMA(body_fraction,10) > 0.1, close > SMA100, close > close[-20]. Short = mirror."""
    c = df["close"]
    bf_ma = ind.sma(ind.body_fraction(df["open"], df["high"], df["low"], c), bf_n)
    s = ind.sma(c, sma_n)
    long_sig = (bf_ma > bf_min) & (c > s) & (c > c.shift(BREAKOUT))
    short_sig = (bf_ma > bf_min) & (c < s) & (c < c.shift(BREAKOUT))
    return long_sig.astype(int) - short_sig.astype(int)


def s5_vwma_buy_dip(df: pd.DataFrame, trend_n: int = 100, basis_n: int = 20,
                    k: float = 2.0) -> pd.Series:
    """Long-only "buy the dip" inside an uptrend. Uptrend = close > VWMA(100);
    dip = close below a VWMA(20)-based lower band (basis - k*std). One order at a
    time (engine enforces single position)."""
    c, v = df["close"], df["volume"]
    trend = ind.vwma(c, v, trend_n)
    basis = ind.vwma(c, v, basis_n)
    sd = c.rolling(basis_n, min_periods=basis_n).std(ddof=0)
    long_sig = (c > trend) & (c < basis - k * sd)
    return long_sig.astype(int)


STRATEGIES = {
    "S1_momentum_breakout": dict(fn=s1_momentum_breakout, sl=0.015, tp=0.03, allow_short=True),
    "S2_sma50_100_cross":   dict(fn=s2_sma_cross,          sl=0.010, tp=0.02, allow_short=True),
    "S3_ema_sma_zscore":    dict(fn=s3_ema_sma_zscore,     sl=0.017, tp=0.03, allow_short=True),
    "S4_body_fraction":     dict(fn=s4_body_fraction_breakout, sl=0.015, tp=0.03, allow_short=True),
    "S5_vwma_buy_dip":      dict(fn=s5_vwma_buy_dip,       sl=0.010, tp=0.02, allow_short=False),
}
