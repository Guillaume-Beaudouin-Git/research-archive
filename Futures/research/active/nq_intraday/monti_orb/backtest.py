"""
backtest.py — Monti ORB cost model, sizing, and metrics.

Costs per contract (NQ full):
  Commission:      $9.00 RT ($4.50/side)
  Exit slippage:   $5.00 RT (0.25 pts × $20, 1-tick exit)
  Entry slippage:  baked into entry_fill_px in signal.py (+ 0.25 pts)
  Total:           COST_PER_CONTRACT = $14.00 RT per contract

Sizing variants:
  "fixed"        : n_contracts_fixed NQ contracts every trade
  "vol_targeted" : contracts = max(1, round(target_dollar_risk / (ATR_20d × POINT_VALUE)))
                   target_dollar_risk calibrated to match median(contracts) = 1

Excess returns: daily P&L minus RF drag (DTB3-based, daily-pro-rated).
"""
from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm

POINT_VALUE: float         = 20.0    # USD per NQ point
COMMISSION_RT: float       = 9.0     # $4.50/side × 2
EXIT_SLIP_USD: float        = 5.0    # 0.25 pt × $20 = $5
COST_PER_CONTRACT: float   = COMMISSION_RT + EXIT_SLIP_USD  # $14.00
EQUITY_START: float        = 50_000.0


# ─────────────────────────────────────────────────────────────────────────────
# ATR helper
# ─────────────────────────────────────────────────────────────────────────────

