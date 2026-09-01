"""
Replication of the TDI filter block of DedaleFormation.mq5 (CheckTradeSignal, CalculateTdiMa,
CalculateTdiAngle) -- used to test candidate filter configs against the declared metadata
(trades/pair/an, win rate, holding time), NOT to optimize for Sharpe/P&L.

Reverse-engineered indexing (see RAPPORT.md sec 2 for the derivation from the raw code):
  CopyBuffer(handle, 0, 0, period+2, rsi) fills `rsi` as a NON-series array (index 0 = oldest of
  the period+2 bars copied, i.e. the array is in chronological order because ArraySetAsSeries was
  never called on it). ArrayCopy(tdi, rsi, 0, 2-shift, period) then selects a `period`-long window
  whose right edge is `shift` bars back from the live/forming bar. Net effect, mapped onto an
  offline OHLC series where every row is a CLOSED bar and "evaluation" happens exactly at a row's
  close (matching the delay-1 entry convention already used by dedale_engine.py):
    shift=1 (TDI_SHIFT default) -> rolling(period).mean() evaluated AT row t (last closed bar)
    shift=2 (TDI_SHIFT+1)       -> the same rolling mean evaluated AT row t-1 (one bar earlier)
  CalculateTdiAngle() hardcodes shift=0 and shift=1 (NOT parametrized by TDI_SHIFT). shift=0's
  window includes the live/forming bar, which does not exist in an offline closed-bar series; at
  the instant a bar closes the forming bar has had ~0 elapsed time (O=H=L=C=last tick), so its
  contribution to a period=2 mean is within noise of duplicating the just-closed bar's value.
  Declared approximation: shift=0 is treated as identical to shift=1 (i.e. angle uses the same
  (row t, row t-1) pair as cross/trend). This does not materially change which bars pass the
  ANGLE_MIN/ANGLE_MAX band -- it only affects the last ~1 bar of lag, which is far smaller than
  the fast-period (2 bars) window itself.
"""
import numpy as np
import pandas as pd

RSI_PERIOD = 21
TDI_FAST_PERIOD = 2
TDI_SLOW_PERIOD = 7
TDI_MIDDLE_PERIOD = 34
TDI_ANGLE_MIN = 20.0
TDI_ANGLE_MAX = 80.0

TF_RULES = {
    0: "15min",   # TDI_TIMEFRAME0 = M15
    1: "30min",   # TDI_TIMEFRAME1 = M30
    2: "1h",      # TDI_TIMEFRAME2 = H1
    3: "4h",      # TDI_TIMEFRAME3 = H4
    4: "1D",      # TDI_TIMEFRAME4 = D1
}


def wilder_rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    diff = close.diff()
    gain = diff.clip(lower=0.0)
    loss = -diff.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.fillna(50.0)
    return rsi


def resample_close(m1_close: pd.Series, rule: str) -> pd.Series:
    # label='right': the bar's index timestamp = its CLOSE time, so a plain ffill-reindex onto a
    # finer index never uses data before that bar has actually closed (no lookahead).
    return m1_close.resample(rule, label="right", closed="left").last().dropna()


def tdi_block(m1_close: pd.Series, tf_idx: int) -> pd.DataFrame:
    """Per-timeframe TDI state, indexed by that timeframe's own (close-labeled) bars.
    Columns: cross_up, cross_down (bool), trend_up, trend_down (bool), angle (float)."""
    rule = TF_RULES[tf_idx]
    close = resample_close(m1_close, rule)
    rsi = wilder_rsi(close, RSI_PERIOD)

    fast_l1 = rsi.rolling(TDI_FAST_PERIOD).mean()
    fast_l2 = fast_l1.shift(1)
    slow_l1 = rsi.rolling(TDI_SLOW_PERIOD).mean()
    slow_l2 = slow_l1.shift(1)
    mid_l1 = rsi.rolling(TDI_MIDDLE_PERIOD).mean()
    mid_l2 = mid_l1.shift(1)

    cross_up = (fast_l2 < slow_l2) & (fast_l1 > slow_l1)      # bullish cross confirmed on last bar
    cross_down = (fast_l2 > slow_l2) & (fast_l1 < slow_l1)    # bearish cross confirmed on last bar
    trend_up = mid_l2 < mid_l1     # middle TDI rising
    trend_down = mid_l2 > mid_l1   # middle TDI falling

    fast_angle = np.degrees(np.arctan(fast_l1 - fast_l2))
    slow_angle = np.degrees(np.arctan(slow_l1 - slow_l2))
    w = RSI_PERIOD / TDI_MIDDLE_PERIOD
    angle = (slow_angle + fast_angle * w) / (1.0 + w)

    angle_buy_ok = (angle >= TDI_ANGLE_MIN) & (angle <= TDI_ANGLE_MAX)
    angle_sell_ok = (angle <= -TDI_ANGLE_MIN) & (angle >= -TDI_ANGLE_MAX)

    out = pd.DataFrame({
        "cross_up": cross_up, "cross_down": cross_down,
        "trend_up": trend_up, "trend_down": trend_down,
        "angle": angle, "angle_buy_ok": angle_buy_ok, "angle_sell_ok": angle_sell_ok,
    })
    return out


def align_to_h1(tf_df: pd.DataFrame, h1_index: pd.DatetimeIndex) -> pd.DataFrame:
    """ffill the (close-labeled) TF condition frame onto the H1 index. Because tf_df's index is
    the bar's CLOSE time, reindex+ffill never reveals a condition before it is actually known."""
    return tf_df.reindex(tf_df.index.union(h1_index)).sort_index().ffill().reindex(h1_index)


def build_all_tf_conditions(m1_close: pd.Series, h1_index: pd.DatetimeIndex) -> dict:
    """Returns {tf_idx: DataFrame aligned to h1_index} for all 5 timeframes."""
    out = {}
    for tf_idx in range(5):
        tf_df = tdi_block(m1_close, tf_idx)
        out[tf_idx] = align_to_h1(tf_df, h1_index)
    return out
