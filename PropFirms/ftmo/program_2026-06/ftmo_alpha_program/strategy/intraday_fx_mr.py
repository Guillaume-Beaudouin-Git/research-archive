"""
intraday_fx_mr.py — Family-1: intraday FX mean-reversion (majors)
==================================================================

Mechanism (white paper Table 4, Priority 1): microstructure overreaction /
liquidity-provision reversal. FX majors are near-random-walk at the daily scale but
exhibit exploitable *intraday* reversion of short-horizon deviations. This is the
native high-win-rate, symmetric-payoff, intraday-flat profile the symmetric barrier
rewards (L24) — the opposite of the lumpy momentum families that are structurally
capped (Strategy C).

Signal (causal, L1: decide at bar t, trade at t+1):
    z_t = (log P_t - SMA_W(log P)_t) / rolling_std_W,   predictor x_t = -z_t
    proportional MR position  pos_t = clip(-z_t / z_scale, -cap, +cap),
    forced flat outside liquid hours and at session close (intraday-flat → no swap).

Costs: full CFD round-trip spread on turnover (engine.cfd_costs), with a conservative
retail markup (L23b). Daily vol-targeting to sigma_d ~ 1% via a lagged rolling vol
(L3/L8). All suitability metrics are computed on the resulting daily-return distribution
(matches _audit/ftmo_suitability_screen.py).

Left-tail control (Risk register): a hard per-bar stop is applied to cap the single-day
loss well inside the 5% daily floor and to defend the kurtosis gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from .fx_data import resample_ohlc, session_filter, to_daily_returns
from engine.cfd_costs import CFDCostModel


# ──────────────────────────────────────────────────────────────────────────────
# Bars + signal
# ──────────────────────────────────────────────────────────────────────────────

def build_bars(df_1m: pd.DataFrame, freq: str = "5min",
               hours: tuple[int, int] = (7, 20)) -> pd.DataFrame:
    bars = session_filter(resample_ohlc(df_1m, freq), hours[0], hours[1])
    bars = bars.copy()
    bars["logret"] = np.log(bars["close"]).diff()
    # break returns across session/day gaps (no overnight carry of a "bar return")
    new_session = bars.index.normalize() != bars.index.normalize().to_series().shift(1).values
    bars.loc[new_session, "logret"] = np.nan
    return bars


def add_mr_signal(bars: pd.DataFrame, window: int = 24) -> pd.DataFrame:
    """z-score of log price vs causal rolling SMA; predictor x = -z (MR)."""
    logp = np.log(bars["close"])
    mean = logp.rolling(window).mean()
    std = logp.rolling(window).std(ddof=0)
    bars = bars.copy()
    bars["z"] = (logp - mean) / std.replace(0, np.nan)
    bars["x"] = -bars["z"]                       # MR predictor (causal, known at t)
    return bars


# ──────────────────────────────────────────────────────────────────────────────
# IC feasibility (Phase 1, step 2) — HAC Newey-West t-stat
# ──────────────────────────────────────────────────────────────────────────────

def compute_ic(bars: pd.DataFrame, maxlags: int = 12, fwd_bars: int = 1) -> dict:
    """
    IC of the MR predictor vs the forward return over the holding horizon (`fwd_bars`
    bars ahead), with a HAC (Newey-West) t-stat on the OLS slope (gate t > 2.5, L8).
    Aligned to respect L1: x_t known at t, captured return is t -> t+fwd_bars, and the
    forward window must not cross a session boundary.
    """
    logp = np.log(bars["close"])
    x = bars["x"]
    fwd = logp.shift(-fwd_bars) - logp
    norm = bars.index.normalize()
    same_session = pd.Series(norm).shift(-fwd_bars).values == norm
    d = pd.DataFrame({"x": x.values, "y": fwd.values}, index=bars.index).loc[same_session].dropna()
    ic = float(d["x"].corr(d["y"]))
    rank_ic = float(d["x"].corr(d["y"], method="spearman"))
    X = sm.add_constant(d["x"].values)
    ols = sm.OLS(d["y"].values, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return {"ic": ic, "rank_ic": rank_ic,
            "hac_t": float(ols.tvalues[1]), "hac_t_maxlags": maxlags,
            "slope": float(ols.params[1]), "n_obs": int(len(d))}


def per_trade_stats(bars: pd.DataFrame, z_entry: float = 2.0, z_exit: float = 0.5) -> dict:
    """
    Feasibility for a THRESHOLD strategy = the realised per-*trade* edge. Extract the
    actual non-overlapping trades implied by the banded position (enter at t+1 after a
    |z|>z_entry crossing, hold to reversion |z|<z_exit), then test whether the mean
    per-trade gross return is significantly > 0 (t-stat over independent trades). This
    is the honest statistic — unconditional IC and overlapping-bar tests are deflated by
    episode overlap (L12b).
    """
    day_id = bars.index.normalize().values
    gate = bars["entry_gate"] if "entry_gate" in bars.columns else None
    pos_state = banded_mr_position(bars["z"], day_id, z_entry, z_exit, entry_gate=gate)
    last = bars.index.normalize().to_series().shift(-1).values != bars.index.normalize()
    pos_state[last] = 0.0
    pos = pos_state.shift(1).fillna(0.0)
    gross_bar = pos * bars["logret"].fillna(0.0)
    seg = (pos != pos.shift(1)).cumsum()
    df = pd.DataFrame({"pos": pos.values, "gb": gross_bar.values})
    trades = df.groupby(seg.values).apply(
        lambda g: g["gb"].sum() if g["pos"].iloc[0] != 0 else np.nan).dropna().values
    if len(trades) < 30:
        return {"n_trades": int(len(trades)), "mean_bps": np.nan, "t_stat": np.nan,
                "win_rate": np.nan, "win_loss": np.nan}
    t = float(trades.mean() / trades.std(ddof=1) * np.sqrt(len(trades)))
    pos_t, neg_t = trades[trades > 0], trades[trades < 0]
    return {"n_trades": int(len(trades)), "mean_bps": float(trades.mean() * 1e4),
            "t_stat": t, "win_rate": float((trades > 0).mean()),
            "win_loss": float(abs(pos_t.mean() / neg_t.mean())) if len(neg_t) else np.nan,
            "trades_per_day": float(len(trades) / bars.index.normalize().nunique())}


def conditional_entry_edge(bars: pd.DataFrame, z_entry: float = 2.0,
                           fwd_bars: int = 6, maxlags: int = 12) -> dict:
    """
    The feasibility statistic that matters for a *threshold* MR strategy: the realised
    forward reversion conditional on an entry signal (|z| > z_entry), in the trade
    direction. Unconditional IC understates this — the edge lives at the extremes.
    HAC (Newey-West) t-stat on the conditional mean (gate t > 2.5).
    """
    logp = np.log(bars["close"])
    z = bars["z"]
    direction = -np.sign(z)                       # MR: fade the deviation
    fwd = logp.shift(-fwd_bars) - logp
    norm = bars.index.normalize()
    same_session = pd.Series(norm).shift(-fwd_bars).values == norm
    entry = (z.abs() > z_entry) & same_session
    cond = (direction * fwd)[entry].dropna()
    if len(cond) < 30:
        return {"n_entries": int(len(cond)), "mean_edge": np.nan, "hac_t": np.nan,
                "win_rate": np.nan}
    ols = sm.OLS(cond.values, np.ones(len(cond))).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return {"n_entries": int(len(cond)), "mean_edge": float(cond.mean()),
            "hac_t": float(ols.tvalues[0]), "win_rate": float((cond > 0).mean())}


# ──────────────────────────────────────────────────────────────────────────────
# Backtest (vectorised, cost-inclusive, vol-targeted)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    # Banded hysteresis MR: enter only at |z| extremes, hold to reversion.
    # This is the turnover-control lever that makes the edge survive CFD spread
    # (white paper killer: "L12 cost ceiling at high turnover").
    z_entry: float = 2.0             # enter when |z| > z_entry
    z_exit: float = 0.5              # exit when |z| < z_exit (reverted)
    sigma_target: float = 0.01       # daily vol target (σd ≈ 1%, n ≈ 10)
    vol_lookback: int = 63           # trading days for the lagged vol estimate
    max_leverage: float = 8.0        # cap on the vol-target scalar
    stop_bar_loss: float | None = None  # DISABLED: a per-bar loss *cap* that keeps the
                                         # position mechanically lifts the mean of a near-
                                         # zero-edge series (cap-and-continue artifact). A
                                         # real stop EXITS — modelled by `daily_stop`.
    daily_stop: float = 0.010        # intraday cumulative loss → FLATTEN for the day (legit:
                                     # optional stopping preserves the mean on a martingale)
    markup: float = 3.0              # retail-vs-feed spread markup (L23b, conservative)
    slippage_points: float = 0.0
    commission_rt: float = 0.0
    const_spread_points: float | None = None   # for feeds without a spread column


@dataclass
class BacktestResult:
    daily_net: pd.Series
    daily_gross: pd.Series
    daily_turnover: pd.Series
    metrics: dict = field(default_factory=dict)


def banded_mr_position(z: pd.Series, day_id: np.ndarray,
                       z_entry: float, z_exit: float,
                       entry_gate: pd.Series | None = None) -> pd.Series:
    """
    Vectorised hysteresis state machine: go long when z < -z_entry (price too low),
    short when z > +z_entry, flat when |z| < z_exit; otherwise hold the current state.
    Forward-filled within each session (no overnight carry).

    `entry_gate` (optional, causal boolean): if given, NEW entries are only initiated
    when the gate is True (exits and holds are unaffected). Used by the overreaction
    filter — only fade a deviation that was caused by a genuine liquidity spike.
    """
    raw = pd.Series(np.nan, index=z.index)
    long_e = z < -z_entry
    short_e = z > z_entry
    if entry_gate is not None:
        g = entry_gate.reindex(z.index).fillna(False).astype(bool)
        long_e = long_e & g
        short_e = short_e & g
    raw[long_e] = 1.0
    raw[short_e] = -1.0
    raw[z.abs() < z_exit] = 0.0
    pos = raw.groupby(day_id).ffill().fillna(0.0)
    return pos


def backtest_mr(bars: pd.DataFrame, symbol: str, cfg: BacktestConfig) -> BacktestResult:
    b = bars.copy()
    day_id = b.index.normalize().values
    # banded MR state, decided at t (uses z_t), applied to bar t+1 (L1)
    gate = b["entry_gate"] if "entry_gate" in b.columns else None
    pos_state = banded_mr_position(b["z"], day_id, cfg.z_entry, cfg.z_exit, entry_gate=gate)
    # intraday-flat: force exit on the last bar of each session
    last_of_day = b.index.normalize().to_series().shift(-1).values != b.index.normalize()
    pos_state[last_of_day] = 0.0
    pos = pos_state.shift(1).fillna(0.0)          # trade at next bar

    ret = b["logret"].fillna(0.0)
    # intraday daily stop: once cumulative same-day PnL (unit sizing) breaches
    # -daily_stop, flatten for the rest of the session (left-tail / kurtosis control).
    prov = pos * ret
    cum = prov.groupby(day_id).cumsum()
    breached = (cum <= -cfg.daily_stop)
    flat_after = (breached.groupby(day_id).cumsum().groupby(day_id).shift(1).fillna(0.0) >= 1)
    pos = pos.where(~flat_after, 0.0)

    gross_bar = pos * ret
    if cfg.stop_bar_loss is not None:                # optional, off by default
        gross_bar = gross_bar.clip(lower=-cfg.stop_bar_loss)

    # costs on turnover (one-way = half the round-trip spread)
    cost_model = CFDCostModel(symbol, markup=cfg.markup,
                              slippage_points=cfg.slippage_points,
                              commission_rt=cfg.commission_rt)
    if "spread" in b.columns and cfg.const_spread_points is None:
        spread_pts = b["spread"]
    else:
        spread_pts = pd.Series(cfg.const_spread_points or 2.0, index=b.index)
    rt_cost = cost_model.rt_cost_return(spread_pts, b["close"])
    turnover_bar = (pos - pos.shift(1).fillna(0.0)).abs()
    cost_bar = turnover_bar * 0.5 * np.asarray(rt_cost)

    # aggregate to daily (unit sizing)
    g_daily = to_daily_returns(gross_bar)
    c_daily = to_daily_returns(cost_bar).reindex(g_daily.index).fillna(0.0)
    turn_daily = to_daily_returns(turnover_bar).reindex(g_daily.index).fillna(0.0)

    # causal daily vol-targeting (lagged rolling vol of the gross series)
    trail_vol = g_daily.rolling(cfg.vol_lookback).std().shift(1)
    scale = (cfg.sigma_target / trail_vol).clip(upper=cfg.max_leverage).fillna(0.0)
    net_daily = (g_daily - c_daily) * scale
    gross_daily_s = g_daily * scale
    turn_daily_s = turn_daily * scale
    net_daily = net_daily.dropna()
    gross_daily_s = gross_daily_s.reindex(net_daily.index)
    turn_daily_s = turn_daily_s.reindex(net_daily.index)

    m = compute_metrics(net_daily, gross_daily_s, turn_daily_s, c_daily * scale)
    return BacktestResult(net_daily, gross_daily_s, turn_daily_s, m)


# ──────────────────────────────────────────────────────────────────────────────
# Metrics (daily distribution — matches the suitability screen)
# ──────────────────────────────────────────────────────────────────────────────

def compute_metrics(net: pd.Series, gross: pd.Series, turnover: pd.Series,
                    cost: pd.Series, periods: int = 252) -> dict:
    net = net.dropna()
    r = net.values
    mu, sd = r.mean(), r.std(ddof=1)
    pos, neg = r[r > 0], r[r < 0]
    sharpe_d = mu / sd if sd > 0 else 0.0
    gross_mu = gross.dropna().mean()
    cost_mu = cost.reindex(net.index).fillna(0.0).mean()
    return {
        "n_days": int(len(r)),
        "mean_daily": float(mu),
        "sigma_daily": float(sd),
        "daily_sharpe": float(sharpe_d),
        "ann_sharpe": float(sharpe_d * np.sqrt(periods)),
        "ann_return": float(mu * periods),
        "win_rate": float((r > 0).mean()),
        "avg_win": float(pos.mean()) if len(pos) else 0.0,
        "avg_loss": float(neg.mean()) if len(neg) else 0.0,
        "win_loss_ratio": float(abs(pos.mean() / neg.mean())) if len(pos) and len(neg) and neg.mean() != 0 else np.nan,
        "excess_kurtosis": float(stats.kurtosis(r, fisher=True, bias=False)),
        "skew": float(stats.skew(r, bias=False)),
        "max_dd": float(_max_dd(r)),
        # cost-gate inputs (annualised)
        "gross_ann_return": float(gross_mu * periods),
        "cost_ann_drag": float(cost_mu * periods),
        "avg_daily_turnover": float(turnover.dropna().mean()),
    }


def _max_dd(r: np.ndarray) -> float:
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((peak - eq).max())