def build_atr(df_1min: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    20-day ATR (points) from RTH daily OHLC derived from 1-min data.
    Returns Series indexed by date (date, not Timestamp).
    """
    rth = df_1min[
        (df_1min.index.time >= datetime.time(9, 30)) &
        (df_1min.index.time <= datetime.time(15, 59))
    ]
    daily = rth.resample("1B").agg(
        high=("high",  "max"),
        low=("low",   "min"),
        close=("close", "last"),
    ).dropna()

    prev_close = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - prev_close).abs(),
        (daily["low"]  - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.rolling(window, min_periods=window).mean()


# ─────────────────────────────────────────────────────────────────────────────
# Daily returns
# ─────────────────────────────────────────────────────────────────────────────

def daily_returns(
    trades: pd.DataFrame,
    sizing: str = "fixed",
    n_contracts_fixed: int = 1,
    target_dollar_risk: float | None = None,
    atr_series: pd.Series | None = None,
    rf_series: pd.Series | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Compute per-trade net P&L and daily excess returns.

    Parameters
    ----------
    trades            : output of monti_orb_signal (indexed by date)
    sizing            : "fixed" | "vol_targeted"
    n_contracts_fixed : for fixed sizing
    target_dollar_risk: for vol_targeted (USD per trade risk target)
    atr_series        : 20d ATR in points, indexed by Timestamp (business day)
    rf_series         : DTB3 daily %, indexed by date

    Returns
    -------
    trade_log  : per-trade DataFrame with net_usd column
    daily_net  : pd.Series of daily P&L net of RF, indexed by date, all trading days
    """
    active = trades[
        ~trades["exit_reason"].isin(["no_signal", "insufficient_orb"])
    ].copy()

    if active.empty:
        empty_daily = pd.Series(dtype=float)
        return pd.DataFrame(), empty_daily

    # Normalize index to tz-naive date for consistent arithmetic
    if active.index.tz is not None:
        active.index = active.index.tz_localize(None)
    active.index = active.index.normalize()

    if sizing == "vol_targeted":
        if target_dollar_risk is None or atr_series is None:
            raise ValueError("vol_targeted requires target_dollar_risk and atr_series")
        atr_idx = atr_series.copy()
        atr_idx.index = pd.to_datetime(atr_idx.index).normalize()
        if atr_idx.index.tz is not None:
            atr_idx.index = atr_idx.index.tz_localize(None)
        atr_aligned = atr_idx.reindex(active.index, method="ffill")
        atr_aligned = atr_aligned.fillna(float(atr_series.dropna().median()))
        raw_c = target_dollar_risk / (atr_aligned * POINT_VALUE)
        active["contracts"] = raw_c.clip(lower=1.0).round().astype(int)
    else:
        active["contracts"] = n_contracts_fixed

    active["gross_usd"] = active["pnl_pts"] * POINT_VALUE * active["contracts"]
    active["cost_usd"]  = COST_PER_CONTRACT * active["contracts"]
    active["net_usd"]   = active["gross_usd"] - active["cost_usd"]

    # Daily aggregation (max 1 trade/day by construction)
    daily_raw = active["net_usd"].copy()

    # Expand to all calendar business days in sample range
    all_days = pd.bdate_range(
        active.index.min().normalize(), active.index.max().normalize()
    )
    daily_full = daily_raw.reindex(all_days.normalize(), fill_value=0.0)
    daily_full.index = pd.to_datetime(daily_full.index).normalize()

    # Excess returns: subtract RF drag (DTB3 daily decimal × EQUITY_START)
    if rf_series is not None:
        rf_pct = rf_series.copy()
        rf_pct.index = pd.to_datetime(rf_pct.index).normalize()
        if rf_pct.index.tz is not None:
            rf_pct.index = rf_pct.index.tz_localize(None)
        rf_aligned = rf_pct.reindex(daily_full.index, method="ffill").fillna(0.0)
        rf_daily_usd = (rf_aligned / 100.0 / 252.0) * EQUITY_START
        daily_excess = daily_full - rf_daily_usd
    else:
        daily_excess = daily_full

    return active, daily_excess


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────

def sharpe_hac(daily_series: pd.Series, lag: int = 6) -> float:
    """
    Annualized Sharpe with HAC Newey-West SE (lag-6).
    Uses SM OLS with intercept-only design (np.ones) — matches engine.py exactly.
    Falls back to plain Sharpe if n < 48.
    """
    r = daily_series.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean = float(r.mean())
    std  = float(r.std(ddof=1))
    if std < 1e-9:
        return np.nan
    if n < 48:
        return mean / std * np.sqrt(252)
    reg = sm.OLS(r.values, np.ones(n)).fit(
        cov_type="HAC", cov_kwds={"maxlags": lag}
    )
    cp      = reg.cov_params()
    lrv     = float(cp[0, 0] if hasattr(cp, "__getitem__") else cp.iloc[0, 0]) * n
    hac_std = np.sqrt(max(lrv, 1e-24))
    if hac_std < 1e-12:
        return np.nan
    return mean / hac_std * np.sqrt(252)


def compute_metrics(
    trade_log: pd.DataFrame,
    daily_net: pd.Series,
    lag_hac: int = 6,
) -> dict:
    """Standard metric suite from trade_log + daily P&L series."""
    if trade_log.empty:
        return {"n_trades": 0}

    n = len(trade_log)
    winners = trade_log[trade_log["net_usd"] > 0]
    losers  = trade_log[trade_log["net_usd"] <= 0]
    win_rate = len(winners) / n
    gross_w  = float(winners["net_usd"].sum())
    gross_l  = abs(float(losers["net_usd"].sum()))
    pf       = gross_w / gross_l if gross_l > 0 else np.nan

    sr = sharpe_hac(daily_net, lag=lag_hac)

    # MaxDD on equity curve from EQUITY_START (avoids division-by-zero when cum P&L ≈ 0)
    equity     = EQUITY_START + daily_net.cumsum()
    dd_usd     = equity - equity.cummax()
    dd_pct     = dd_usd / equity.cummax()
    max_dd_pct = float(dd_pct.min()) if len(dd_pct) > 0 else np.nan
    max_dd_usd = float(dd_usd.min())

    # Monthly returns
    dn_clean = daily_net.copy()
    dn_clean.index = pd.to_datetime(dn_clean.index).normalize()
    monthly = dn_clean.resample("ME").sum()
    worst_month = float(monthly.min())

    return {
        "n_trades":        int(n),
        "win_rate":        round(float(win_rate), 4),
        "avg_net_usd":     round(float(trade_log["net_usd"].mean()), 2),
        "avg_gross_pts":   round(float(trade_log["pnl_pts"].mean()), 4),
        "profit_factor":   round(float(pf), 4) if np.isfinite(pf) else None,
        "total_net_usd":   round(float(trade_log["net_usd"].sum()), 2),
        "sharpe_hac":      round(float(sr), 4) if np.isfinite(sr) else None,
        "max_dd_pct":      round(float(max_dd_pct), 4),
        "max_dd_usd":      round(float(max_dd_usd), 2),
        "worst_month_usd": round(float(worst_month), 2),
        "best_day_usd":    round(float(daily_net.max()), 2),
        "worst_day_usd":   round(float(daily_net.min()), 2),
    }


def walk_forward(
    trades: pd.DataFrame,
    df_1min: pd.DataFrame,
    n_folds: int = 5,
    sizing: str = "fixed",
    n_contracts_fixed: int = 1,
    rf_series: pd.Series | None = None,
    target_dollar_risk: float | None = None,
) -> list[dict]:
    """
    Expanding walk-forward: train 60% / test 40% per fold (expanding train window).

    Returns list of dicts with fold metrics.
    """
    active = trades[
        ~trades["exit_reason"].isin(["no_signal", "insufficient_orb"])
    ].copy()
    if active.empty:
        return []

    if active.index.tz is not None:
        active.index = active.index.tz_localize(None)
    active.index = active.index.normalize()

    dates = sorted(active.index.unique())
    n_dates = len(dates)
    fold_size = n_dates // (n_folds + 1)

    folds = []
    for i in range(n_folds):
        train_end_idx  = fold_size * (i + 1)
        test_start_idx = train_end_idx
        test_end_idx   = min(train_end_idx + fold_size, n_dates)

        if test_end_idx <= test_start_idx:
            break

        test_dates = dates[test_start_idx:test_end_idx]
        test_trades = active[active.index.isin(test_dates)]

        if test_trades.empty:
            continue

        atr_s = None
        if sizing == "vol_targeted" and target_dollar_risk is not None:
            atr_s = build_atr(df_1min)

        tl, dn = daily_returns(
            test_trades,
            sizing=sizing,
            n_contracts_fixed=n_contracts_fixed,
            target_dollar_risk=target_dollar_risk,
            atr_series=atr_s,
            rf_series=rf_series,
        )
        if tl.empty:
            continue

        sr = sharpe_hac(dn)
        folds.append({
            "fold":            i + 1,
            "test_start":      str(test_dates[0].date()),
            "test_end":        str(test_dates[-1].date()),
            "n_trades":        len(tl),
            "sharpe_hac":      round(float(sr), 4) if np.isfinite(sr) else None,
            "total_net_usd":   round(float(tl["net_usd"].sum()), 2),
            "win_rate":        round(float((tl["net_usd"] > 0).mean()), 4),
        })

    return folds


def bootstrap_sharpe_ci(
    daily_net: pd.Series,
    n_boot: int = 10_000,
    seed: int = 42,
) -> tuple[float, float]:
    """Block bootstrap 95% CI for Sharpe (block = 5 days)."""
    rng  = np.random.default_rng(seed)
    vals = daily_net.dropna().values
    n    = len(vals)
    if n < 10:
        return (np.nan, np.nan)
    block = 5
    n_blocks = max(1, n // block)

    sharpes = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, n - block + 1), size=n_blocks)
        sample = np.concatenate([vals[s : s + block] for s in starts])[:n]
        m = sample.mean()
        s = sample.std(ddof=1)
        if s > 0:
            sharpes.append(m / s * np.sqrt(252))

    arr = np.array(sharpes)
    return (float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)))
