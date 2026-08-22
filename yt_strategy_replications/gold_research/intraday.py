"""
Gold intraday research engine — session/seasonality/momentum strategies on a
daily decision frequency (one position per day, held over a UTC trade window).

No look-ahead: a day's position uses only hours that close BEFORE the trade
window opens. Costs are charged per round trip on the position size (enter at the
window open, exit at the window close). Optional conditional vol-targeting scales
exposure inversely to trailing realised vol.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S  # noqa: E402

ANN = 252.0


def hourly_pivot(symbol="XAUUSD", anchor_hour=0):
    """Pivot of hourly log returns (anchored-day x UTC-hour). anchor_hour shifts the
    day boundary so cross-midnight windows (e.g. the overnight 21:00->13:00 session)
    fall inside one row; columns remain the real UTC hour for window selection."""
    g = data.load_h1(symbol)
    g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
    aday = (g.index - pd.Timedelta(hours=anchor_hour)).normalize()
    g = g.assign(aday=aday, hour=g.index.hour)
    piv = g.pivot_table(index="aday", columns="hour", values="lr", aggfunc="sum")
    piv = piv[piv.notna().sum(axis=1) >= 18].fillna(0.0)
    return piv


def win_ret(piv, hours):
    return piv[[h for h in hours if h in piv.columns]].sum(axis=1)


def backtest(piv, position, trade_hours, *, cost_bps=3.0, swap_bps=0.0, voltarget=False,
             vt_lookback=20, max_lev=3.0, label="", n_trials=1):
    """
    position : daily desired exposure (index = date), decided pre-window (will be
               shifted is NOT needed because it is already built from prior hours).
    trade_hours : UTC hours realised as the trade P&L for the day.
    Returns (net_daily_series, metrics dict).
    """
    r = win_ret(piv, trade_hours)
    pos = position.reindex(r.index).fillna(0.0)
    if voltarget:
        rv = r.rolling(vt_lookback, min_periods=vt_lookback).std().shift(1)
        target = rv.expanding(min_periods=vt_lookback).median()  # causal (no full-sample look-ahead)
        scale = (target / rv).clip(upper=max_lev).fillna(0.0)
        pos = pos * scale
    gross = pos * r
    # cost_bps = round-trip spread; swap_bps = overnight financing charged once per
    # night ONLY if the trade window is held across the broker rollover (else 0).
    turn = pos.abs()
    cost = turn * (cost_bps * 1e-4)
    swap = turn * (swap_bps * 1e-4)
    net = (gross - cost - swap).dropna()
    eq = (1 + net).cumprod()
    mdd, _ = S.max_drawdown(eq.to_numpy())
    _, t = S.hac_tstat(net.to_numpy())
    dsr = S.deflated_sharpe_ratio(net.to_numpy(), n_trials=n_trials, periods_per_year=ANN)
    folds = S.fold_metrics(net.to_numpy(), 5, ANN)
    m = dict(label=label, n_days=int(len(net)),
             sharpe_net=float(S.sharpe_ratio(net.to_numpy(), ANN)),
             sharpe_gross=float(S.sharpe_ratio(gross.dropna().to_numpy(), ANN)),
             hac_t=float(t), dsr=float(dsr.get("dsr", float("nan"))),
             mean_bps=float(net.mean() * 1e4), ann_ret=float(net.mean() * ANN),
             ann_vol=float(net.std() * np.sqrt(ANN)), maxdd=float(mdd),
             wf=float(folds["wf_score"]), fold_sharpes=folds["fold_sharpes"],
             avg_exposure=float(pos.abs().mean()), cost_bps=cost_bps)
    return net, m
