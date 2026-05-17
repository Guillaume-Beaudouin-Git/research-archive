"""
Naive spread backtest — signal existence test only.

Rules (no costs, no leverage):
  - Enter long spread  when Z[t-1] < -2  (spread too cheap)
  - Enter short spread when Z[t-1] >  2  (spread too rich)
  - Exit  long  spread when Z[t-1] > -0.5
  - Exit  short spread when Z[t-1] <  0.5

CRITICAL: Signal on bar t-1 close → position at bar t open.
Position is taken at open[t], using spread of close[t-1].

Spread P&L computed as log-return of the synthetic spread (long A / short B × β).
No costs, no leverage — pure signal existence test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ENTRY_THRESHOLD = 2.0
EXIT_THRESHOLD  = 0.5


def run_naive_backtest(
    close: pd.DataFrame,
    open_prices: pd.DataFrame,
    a: str,
    b: str,
    beta: float,
    alpha: float,
    z_series: pd.Series,
) -> pd.DataFrame:
    """
    Run naive spread backtest for a single pair.

    Signal: Z[t-1] (Z-score of spread residual on bar t-1 close)
    Position entry/exit: at bar t OPEN (1-bar lag enforced via .shift(1))
    P&L: log-return of spread = log(P_A) - beta * log(P_B)

    Returns DataFrame with columns:
      timestamp, z_signal, position, spread_ret, cum_pnl
    """
    # Align all series
    log_pa = np.log(close[a])
    log_pb = np.log(close[b])
    aligned = pd.concat([log_pa, log_pb, z_series], axis=1).dropna()
    aligned.columns = ["log_pa", "log_pb", "z"]

    # Check that open prices are available for execution
    if a in open_prices.columns and b in open_prices.columns:
        log_oa = np.log(open_prices[a])
        log_ob = np.log(open_prices[b])
        open_aligned = pd.concat([log_oa, log_ob], axis=1).dropna()
        open_aligned.columns = ["log_oa", "log_ob"]
        # Inner join on timestamp
        aligned = aligned.join(open_aligned, how="inner")
        use_open = True
    else:
        use_open = False

    # Z-score signal: shift by 1 bar (know Z at bar t-1, trade at bar t)
    z_lag = aligned["z"].shift(1)

    # Position signal: -1 (short spread), 0 (flat), +1 (long spread)
    # Long spread = long A, short B*beta
    # Short spread = short A, long B*beta
    position = pd.Series(0.0, index=aligned.index)
    pos = 0.0
    positions_list = []

    for t in range(len(aligned)):
        z_prev = z_lag.iloc[t]
        if np.isnan(z_prev):
            positions_list.append(0.0)
            continue

        # Entry rules
        if pos == 0.0:
            if z_prev < -ENTRY_THRESHOLD:
                pos = 1.0    # long spread (buy cheap)
            elif z_prev > ENTRY_THRESHOLD:
                pos = -1.0   # short spread (sell rich)
        # Exit rules
        elif pos == 1.0:
            if z_prev > -EXIT_THRESHOLD:
                pos = 0.0
        elif pos == -1.0:
            if z_prev < EXIT_THRESHOLD:
                pos = 0.0

        positions_list.append(pos)

    position = pd.Series(positions_list, index=aligned.index)

    # Spread log-return on bar t: log(spread[t]) - log(spread[t-1])
    # spread[t] = log_pa[t] - beta * log_pb[t]  (already log prices)
    spread_lv = aligned["log_pa"] - beta * aligned["log_pb"]
    spread_ret = spread_lv.diff()   # log-return of the synthetic spread

    # P&L: position[t] × spread_ret[t+1]
    # Position is entered at open of bar t, so return is realised at close of bar t
    # We use close-to-close for simplicity (conservative — open execution assumed same)
    # The 1-bar lag in position already handles the look-ahead constraint
    pnl = position.shift(1) * spread_ret   # shift(1): position from t-1, return at t

    cum_pnl = pnl.cumsum()

    result = pd.DataFrame({
        "timestamp": aligned.index,
        "z_signal":  z_lag,
        "position":  position,
        "spread_ret": spread_ret,
        "pnl":       pnl,
        "cum_pnl":   cum_pnl,
    })
    result = result.set_index("timestamp")
    return result


def compute_backtest_metrics(bt: pd.DataFrame, hours_per_year: int = 8760) -> dict:
    """Compute annualized metrics from hourly P&L series."""
    pnl = bt["pnl"].dropna()
    if len(pnl) == 0 or pnl.std() == 0:
        return {"sharpe": np.nan, "total_return": np.nan, "max_dd": np.nan, "n_trades": 0}

    ann_return = pnl.mean() * hours_per_year
    ann_vol    = pnl.std() * np.sqrt(hours_per_year)
    sharpe     = ann_return / ann_vol if ann_vol > 0 else np.nan

    # Max drawdown on cumulative P&L
    cum = bt["cum_pnl"].dropna()
    roll_max = cum.cummax()
    drawdown  = cum - roll_max
    max_dd    = float(drawdown.min())

    total_return = float(cum.iloc[-1]) if len(cum) > 0 else np.nan

    # Count round-trip trades
    pos_changes = bt["position"].diff().abs()
    n_entries = int((pos_changes > 0).sum() // 2)

    return {
        "sharpe":       round(sharpe, 3),
        "total_return": round(total_return, 4),
        "max_dd":       round(max_dd, 4),
        "n_trades":     n_entries,
    }
