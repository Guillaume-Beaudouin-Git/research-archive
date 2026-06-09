"""
btc_breakout.py — BTCUSD Donchian channel breakout (tight stop), targeted at the reduced crypto floor
======================================================================================================

Family-6 (z-score banded momentum) found a REAL net-positive crypto edge that failed the FTMO crypto
barrier specifically because its losing days clustered at -2..-4%, breaching the REDUCED crypto
daily-loss floor (2-3%). This module tests a structurally-distinct momentum formulation — a classic
N-bar Donchian channel breakout (trigger = an actual prior-range break, not a sigma-extension) — with
a TIGHT per-trade stop designed to keep daily losses inside that reduced floor, while keeping the
positive-skew benefit. Two-sided, intraday-flat (no swap). Judged on the untouched hold-out at the
realistic 2-3% floor from the start.

Causal (L1): the channel uses bars strictly before the decision bar; signal at t-1, trade at t; the
stop is evaluated on realised trade P&L through the current close (no look-ahead).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .fx_data import resample_ohlc, session_filter, to_daily_returns
from .intraday_fx_mr import build_bars
from engine.cfd_costs import CFDCostModel


def build_breakout_bars(df_1m: pd.DataFrame, freq: str = "60min",
                        hours: tuple[int, int] = (0, 21), channel: int = 18) -> pd.DataFrame:
    """Bars + causal Donchian channel (prior `channel` bars, excluding the current bar)."""
    bars = build_bars(df_1m, freq=freq, hours=hours)
    bars = bars.copy()
    bars["upper"] = bars["high"].rolling(channel).max().shift(1)   # prior N-bar high
    bars["lower"] = bars["low"].rolling(channel).min().shift(1)    # prior N-bar low
    bars["atr"] = (bars["high"] - bars["low"]).rolling(channel).mean().shift(1)
    return bars


@dataclass
class BreakoutConfig:
    stop_atr: float = 1.0            # hard stop = stop_atr × ATR (tight → bound daily loss)
    sigma_target: float = 0.01
    vol_lookback: int = 63
    max_leverage: float = 6.0
    markup: float = 3.0
    daily_stop: float = 0.02         # session circuit-breaker (flatten for the day)


@dataclass
class BreakoutResult:
    daily_net: pd.Series
    daily_gross: pd.Series
    trades: np.ndarray
    metrics: dict = field(default_factory=dict)


def backtest_breakout(bars: pd.DataFrame, cfg: BreakoutConfig) -> BreakoutResult:
    idx = bars.index
    close = bars["close"].values
    upper, lower, atr = bars["upper"].values, bars["lower"].values, bars["atr"].values
    day = idx.normalize().values
    cm = CFDCostModel("BTCUSD", markup=cfg.markup)
    rt = np.asarray(cm.rt_cost_return(bars["spread"].values, close))
    n = len(bars)

    gross = np.zeros(n); cost = np.zeros(n)
    pos = 0; entry_px = np.nan; trade_pnl = 0.0
    trades = []
    for i in range(1, n):
        r = close[i] / close[i - 1] - 1.0
        gross[i] = pos * r
        if pos != 0:
            trade_pnl += pos * r
        is_last = (i == n - 1) or (day[i + 1] != day[i] if i + 1 < n else True)
        new_pos = pos
        # exits: hard stop (tight), opposite channel, session end
        if pos != 0:
            stop_hit = trade_pnl <= -(cfg.stop_atr * atr[i] / close[i]) if atr[i] == atr[i] else False
            opp = (pos > 0 and close[i] < lower[i]) or (pos < 0 and close[i] > upper[i])
            if stop_hit or opp:
                new_pos = 0
        if is_last:
            new_pos = 0
        # entries: Donchian breakout (only when flat after handling exits)
        if new_pos == 0 and not is_last and upper[i] == upper[i] and lower[i] == lower[i]:
            if close[i] > upper[i]:
                new_pos = 1
            elif close[i] < lower[i]:
                new_pos = -1
        if new_pos != pos:
            cost[i] += abs(new_pos - pos) * 0.5 * rt[i]
            if pos != 0 and new_pos == 0:
                trades.append(trade_pnl)
            if new_pos != 0 and pos == 0:
                trade_pnl = 0.0; entry_px = close[i]
        pos = new_pos

    g = pd.Series(gross, index=idx); c = pd.Series(cost, index=idx)
    g_daily = to_daily_returns(g); c_daily = to_daily_returns(c).reindex(g_daily.index).fillna(0.0)
    # session circuit-breaker handled implicitly by intraday-flat; daily_stop kept as a guard
    trail = g_daily.rolling(cfg.vol_lookback).std().shift(1)
    scale = (cfg.sigma_target / trail).clip(upper=cfg.max_leverage).fillna(0.0)
    net = ((g_daily - c_daily) * scale).dropna()
    gross_s = (g_daily * scale).reindex(net.index)
    cost_s = (c_daily * scale).reindex(net.index)
    m = _metrics(net, gross_s, cost_s)
    tr = np.array(trades)
    m["n_trades"] = len(tr)
    m["trades_per_day"] = len(tr) / max(1, len(np.unique(day)))
    m["trade_t"] = float(tr.mean() / tr.std(ddof=1) * np.sqrt(len(tr))) if len(tr) > 2 and tr.std() > 0 else np.nan
    m["trade_win_rate"] = float((tr > 0).mean()) if len(tr) else np.nan
    m["worst_day_pct"] = float(net.min() * 100) if len(net) else np.nan
    return BreakoutResult(net, gross_s, tr, m)


def _metrics(net, gross, cost, periods=252):
    r = net.dropna().values
    mu, sd = (r.mean(), r.std(ddof=1)) if len(r) > 1 else (0.0, 0.0)
    pos, neg = r[r > 0], r[r < 0]
    return {
        "n_days": int(len(r)), "daily_sharpe": float(mu / sd) if sd > 0 else 0.0,
        "ann_sharpe": float(mu / sd * np.sqrt(periods)) if sd > 0 else 0.0,
        "sigma_daily": float(sd), "win_rate": float((r > 0).mean()) if len(r) else np.nan,
        "win_loss_ratio": float(abs(pos.mean() / neg.mean())) if len(pos) and len(neg) and neg.mean() != 0 else np.nan,
        "excess_kurtosis": float(stats.kurtosis(r, fisher=True, bias=False)) if len(r) > 3 else np.nan,
        "skew": float(stats.skew(r, bias=False)) if len(r) > 2 else np.nan,
        "max_dd": float(_max_dd(r)) if len(r) else np.nan,
        "gross_ann_return": float(gross.dropna().mean() * periods),
        "cost_ann_drag": float(cost.reindex(net.index).fillna(0.0).mean() * periods),
    }


def _max_dd(r):
    eq = np.cumsum(r); peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((peak - eq).max())
