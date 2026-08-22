"""
strategy.py — Defined-risk intraday breakout (the execution vehicle).

This is NOT presented as an alpha source. Across 2020-2024 it has slightly
*negative* expectancy after costs (mean ~ -0.12R) — consistent with the report's
finding that EURUSD/GBPUSD are too efficient for simple edges to beat costs.
Its value for the FTMO challenge is its SHAPE: defined 1R risk per trade,
29% win rate, and strong positive skew (+3.4), i.e. a few large winners. That
right tail is what gives a path a chance to spike to +10% before ruin.

Backtest protocol (no look-ahead):
* Signals computed on the CLOSE of bar i (rolling high/low channel is shift(1)).
* Entry filled at the OPEN of bar i+1.
* Stops checked intrabar against bar high/low (conservative).
* Trades only inside the London/NY session (07:00-16:00 UTC), exit at session end.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from costs import PIP, round_trip_cost


def breakout_trades(
    df: pd.DataFrame,
    symbol: str,
    channel: int = 12,          # bars for the breakout channel (12 x 15m = 3h)
    atr_period: int = 20,
    atr_mult: float = 1.5,      # initial stop distance = atr_mult * ATR
    trail_mult: float = 2.5,    # trailing stop distance
    session: tuple[int, int] = (7, 16),
    cost_stress: float = 1.0,
) -> pd.DataFrame:
    """
    Run the breakout on a single symbol's OHLC frame.

    Returns one row per closed trade with columns:
        entry_time, direction, pnl_pips (net of cost), R (R-multiple, net).
    """
    df = df.copy()
    df["hr"] = df.index.hour
    df["atr"] = (df["high"] - df["low"]).rolling(atr_period).mean()
    hh = df["high"].rolling(channel).max().shift(1).values
    ll = df["low"].rolling(channel).min().shift(1).values
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    atr, hr = df["atr"].values, df["hr"].values
    idx = df.index
    cost = round_trip_cost(symbol, cost_stress)

    pos = 0
    entry = stop = risk = 0.0
    t0 = None
    rows = []
    for i in range(channel + atr_period, len(df) - 1):
        in_sess = session[0] <= hr[i] < session[1]
        if pos == 0:
            if not in_sess or np.isnan(atr[i]) or atr[i] <= 0:
                continue
            if c[i] > hh[i]:          # breakout up
                pos, entry, risk = 1, o[i + 1], atr_mult * atr[i]
                stop, t0 = entry - risk, idx[i]
            elif c[i] < ll[i]:        # breakout down
                pos, entry, risk = -1, o[i + 1], atr_mult * atr[i]
                stop, t0 = entry + risk, idx[i]
        else:
            done, exit_px = False, None
            if pos == 1:
                if l[i] <= stop:
                    exit_px, done = stop, True
                else:
                    stop = max(stop, c[i] - trail_mult * atr[i])
            else:
                if h[i] >= stop:
                    exit_px, done = stop, True
                else:
                    stop = min(stop, c[i] + trail_mult * atr[i])
            if not done and hr[i] >= session[1]:   # time-stop at session end
                exit_px, done = c[i], True
            if done:
                pnl = pos * (exit_px - entry) * PIP - cost
                rows.append({"entry_time": t0, "direction": pos,
                             "pnl_pips": pnl, "R": pnl / (risk * PIP)})
                pos = 0
    return pd.DataFrame(rows).set_index("entry_time")


def r_multiples(symbols=("EURUSD", "GBPUSD"), cost_stress: float = 1.0,
                split: str | None = None) -> pd.Series:
    """Pooled, time-sorted R-multiple series across symbols (drives the MC)."""
    from data import load
    parts = []
    for s in symbols:
        df = load(s, "15min", split)
        parts.append(breakout_trades(df, s, cost_stress=cost_stress)["R"])
    return pd.concat(parts).sort_index()
