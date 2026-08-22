"""Métriques de performance et inférence statistique pour le backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def cagr(equity: pd.Series) -> float:
    yrs = (equity.index[-1] - equity.index[0]).days / 365.25
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else np.nan


def sharpe(r: pd.Series, rf_annual: float = 0.0) -> float:
    ex = r - rf_annual / TRADING_DAYS
    return np.sqrt(TRADING_DAYS) * ex.mean() / ex.std(ddof=1) if ex.std(ddof=1) > 0 else np.nan


def sortino(r: pd.Series) -> float:
    dn = r[r < 0]
    dd = np.sqrt((dn**2).sum() / len(r)) if len(dn) else np.nan
    return np.sqrt(TRADING_DAYS) * r.mean() / dd if dd and dd > 0 else np.nan


def max_drawdown(equity: pd.Series) -> tuple[float, pd.Series]:
    dd = equity / equity.cummax() - 1
    return dd.min(), dd


def newey_west_tstat(r: pd.Series, lags: int | None = None) -> float:
    """t-stat de la moyenne des rendements quotidiens, erreurs Newey-West (HAC).

    Corrige l'autocorrélation induite par les positions multi-jours.
    lags par défaut: floor(4*(n/100)^(2/9)) (Newey-West 1994).
    """
    x = r.values - 0.0
    n = len(x)
    if lags is None:
        lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
    mu = x.mean()
    e = x - mu
    s = e @ e / n
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        s += 2 * w * (e[l:] @ e[:-l]) / n
    se = np.sqrt(s / n)
    return mu / se if se > 0 else np.nan


def block_bootstrap_sharpe_ci(
    r: pd.Series, n_boot: int = 2000, block: int = 20,
    ci: tuple[float, float] = (2.5, 97.5), seed: int = 42,
) -> tuple[float, float]:
    """IC bootstrap par blocs circulaires sur le Sharpe annualisé."""
    rng = np.random.default_rng(seed)
    x = r.values
    n = len(x)
    n_blocks = int(np.ceil(n / block))
    stats = np.empty(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n, n_blocks)
        sample = np.concatenate([x[(s + np.arange(block)) % n] for s in starts])[:n]
        sd = sample.std(ddof=1)
        stats[b] = np.sqrt(TRADING_DAYS) * sample.mean() / sd if sd > 0 else np.nan
    lo, hi = np.nanpercentile(stats, ci)
    return lo, hi


def trade_stats(trades_df: pd.DataFrame) -> dict:
    closed = trades_df.dropna(subset=["pnl"]) if len(trades_df) else trades_df
    if len(closed) == 0:
        return {}
    wins = closed[closed["pnl"] > 0]
    losses = closed[closed["pnl"] <= 0]
    gross_win, gross_loss = wins["pnl"].sum(), -losses["pnl"].sum()
    return {
        "n_trades": int(len(closed)),
        "win_rate": len(wins) / len(closed),
        "avg_trade_ret": closed["ret"].mean(),
        "avg_win_ret": wins["ret"].mean() if len(wins) else np.nan,
        "avg_loss_ret": losses["ret"].mean() if len(losses) else np.nan,
        "payoff_ratio": (wins["ret"].mean() / abs(losses["ret"].mean()))
        if len(losses) and len(wins) else np.nan,
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else np.inf,
        "avg_holding_days": closed["holding_days"].mean(),
        "worst_trade_ret": closed["ret"].min(),
        "best_trade_ret": closed["ret"].max(),
        "trade_ret_tstat": closed["ret"].mean() / closed["ret"].std(ddof=1)
        * np.sqrt(len(closed)) if len(closed) > 1 else np.nan,
    }


def summary(equity: pd.Series, trades_df: pd.DataFrame, exposure: pd.Series | None = None,
            rf_annual: float = 0.0) -> dict:
    r = daily_returns(equity)
    mdd, _ = max_drawdown(equity)
    out = {
        "start": str(equity.index[0].date()),
        "end": str(equity.index[-1].date()),
        "total_return": equity.iloc[-1] / equity.iloc[0] - 1,
        "cagr": cagr(equity),
        "ann_vol": r.std(ddof=1) * np.sqrt(TRADING_DAYS),
        "sharpe": sharpe(r, rf_annual),
        "sortino": sortino(r),
        "max_drawdown": mdd,
        "calmar": cagr(equity) / abs(mdd) if mdd < 0 else np.nan,
        "nw_tstat": newey_west_tstat(r),
        "skew": r.skew(),
        "kurtosis": r.kurtosis(),
        "pct_days_in_market": float((exposure > 0).mean()) if exposure is not None else np.nan,
        "avg_exposure": float(exposure.mean()) if exposure is not None else np.nan,
    }
    out.update(trade_stats(trades_df))
    return out
