"""
momentum_strategy.py

Weekly-rebalanced cross-sectional momentum strategy.

Edge mechanism: rank a universe of crypto assets by recent momentum, go long
the top N (winners) and short the bottom N (losers). The portfolio is always
hedged (long + short ≈ market neutral). The edge comes from relative
mispricing, not absolute direction prediction.

Academic basis: Jegadeesh & Titman (1993), adapted to crypto by
Liu, Tsyvinski & Wu (2022) "Common Risk Factors in Cryptocurrency."

Signal timing (no look-ahead):
  - Compute formation return at Friday close using data UP TO t-1
    (skip day t = current Friday to avoid microstructure noise / bid-ask bounce)
  - Rank and select top/bottom N symbols
  - Execute at Monday open of the following week

Signal convention:
  longs  = list of symbols to go long  (top N by momentum)
  shorts = list of symbols to go short (bottom N by momentum)
"""

import numpy as np
import pandas as pd


class MomentumStrategy:
    """
    Cross-sectional momentum with weekly rebalancing.

    Parameters
    ----------
    formation_period : int
        Number of trailing bars for return computation. Default 14 (2 weeks).
    skip_days : int
        Most recent bars to skip (avoids bid-ask bounce). Default 1.
        Formation return = close[t - skip_days] / close[t - skip_days - formation_period] - 1
    n_long : int
        Number of top-momentum symbols to hold long. Default 4.
    n_short : int
        Number of bottom-momentum symbols to hold short. Default 4.
    long_pct : float
        Fraction of capital allocated to the long leg. Default 0.40 (40%).
    short_pct : float
        Fraction of capital allocated to the short leg. Default 0.40 (40%).
    rebalance_day : int
        Signal day of week (0=Mon … 4=Fri). Default 4 (Friday).
    stop_loss : float
        Per-symbol stop-loss fraction from entry price. Default 0.10 (10%).
    max_hold_weeks : int
        Maximum consecutive weeks to hold a position. Default 4.
    max_position_pct : float
        Hard cap: no single symbol > this fraction of equity. Default 0.15 (15%).
    """

    def __init__(
        self,
        formation_period: int   = 14,
        skip_days:        int   = 1,
        n_long:           int   = 4,
        n_short:          int   = 4,
        long_pct:         float = 0.40,
        short_pct:        float = 0.40,
        rebalance_day:    int   = 4,       # Friday
        stop_loss:        float = 0.10,
        max_hold_weeks:   int   = 4,
        max_position_pct: float = 0.15,
    ):
        self.formation_period = formation_period
        self.skip_days        = skip_days
        self.n_long           = n_long
        self.n_short          = n_short
        self.long_pct         = long_pct
        self.short_pct        = short_pct
        self.rebalance_day    = rebalance_day
        self.stop_loss        = stop_loss
        self.max_hold_weeks   = max_hold_weeks
        self.max_position_pct = max_position_pct

    # ── Signal computation ────────────────────────────────────────────────────

    def compute_weekly_signals(self, df: pd.DataFrame) -> list:
        """
        Generate one signal dict per rebalance day (Friday).

        Parameters
        ----------
        df : long-format DataFrame with columns: date, symbol, close.
             date must be sortable and convertible to pd.Timestamp.

        Returns
        -------
        List of dicts, one per valid signal date:
            signal_date  : pd.Timestamp — Friday close (signal computed here)
            exec_date    : pd.Timestamp — next Monday (trade executes here)
            longs        : list[str]    — top-N symbols by formation return
            shorts       : list[str]    — bottom-N symbols by formation return
            scores       : dict[str, float] — {symbol: formation_return}
            n_available  : int          — number of symbols ranked this week
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()

        # Wide close prices: rows = dates, cols = symbols
        close_wide = (
            df.pivot_table(index="date", columns="symbol", values="close")
            .sort_index()
        )
        all_dates = close_wide.index

        # All rebalance days (Fridays by default)
        rebal_dates = all_dates[all_dates.day_of_week == self.rebalance_day]

        signals     = []
        min_history = self.skip_days + self.formation_period   # bars needed before signal date

        for signal_date in rebal_dates:
            scores = {}

            for sym in close_wide.columns:
                series = close_wide[sym].dropna()
                if signal_date not in series.index:
                    continue

                iloc_at_signal = series.index.get_loc(signal_date)
                if iloc_at_signal < min_history:
                    continue                         # not enough history

                end_iloc   = iloc_at_signal - self.skip_days         # t-1 (yesterday)
                start_iloc = end_iloc - self.formation_period         # t-1-14

                p_end   = series.iloc[end_iloc]
                p_start = series.iloc[start_iloc]

                if p_start > 0 and np.isfinite(p_end) and np.isfinite(p_start):
                    scores[sym] = p_end / p_start - 1

            if len(scores) < self.n_long + self.n_short:
                continue    # universe too thin for this date

            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            longs  = [s for s, _ in ranked[: self.n_long]]
            shorts = [s for s, _ in ranked[-self.n_short :]]

            exec_date = self._find_exec_date(signal_date, all_dates)
            if exec_date is None:
                continue

            signals.append({
                "signal_date": signal_date,
                "exec_date":   exec_date,
                "longs":       longs,
                "shorts":      shorts,
                "scores":      scores,
                "n_available": len(scores),
            })

        return signals

    # ── Parameter access ─────────────────────────────────────────────────────

    def get_params(self) -> dict:
        return {
            "formation_period": self.formation_period,
            "skip_days":        self.skip_days,
            "n_long":           self.n_long,
            "n_short":          self.n_short,
            "long_pct":         self.long_pct,
            "short_pct":        self.short_pct,
            "rebalance_day":    self.rebalance_day,
            "stop_loss":        self.stop_loss,
            "max_hold_weeks":   self.max_hold_weeks,
            "max_position_pct": self.max_position_pct,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _find_exec_date(
        self, signal_date: pd.Timestamp, available_dates: pd.Index
    ) -> pd.Timestamp | None:
        """
        Return the first available trading date that is Monday (or later)
        after signal_date.  For crypto with weekend data: Friday + 3 days = Monday.
        For any data without Saturday/Sunday, Friday + 1 day is already Monday.
        """
        target = signal_date + pd.Timedelta(days=3)    # Friday → Monday
        future = available_dates[available_dates >= target]
        return future[0] if len(future) > 0 else None
