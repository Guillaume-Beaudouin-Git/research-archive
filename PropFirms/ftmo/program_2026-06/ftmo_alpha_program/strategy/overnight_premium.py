"""
overnight_premium.py — Family-5: equity-index overnight premium (structural risk premium)
==========================================================================================

Structural prior (Cooper, Cliff & Gulen; Lou-Polk-Skouras "night and day"): equity indices
earn the bulk of their drift OVERNIGHT (close -> open), not intraday. This is a risk premium
(compensation for bearing overnight gap risk), NOT a microstructure inefficiency — it does
not decay the way the four reversal families did. Recon (IS 2022-24): US100 overnight 13%/yr,
Sharpe 0.85, daily kurtosis 2.5 (barrier-friendly); intraday ~0.

Why this is structurally different from the four nulls (clears the no-family-hop bar):
  • risk premium, not reversal;  • 1 trade/night => cost is a fixed tax, not turnover-scaled;
  • it HOLDS the risk overnight (the opposite of intraday-flat) — that holding IS the premium.

Pivotal venue variable = SWAP. Long index CFD pays financing overnight (net of dividends).
We separate GROSS (the premium) from NET-of-swap (what the retail CFD venue leaves) to decide:
GO / VENUE-swap failure (gross survives, reopens futures) / EDGE failure (premium decayed).

Constraints honoured: WEEKDAY holds only (FTMO Standard restricts weekend holding — no Fri->Mon),
triple swap on the Wednesday hold, conservative dealer markup. The hard left-tail control is
position SIZE (vol-targeting) + the daily-loss limit; an optional vol-regime filter skips
elevated-gap-risk nights (a frequency/shape lever, not a tail guarantee).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .fx_data import load_mt5_panel
from engine.cfd_costs import point_size

# index CFD point size (price decimals); spread column is in points
_CLOSE_H = 20.0     # ~US cash close in UTC (summer); DST slippage immaterial for overnight
_OPEN_H = 13.5      # ~US cash open in UTC


def extract_overnight(sym: str, start: str, end: str) -> pd.DataFrame:
    """
    Daily frame: overnight return (prev close -> today open), today's day-of-week, and the
    realised spread (points) at the close-entry and open-exit bars. Weekday holds only.
    """
    df = load_mt5_panel(sym).loc[start:end].copy()
    h = df.index.hour + df.index.minute / 60.0
    cmask, omask = h <= _CLOSE_H, h >= _OPEN_H
    day = df.index.normalize()
    close_px = df[cmask].groupby(day[cmask])["close"].last()
    close_sp = df[cmask].groupby(day[cmask])["spread"].last()
    open_px = df[omask].groupby(day[omask])["close"].first()
    open_sp = df[omask].groupby(day[omask])["spread"].first()
    d = pd.DataFrame({"open": open_px, "close": close_px,
                      "open_sp": open_sp, "close_sp": close_sp}).dropna()
    d["overnight"] = d["open"] / d["close"].shift(1) - 1.0
    d["entry_sp"] = d["close_sp"].shift(1)        # spread at the close we entered on
    d["dow"] = d.index.dayofweek
    # weekday holds only: today's open is Tue..Fri (held over a single weeknight)
    d = d[(d["dow"] >= 1) & (d["dow"] <= 4)]
    return d.dropna()


@dataclass
class OvernightConfig:
    sigma_target: float = 0.01
    vol_lookback: int = 63
    max_leverage: float = 4.0
    swap_bps_per_night: float = 2.0     # adverse long-CFD financing net of dividends (conservative)
    markup: float = 3.0                  # spread dealer markup (L23b)
    use_vol_filter: bool = False         # skip nights after elevated realised vol (gap-risk regime)
    vol_filter_mult: float = 1.5


@dataclass
class OvernightResult:
    daily_net: pd.Series
    daily_gross: pd.Series
    metrics: dict = field(default_factory=dict)


def backtest_overnight(d: pd.DataFrame, sym: str, cfg: OvernightConfig) -> OvernightResult:
    pt = point_size(sym)
    # round-trip spread cost: cross HALF the spread at entry (buy@ask vs mid) and half at
    # exit (sell@bid vs mid) => 0.5*(entry_spread + exit_spread), one full spread per RT.
    rt_spread = (0.5 * (d["entry_sp"].fillna(d["entry_sp"].median()) + d["open_sp"]) * pt
                 * cfg.markup / d["close"])
    # swap: per night, triple on the Wednesday hold (dow==2 today)
    nights = np.where(d["dow"].values == 2, 3.0, 1.0)
    swap = pd.Series(nights * cfg.swap_bps_per_night * 1e-4, index=d.index)

    pos = pd.Series(1.0, index=d.index)               # long the premium every eligible night
    if cfg.use_vol_filter:
        realised = d["overnight"].abs().rolling(20).mean().shift(1)
        base = d["overnight"].abs().rolling(60).mean().shift(1)
        pos = pos.where(~(realised > cfg.vol_filter_mult * base).fillna(False), 0.0)

    gross = pos * d["overnight"]
    cost = pos.abs() * (rt_spread + swap)             # 1 round trip/night when in
    net_unit = gross - cost

    # causal daily vol-targeting on the gross premium
    trail = gross.rolling(cfg.vol_lookback).std().shift(1)
    scale = (cfg.sigma_target / trail).clip(upper=cfg.max_leverage).fillna(0.0)
    net = (net_unit * scale).dropna()
    gross_s = (gross * scale).reindex(net.index)
    cost_s = (cost * scale).reindex(net.index)

    m = _metrics(net, gross_s, cost_s)
    # gross-only (zero swap, zero spread) for the edge-vs-venue split
    m["gross_only_ann_sharpe"] = float(gross.mean() / gross.std(ddof=1) * np.sqrt(252)) if gross.std() > 0 else 0.0
    return OvernightResult(net, gross_s, m)


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
