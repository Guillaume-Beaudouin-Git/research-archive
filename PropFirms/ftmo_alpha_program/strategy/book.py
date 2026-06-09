"""
book.py — the FTMO-candidate book: a diversified intraday MR portfolio
=======================================================================

Design locked from the Phase-1 feasibility sweep:

  Instruments : EURUSD, GBPUSD (FX majors, Family-1) + XAUUSD (gold, Tier B).
                Index CFDs (US500/US100) are EXCLUDED from the core book: standalone
                they carry excess kurtosis 25-45 (opening-gap / disguised-momentum
                left tail) and fail the kurtosis gate — empirically confirming the
                white paper's family ranking (Family-1 first, Family-2 has the
                kurtosis killer).
  Bars        : 30-min, liquid hours 07-20 UTC (FX) / 13-21 UTC (US session).
  Signal      : z-score vs causal SMA(16); banded hysteresis entry |z|>2.0, exit |z|<0.5.
  Risk        : hard per-bar stop + intraday daily-stop (left-tail control); intraday-flat
                (no swap); per-instrument vol-targeting then inverse-kurtosis blend.
  Sizing      : book vol-targeted to sigma_d (the only sizing lever, L24); sigma_d is
                the speed-safety dial (lower sigma_d → higher pass-prob, longer time).

Weights are inverse-excess-kurtosis (down-weight fat-tailed sleeves). For honest OOS,
`build_book` can compute weights on a training window only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .fx_data import load_mt5_panel, load_dukascopy
from .intraday_fx_mr import build_bars, add_mr_signal, backtest_mr, BacktestConfig

# (symbol, source, session-hours, const_spread_points)
BOOK_INSTRUMENTS = [
    ("EURUSD", "panel", (7, 20), None),
    ("GBPUSD", "duka",  (7, 20), 3.0),
    ("XAUUSD", "panel", (7, 20), None),
]
FREQ = "30min"
WINDOW = 16
BASE_CFG = dict(z_entry=2.0, z_exit=0.5, daily_stop=0.008, markup=3.0)


@dataclass
class Book:
    daily: pd.Series                 # book daily returns, vol-targeted to sigma_d
    instrument_nets: pd.DataFrame    # per-instrument daily nets at unit (1%) sizing
    weights: pd.Series
    sigma_d: float
    instrument_metrics: dict


def _instrument_net(symbol: str, source: str, hours, const_spread,
                    start: str, end: str) -> tuple[pd.Series, dict]:
    df = (load_dukascopy(symbol) if source == "duka" else load_mt5_panel(symbol)).loc[start:end]
    bars = add_mr_signal(build_bars(df, freq=FREQ, hours=hours), window=WINDOW)
    cfg = BacktestConfig(sigma_target=0.01, const_spread_points=const_spread, **BASE_CFG)
    res = backtest_mr(bars, symbol, cfg)
    return res.daily_net, res.metrics


def inverse_kurtosis_weights(nets: pd.DataFrame) -> pd.Series:
    ks = {s: max(1.0, stats.kurtosis(nets[s].dropna().values, fisher=True, bias=False))
          for s in nets.columns}
    w = pd.Series({s: 1.0 / ks[s] for s in nets.columns})
    return w / w.sum()


def build_book(start: str = "2022-01-01", end: str = "2024-12-31",
               sigma_d: float = 0.007, weight_window: tuple[str, str] | None = None) -> Book:
    nets, metrics = {}, {}
    for sym, src, hours, cs in BOOK_INSTRUMENTS:
        nets[sym], metrics[sym] = _instrument_net(sym, src, hours, cs, start, end)
    df_all = pd.concat(nets, axis=1).dropna(how="all").fillna(0.0)

    # weights computed on a training window only (no look-ahead) if requested
    wsrc = df_all.loc[weight_window[0]:weight_window[1]] if weight_window else df_all
    w = inverse_kurtosis_weights(wsrc)

    blend = (df_all * w).sum(axis=1)
    sd = blend.std()
    daily = (blend / sd * sigma_d) if sd > 0 else blend
    return Book(daily=daily.rename("book_daily"), instrument_nets=df_all,
                weights=w, sigma_d=sigma_d, instrument_metrics=metrics)
