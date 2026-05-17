"""
funding_strategy.py

Rule-based funding rate mean reversion strategy.

Core insight: Hyperliquid funding is hourly and highly persistent (ACF lag-1 ≈ 0.87).
When funding is extremely high (z > +2), the market is over-leveraged long. Shorts
receive that elevated funding while waiting for mean reversion.  The reverse applies
for extremely low funding.

Signal convention (used by the backtester):
    +1  →  open SHORT   (z > +z_entry : funding extremely high)
    -1  →  open LONG    (z < -z_entry : funding extremely low)
     0  →  no new position

Exits are NOT encoded here — they are managed by the backtester's state machine
(z crosses zero, stop-loss, or max-hold timeout).
"""

import numpy as np
import pandas as pd


class FundingStrategy:
    """
    Rolling z-score funding mean reversion strategy.

    Parameters
    ----------
    lookback : int
        Rolling window (hours) for z-score mean and std.  Default 168 = 7 days.
    z_entry : float
        Absolute z-score threshold to open a position.  Default 2.0.
    z_exit : float
        Z-score level at which to close the position (mean reversion complete).
        Default 0.0 (crosses back through the mean).
    stop_loss : float
        Maximum adverse price move as a fraction of entry price.  Default 0.02 (2%).
    max_hold_hours : int
        Hard cap on position duration.  Default 72 h (3 days).
    position_size : float
        Fraction of capital allocated per trade.  Default 0.20 (20%).
    """

    def __init__(
        self,
        lookback: int = 168,
        z_entry: float = 2.0,
        z_exit: float = 0.0,
        stop_loss: float = 0.02,
        max_hold_hours: int = 72,
        position_size: float = 0.20,
    ):
        self.lookback = lookback
        self.z_entry = z_entry
        self.z_exit = z_exit
        self.stop_loss = stop_loss
        self.max_hold_hours = max_hold_hours
        self.position_size = position_size

    # ── Signal computation ────────────────────────────────────────────────────

    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add z_score, signal, and position columns to df.

        Uses funding_rate only (no mark_price needed for z-score).
        This allows the full funding history (including no-price period) to
        warm the rolling window before the backtestable price period starts.

        Parameters
        ----------
        df : DataFrame with at minimum: timestamp (sorted asc), funding_rate

        Returns
        -------
        df copy with added columns:
            z_score  : (funding_rate - rolling_mean) / rolling_std
                       rolling window = self.lookback, min_periods = lookback // 2
            signal   : +1 (short entry) | -1 (long entry) | 0 (no action)
                       Entry signals only.  Exits handled by the backtester.
            position : np.sign(z_score) cast to int
                       Regime indicator: +1 above mean, -1 below, 0 at mean.
        """
        df = df.copy().sort_values("timestamp").reset_index(drop=True)

        roll = df["funding_rate"].rolling(
            window=self.lookback,
            min_periods=max(self.lookback // 2, 2),
        )
        roll_mean = roll.mean()
        roll_std  = roll.std(ddof=1)

        # Guard against zero-std (perfectly flat funding periods)
        df["z_score"] = np.where(
            roll_std > 0,
            (df["funding_rate"] - roll_mean) / roll_std,
            0.0,
        )

        df["signal"] = 0
        df.loc[df["z_score"] >  self.z_entry, "signal"] =  1   # short
        df.loc[df["z_score"] < -self.z_entry, "signal"] = -1   # long

        # Regime indicator (for reference / debugging)
        df["position"] = np.sign(df["z_score"]).astype(int)

        return df

    # ── Parameter access ─────────────────────────────────────────────────────

    def get_params(self) -> dict:
        return {
            "lookback":       self.lookback,
            "z_entry":        self.z_entry,
            "z_exit":         self.z_exit,
            "stop_loss":      self.stop_loss,
            "max_hold_hours": self.max_hold_hours,
            "position_size":  self.position_size,
        }
