"""
xauusd_rangefade.py — Family-4: honest XAUUSD intraday range-fade (HARD STOP, no grid)
========================================================================================

Structural prior (mechanism note). Retail "gold scalper" EAs fade extensions of the
intraday range — strongest in the ASIAN session (00-08 UTC), where gold is low-vol and
range-bound (recon: |ret| 2-6 bps/30min vs 8-14 bps in the US data session). Their
advertised 90%+ win rate is an ARTEFACT of grid/martingale averaging into losers, NOT an
edge: a single CPI/FOMC trend day touches the FTMO -10% equity floor in one session. We
keep ONLY the mechanism (range mean-reversion in Asia) and reconstruct it honestly.

Toxicity NOT reproduced (the whole point):
  • one position at a time — NEVER averaging / grid / lot progression;
  • a HARD per-trade STOP that EXITS (realises the loss), never a cap-and-continue (L25);
  • intraday-flat (no swap, no overnight gap).

The optional regime FILTER is a *design variable* to cut trend contexts (lowers frequency
=> lowers cost and improves distribution shape). It is backward-looking and does NOT
protect against an intraday shock — the hard STOP bounds the left tail. Tested on/off.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .fx_data import resample_ohlc, session_filter, to_daily_returns
from .intraday_fx_mr import build_bars  # reuse causal bar builder
from engine.cfd_costs import CFDCostModel


def build_xau_bars(df_1m: pd.DataFrame, freq: str = "30min",
                   hours: tuple[int, int] = (0, 8), window: int = 16) -> pd.DataFrame:
    """Asia-session XAUUSD bars with a causal range z-score (deviation from recent range)."""
    bars = build_bars(df_1m, freq=freq, hours=hours)        # has close, spread, logret
    logp = np.log(bars["close"])
    mean = logp.rolling(window).mean()
    std = logp.rolling(window).std(ddof=0)
    bars = bars.copy()
    bars["z"] = (logp - mean) / std.replace(0, np.nan)
    return bars


def add_regime_filter(bars: pd.DataFrame, slope_bars: int = 32, slope_mult: float = 1.0) -> pd.Series:
    """
    Backward-looking range/trend filter: allow a fade only when the longer trend is FLAT
    (range), i.e. |EMA slope| below a multiple of its own trailing scale. Cuts trend-day
    contexts. NOT a tail protector (the stop is). Returns a causal boolean Series.
    """
    logp = np.log(bars["close"])
    ema = logp.ewm(span=slope_bars, adjust=False).mean()
    slope = (ema - ema.shift(slope_bars)).abs()
    scale = slope.rolling(slope_bars * 4).median()
    return (slope < slope_mult * scale).fillna(False)


@dataclass
class RangeFadeConfig:
    z_entry: float = 2.0
    z_exit: float = 0.5
    stop_loss: float = 0.005          # HARD per-trade stop (fraction of price); exits & flat
    sigma_target: float = 0.01
    vol_lookback: int = 63
    max_leverage: float = 8.0
    markup: float = 3.0               # CFD dealer markup (L23b)
    use_filter: bool = False
    slope_mult: float = 1.0


@dataclass
class RangeFadeResult:
    daily_net: pd.Series
    daily_gross: pd.Series
    trades: np.ndarray
    metrics: dict = field(default_factory=dict)


def backtest_rangefade(bars: pd.DataFrame, cfg: RangeFadeConfig) -> RangeFadeResult:
    """
    Stateful, one-position-at-a-time range fade with a HARD stop. L1: the position held
    during bar i was decided at the close of bar i-1; the stop is evaluated on the trade
    P&L realised through the current close (no look-ahead).
    """
    idx = bars.index
    close = bars["close"].values
    z = bars["z"].values
    day = idx.normalize().values
    filt = (add_regime_filter(bars, slope_mult=cfg.slope_mult).values
            if cfg.use_filter else np.ones(len(bars), dtype=bool))
    cm = CFDCostModel("XAUUSD", markup=cfg.markup)
    rt = np.asarray(cm.rt_cost_return(bars["spread"].values, close))  # RT cost in return units

    n = len(bars)
    gross = np.zeros(n)
    cost = np.zeros(n)
    pos = 0
    trade_pnl = 0.0
    stopped = False
    trades = []                       # realised per-trade gross returns

    for i in range(1, n):
        r = close[i] / close[i - 1] - 1.0
        gross[i] = pos * r            # pos decided at i-1, held during bar i
        if pos != 0:
            trade_pnl += pos * r      # realised through close[i]

        is_last = (i == n - 1) or (day[i + 1] != day[i] if i + 1 < n else True)
        new_pos = pos
        if pos != 0:
            if trade_pnl <= -cfg.stop_loss:          # HARD STOP — exit, realise loss
                new_pos = 0
                stopped = True
            elif abs(z[i]) < cfg.z_exit:             # reversion target — exit
                new_pos = 0
                stopped = False
        if is_last:
            new_pos = 0                              # intraday-flat
        if new_pos == 0 and not is_last:
            if abs(z[i]) < cfg.z_exit:
                stopped = False                      # excursion reset → re-enable entries
            if (not stopped) and filt[i] and not np.isnan(z[i]):
                if z[i] < -cfg.z_entry:
                    new_pos = 1
                elif z[i] > cfg.z_entry:
                    new_pos = -1

        if new_pos != pos:
            cost[i] += abs(new_pos - pos) * 0.5 * rt[i]
            if pos != 0 and new_pos == 0:
                trades.append(trade_pnl)
            if new_pos != 0 and pos == 0:
                trade_pnl = 0.0
        pos = new_pos

    g = pd.Series(gross, index=idx)
    c = pd.Series(cost, index=idx)
    g_daily = to_daily_returns(g)
    c_daily = to_daily_returns(c).reindex(g_daily.index).fillna(0.0)
    trail = g_daily.rolling(cfg.vol_lookback).std().shift(1)
    scale = (cfg.sigma_target / trail).clip(upper=cfg.max_leverage).fillna(0.0)
    net = ((g_daily - c_daily) * scale).dropna()
    gross_s = (g_daily * scale).reindex(net.index)
    cost_s = (c_daily * scale).reindex(net.index)

    m = _metrics(net, gross_s, cost_s)
    m["n_trades"] = len(trades)
    m["trades_per_day"] = len(trades) / max(1, len(np.unique(day)))
    tr = np.array(trades)
    m["trade_t"] = float(tr.mean() / tr.std(ddof=1) * np.sqrt(len(tr))) if len(tr) > 2 and tr.std() > 0 else np.nan
    m["trade_win_rate"] = float((tr > 0).mean()) if len(tr) else np.nan
    return RangeFadeResult(net, gross_s, tr, m)


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
        "net_daily": net,
    }


def _max_dd(r):
    eq = np.cumsum(r); peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((peak - eq).max())
