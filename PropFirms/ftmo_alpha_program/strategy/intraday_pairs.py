"""
intraday_pairs.py — Family-3: intraday relative-value (market-neutral index pairs)
===================================================================================

Mechanism (white paper Table 4, Priority 3): spread reversion between correlated CFDs.
Naturally low directional vol => high n => the symmetric barrier is easier. Admissible
ONLY intraday with an hours-scale half-life — the level cointegration spread is a
graveyard (recon: index-pair LEVEL half-life ~255-700h). We therefore trade the
*rolling-detrended divergence* (short-window z-score of a causal-hedge residual), whose
half-life is bounded by the window, not the level drift.

Construction (causal; L1):
  beta_t   = trailing rolling cov(r1,r2)/var(r2) over BETA_W bars, lagged 1 bar
  spread_t = log P1_t - beta_t * log P2_t
  z_t      = (spread_t - SMA_W(spread)) / rollstd_W(spread)
  banded MR on z (enter |z|>2, exit |z|<0.5), market-neutral, intraday-flat.

P&L per unit leg-1 notional:  r_spread = r1 - beta*r2.
Cost per round trip pays BOTH legs:  rt1 + |beta|*rt2  (this is the killer for pairs).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .fx_data import load_mt5_panel, resample_ohlc, session_filter, to_daily_returns
from .intraday_fx_mr import banded_mr_position
from engine.cfd_costs import CFDCostModel, point_size


def build_pair(sym1: str, sym2: str, start: str, end: str,
               freq: str = "30min", hours: tuple[int, int] = (13, 21),
               beta_w: int = 64, z_w: int = 16) -> pd.DataFrame:
    """Aligned pair bars with causal rolling hedge ratio, residual spread and z-score."""
    def load(s):
        df = load_mt5_panel(s).loc[start:end]
        b = session_filter(resample_ohlc(df, freq), *hours)
        return b[["close", "spread"]].rename(columns={"close": f"c_{s}", "spread": f"sp_{s}"})
    d = load(sym1).join(load(sym2), how="inner").dropna()
    lp1, lp2 = np.log(d[f"c_{sym1}"]), np.log(d[f"c_{sym2}"])
    r1, r2 = lp1.diff(), lp2.diff()
    # break returns across session/day gaps
    new_day = d.index.normalize() != pd.Series(d.index.normalize()).shift(1).values
    r1[new_day] = np.nan
    r2[new_day] = np.nan
    # causal rolling hedge ratio (trailing, lagged 1 bar). Fill session-gap NaNs with 0
    # so they don't poison the rolling windows (a 0-return gap bar is negligible over 64).
    r1f, r2f = r1.fillna(0.0), r2.fillna(0.0)
    cov = (r1f * r2f).rolling(beta_w).mean() - r1f.rolling(beta_w).mean() * r2f.rolling(beta_w).mean()
    var = r2f.rolling(beta_w).var()
    beta = (cov / var).shift(1).clip(0.2, 3.0)
    spread = lp1 - beta * lp2
    z = (spread - spread.rolling(z_w).mean()) / spread.rolling(z_w).std(ddof=0)
    out = pd.DataFrame({"r1": r1, "r2": r2, "beta": beta, "spread": spread, "z": z,
                        f"c_{sym1}": d[f"c_{sym1}"], f"c_{sym2}": d[f"c_{sym2}"],
                        f"sp_{sym1}": d[f"sp_{sym1}"], f"sp_{sym2}": d[f"sp_{sym2}"]},
                       index=d.index)
    out.attrs["sym1"], out.attrs["sym2"] = sym1, sym2
    return out


@dataclass
class PairConfig:
    z_entry: float = 2.0
    z_exit: float = 0.5
    sigma_target: float = 0.01
    vol_lookback: int = 63
    max_leverage: float = 8.0
    daily_stop: float = 0.010
    markup: float = 3.0


@dataclass
class PairResult:
    daily_net: pd.Series
    daily_gross: pd.Series
    metrics: dict = field(default_factory=dict)


def spread_half_life(z: pd.Series) -> float:
    """AR(1) half-life of the traded (detrended) z series, in bars."""
    import statsmodels.api as sm
    s = z.dropna()
    d = pd.DataFrame({"ds": s.diff(), "lag": s.shift(1)}).dropna()
    if len(d) < 50:
        return np.inf
    b = sm.OLS(d["ds"].values, sm.add_constant(d["lag"].values)).fit().params[1]
    return float(-np.log(2) / np.log(1 + b)) if -1 < b < 0 else np.inf


def backtest_pairs(pf: pd.DataFrame, cfg: PairConfig) -> PairResult:
    sym1, sym2 = pf.attrs["sym1"], pf.attrs["sym2"]
    day_id = pf.index.normalize().values
    pos_state = banded_mr_position(pf["z"], day_id, cfg.z_entry, cfg.z_exit)
    last = pf.index.normalize().to_series().shift(-1).values != pf.index.normalize()
    pos_state[last] = 0.0
    pos = pos_state.shift(1).fillna(0.0)

    beta = pf["beta"].fillna(0.0)
    r_spread = (pos * (pf["r1"].fillna(0.0) - beta * pf["r2"].fillna(0.0)))

    # daily stop (flatten for the session after a cumulative loss; legit risk control)
    cum = r_spread.groupby(day_id).cumsum()
    flat_after = ((cum <= -cfg.daily_stop).groupby(day_id).cumsum()
                  .groupby(day_id).shift(1).fillna(0.0) >= 1)
    pos = pos.where(~flat_after, 0.0)
    r_spread = pos * (pf["r1"].fillna(0.0) - beta * pf["r2"].fillna(0.0))

    # 2-leg cost: turnover pays leg1 spread + |beta| * leg2 spread
    cm1 = CFDCostModel(sym1, markup=cfg.markup)
    cm2 = CFDCostModel(sym2, markup=cfg.markup)
    rt1 = cm1.rt_cost_return(pf[f"sp_{sym1}"], pf[f"c_{sym1}"])
    rt2 = cm2.rt_cost_return(pf[f"sp_{sym2}"], pf[f"c_{sym2}"])
    turnover = (pos - pos.shift(1).fillna(0.0)).abs()
    cost_bar = turnover * 0.5 * (np.asarray(rt1) + beta.abs() * np.asarray(rt2))

    g_daily = to_daily_returns(r_spread)
    c_daily = to_daily_returns(cost_bar).reindex(g_daily.index).fillna(0.0)
    turn_daily = to_daily_returns(turnover).reindex(g_daily.index).fillna(0.0)

    trail = g_daily.rolling(cfg.vol_lookback).std().shift(1)
    scale = (cfg.sigma_target / trail).clip(upper=cfg.max_leverage).fillna(0.0)
    net = ((g_daily - c_daily) * scale).dropna()
    gross = (g_daily * scale).reindex(net.index)
    cost_s = (c_daily * scale).reindex(net.index)

    m = _metrics(net, gross, cost_s, turn_daily.reindex(net.index))
    m["half_life_bars"] = spread_half_life(pf["z"])
    return PairResult(net, gross, m)


def per_trade_pairs(pf: pd.DataFrame, cfg: PairConfig) -> dict:
    day_id = pf.index.normalize().values
    pos_state = banded_mr_position(pf["z"], day_id, cfg.z_entry, cfg.z_exit)
    last = pf.index.normalize().to_series().shift(-1).values != pf.index.normalize()
    pos_state[last] = 0.0
    pos = pos_state.shift(1).fillna(0.0)
    beta = pf["beta"].fillna(0.0)
    gb = pos * (pf["r1"].fillna(0.0) - beta * pf["r2"].fillna(0.0))
    seg = (pos != pos.shift(1)).cumsum()
    df = pd.DataFrame({"pos": pos.values, "gb": gb.values})
    trades = df.groupby(seg.values).apply(
        lambda g: g["gb"].sum() if g["pos"].iloc[0] != 0 else np.nan).dropna().values
    if len(trades) < 30:
        return {"n_trades": int(len(trades)), "t_stat": np.nan, "win_rate": np.nan,
                "trades_per_day": float(len(trades) / pf.index.normalize().nunique())}
    return {"n_trades": int(len(trades)),
            "t_stat": float(trades.mean() / trades.std(ddof=1) * np.sqrt(len(trades))),
            "win_rate": float((trades > 0).mean()), "mean_bps": float(trades.mean() * 1e4),
            "trades_per_day": float(len(trades) / pf.index.normalize().nunique())}


def _metrics(net, gross, cost, turnover, periods=252):
    r = net.dropna().values
    mu, sd = r.mean(), r.std(ddof=1)
    pos, neg = r[r > 0], r[r < 0]
    return {
        "n_days": int(len(r)), "daily_sharpe": float(mu / sd) if sd > 0 else 0.0,
        "ann_sharpe": float(mu / sd * np.sqrt(periods)) if sd > 0 else 0.0,
        "sigma_daily": float(sd), "win_rate": float((r > 0).mean()),
        "win_loss_ratio": float(abs(pos.mean() / neg.mean())) if len(pos) and len(neg) and neg.mean() != 0 else np.nan,
        "excess_kurtosis": float(stats.kurtosis(r, fisher=True, bias=False)),
        "max_dd": float(_max_dd(r)),
        "gross_ann_return": float(gross.dropna().mean() * periods),
        "cost_ann_drag": float(cost.reindex(net.index).fillna(0.0).mean() * periods),
        "avg_daily_turnover": float(turnover.dropna().mean()),
    }


def _max_dd(r):
    eq = np.cumsum(r); peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((peak - eq).max())
