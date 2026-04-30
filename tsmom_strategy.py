"""
TSMOM Strategy — Time-Series Momentum on Crypto Perpetuals
Moskowitz, Ooi & Pedersen (2012) applied to crypto perpetuals.

Timing guarantee (verified in backtest):
  signal[t]    = sign(sum of log returns [t-lookback, t-1])
                 → rolling(lookback).sum().shift(1)
  vol_scalar[t] = clip(vol_target / realized_vol[t-1], 0.1, 2.0)
                 → rolling(vol_lookback).std().shift(1) * sqrt(365)
  position[t]  = signal[t] * vol_scalar[t]   ← both use data through t-1
  net_return[t] = position[t] * arith_return[t]   ← earn t's return

Zero look-ahead bias: position at t uses only data through t-1.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 365  # crypto trades 365 days/year (24/7)


class TSMOMStrategy:
    """
    Time-Series Momentum with volatility targeting.

    Parameters
    ----------
    lookback     : momentum signal window (days)
    vol_target   : annualized target volatility (fraction, e.g. 0.15 = 15%)
    vol_lookback : realized vol estimation window (days)
    fee_rate     : one-way taker fee (Hyperliquid default 0.035% = 0.00035)
    slippage     : one-way slippage estimate (0.05% = 0.0005)
    """

    def __init__(
        self,
        lookback: int = 28,
        vol_target: float = 0.15,
        vol_lookback: int = 30,
        fee_rate: float = 0.00035,
        slippage: float = 0.0005,
    ):
        self.lookback = lookback
        self.vol_target = vol_target
        self.vol_lookback = vol_lookback
        self.fee_rate = fee_rate
        self.slippage = slippage

    # ──────────────────────────────────────────────────────────────────────────
    # SIGNAL
    # ──────────────────────────────────────────────────────────────────────────

    def compute_signal(self, log_returns: pd.Series) -> pd.Series:
        """
        signal(t) = sign( sum of log_returns from t-lookback to t-1 )

        Implementation: rolling(lookback).sum() at t = sum[t-lookback+1 : t]
        After .shift(1): value at t = sum[t-lookback : t-1]  ← excludes day t
        Result: +1 (long), -1 (short), 0 (indeterminate — treated as flat)
        """
        cum_return = log_returns.rolling(self.lookback).sum().shift(1)
        return np.sign(cum_return)

    # ──────────────────────────────────────────────────────────────────────────
    # VOLATILITY SCALING
    # ──────────────────────────────────────────────────────────────────────────

    def compute_vol_scalar(self, log_returns: pd.Series) -> pd.Series:
        """
        position_scale(t) = clip(vol_target / realized_vol(t-1), 0.1, 2.0)

        realized_vol(t-1) = std(log_returns[t-vol_lookback : t-1]) * sqrt(365)
        .shift(1) ensures we only use data available at close of t-1.
        Clip prevents extreme leverage: [0.1x, 2.0x] of nominal position.
        """
        realized_vol = (
            log_returns.rolling(self.vol_lookback).std() * np.sqrt(TRADING_DAYS)
        )
        scalar = (self.vol_target / realized_vol).shift(1)
        return scalar.clip(0.1, 2.0)

    # ──────────────────────────────────────────────────────────────────────────
    # POSITION
    # ──────────────────────────────────────────────────────────────────────────

    def compute_positions(self, log_returns: pd.Series) -> pd.Series:
        """
        position(t) = signal(t) * vol_scalar(t)

        Both components incorporate .shift(1) internally → no look-ahead.
        Positive = long, negative = short.
        |position| ≈ 1.0 when realized vol ≈ vol_target.
        """
        signal = self.compute_signal(log_returns)
        vol_scalar = self.compute_vol_scalar(log_returns)
        return signal * vol_scalar

    # ──────────────────────────────────────────────────────────────────────────
    # FULL PIPELINE
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, log_returns: pd.Series) -> pd.DataFrame:
        """
        Run the strategy on a log-return series.

        Returns
        -------
        DataFrame with columns:
          signal        : +1, -1, or 0
          vol_scalar    : position size multiplier [0.1, 2.0]
          position      : actual position (signal * vol_scalar)
          arith_return  : arithmetic daily return (for P&L)
          gross_return  : position * arith_return
          turnover      : |position(t) - position(t-1)|
          cost          : turnover * (fee_rate + slippage)
          net_return    : gross_return - cost

        Cost accounting:
          Costs are incurred only on position changes (turnover), not daily.
          Round-trip cost = 2 * (fee_rate + slippage) = 0.17% at defaults.
          First non-NaN bar: entering from cash (prev position = 0).
        """
        # Arithmetic returns for P&L (log returns for signal — see compute_signal)
        arith_returns = np.exp(log_returns) - 1

        signal = self.compute_signal(log_returns)
        vol_scalar = self.compute_vol_scalar(log_returns)
        position = signal * vol_scalar

        gross_return = position * arith_returns

        # Turnover: absolute position change from previous day
        # Entering from 0 (cash) on first bar: turnover = |position|
        prev_position = position.shift(1).fillna(0.0)
        turnover = (position - prev_position).abs()

        cost = turnover * (self.fee_rate + self.slippage)
        net_return = gross_return - cost

        return pd.DataFrame(
            {
                "signal":       signal,
                "vol_scalar":   vol_scalar,
                "position":     position,
                "arith_return": arith_returns,
                "gross_return": gross_return,
                "turnover":     turnover,
                "cost":         cost,
                "net_return":   net_return,
            }
        )
