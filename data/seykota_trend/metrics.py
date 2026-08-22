"""Performance and risk metrics computed from the daily equity curve and trade log."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 365.25  # union calendar includes weekends (crypto); annualize on
                       # actual elapsed time, daily stats scaled by sqrt(n/yr)


def _ann_factor(idx: pd.DatetimeIndex) -> float:
    """Observed bars per year on this calendar."""
    years = (idx[-1] - idx[0]).days / 365.25
    return len(idx) / years if years > 0 else np.nan


def equity_metrics(ec: pd.DataFrame, rf_annual: float = 0.0) -> dict:
    eq = ec["equity"]
    r = eq.pct_change().dropna()
    n_yr = _ann_factor(eq.index)
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    rf_daily = (1 + rf_annual) ** (1 / n_yr) - 1
    ex = r - rf_daily

    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    vol = r.std(ddof=1) * np.sqrt(n_yr)
    sharpe = ex.mean() / r.std(ddof=1) * np.sqrt(n_yr) if r.std() > 0 else np.nan
    downside = r[r < 0].std(ddof=1) * np.sqrt(n_yr)
    sortino = ex.mean() * n_yr / downside if downside > 0 else np.nan

    peak = eq.cummax()
    dd = eq / peak - 1
    mdd = dd.min()
    # longest drawdown spell in days
    in_dd = dd < 0
    spells = (~in_dd).cumsum()[in_dd]
    longest_dd = (
        max(
            (g.index[-1] - g.index[0]).days
            for _, g in dd[in_dd].groupby(spells)
        )
        if in_dd.any()
        else 0
    )

    return {
        "start": str(eq.index[0].date()),
        "end": str(eq.index[-1].date()),
        "years": round(years, 2),
        "final_equity": round(eq.iloc[-1], 0),
        "total_return": eq.iloc[-1] / eq.iloc[0] - 1,
        "cagr": cagr,
        "ann_vol": vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": cagr / abs(mdd) if mdd < 0 else np.nan,
        "longest_dd_days": longest_dd,
        "skew": r.skew(),
        "kurtosis": r.kurtosis(),
        "var95_daily": r.quantile(0.05),
        "es95_daily": r[r <= r.quantile(0.05)].mean(),
        "avg_gross_exposure": ec["gross_exposure"].mean(),
        "max_gross_exposure": ec["gross_exposure"].max(),
        "pct_days_in_market": (ec["gross_exposure"] > 1e-9).mean(),
    }


def trade_metrics(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {}
    w = tr[tr.pnl_net > 0]
    l = tr[tr.pnl_net <= 0]
    gross_win, gross_loss = w.pnl_net.sum(), -l.pnl_net.sum()
    return {
        "n_trades": len(tr),
        "n_episodes": tr.groupby(["symbol", "exit_date"]).ngroups,
        "win_rate": len(w) / len(tr),
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else np.inf,
        "avg_win": w.pnl_net.mean(),
        "avg_loss": l.pnl_net.mean(),
        "win_loss_ratio": -w.pnl_net.mean() / l.pnl_net.mean() if len(l) else np.nan,
        "expectancy_R": tr.r_multiple.mean(),
        "best_trade_R": tr.r_multiple.max(),
        "worst_trade_R": tr.r_multiple.min(),
        "avg_holding_days": tr.holding_days.mean(),
        "total_costs": tr.costs.sum(),
    }


def per_asset_table(tr: pd.DataFrame, ec: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym, g in tr.groupby("symbol"):
        w = g[g.pnl_net > 0]
        l = g[g.pnl_net <= 0]
        rows.append({
            "symbol": sym,
            "trades": len(g),
            "win_rate": len(w) / len(g),
            "pnl_net": g.pnl_net.sum(),
            "profit_factor": (w.pnl_net.sum() / -l.pnl_net.sum()) if len(l) and l.pnl_net.sum() < 0 else np.inf,
            "avg_R": g.r_multiple.mean(),
            "long_share": (g.direction > 0).mean(),
        })
    return pd.DataFrame(rows).sort_values("pnl_net", ascending=False)


def monthly_table(ec: pd.DataFrame) -> pd.DataFrame:
    m = ec["equity"].resample("ME").last().pct_change()
    out = m.to_frame("ret")
    out["year"], out["month"] = out.index.year, out.index.month
    return out.pivot_table(index="year", columns="month", values="ret")


def block_bootstrap(
    returns: pd.Series, n_boot: int = 2000, block: int = 21, seed: int = 42
) -> pd.DataFrame:
    """Stationary block bootstrap CIs for Sharpe, CAGR, MaxDD."""
    rng = np.random.default_rng(seed)
    r = returns.values
    n = len(r)
    n_yr = _ann_factor(returns.index)
    stats = []
    for _ in range(n_boot):
        idx, out = rng.integers(0, n), []
        while len(out) < n:
            L = rng.geometric(1 / block)
            out.extend(r[(idx + np.arange(L)) % n])
            idx = rng.integers(0, n)
        b = np.array(out[:n])
        eqb = np.cumprod(1 + b)
        peak = np.maximum.accumulate(eqb)
        stats.append({
            "sharpe": b.mean() / b.std(ddof=1) * np.sqrt(n_yr),
            "cagr": eqb[-1] ** (n_yr / n) - 1,
            "max_dd": (eqb / peak - 1).min(),
        })
    s = pd.DataFrame(stats)
    return s.quantile([0.025, 0.05, 0.5, 0.95, 0.975])
