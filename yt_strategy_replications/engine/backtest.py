"""
Event-driven, one-position-at-a-time backtester with intrabar SL/TP resolution.

Core discipline (hard rule from CLAUDE.md): a signal at the CLOSE of bar t is
acted on at the OPEN of bar t+1 — "signal at T-1, trade at T". Enforced centrally
so strategies cannot peek.

Exit logic uses each bar's high/low. When both stop and target are touched inside
the same bar the outcome is ambiguous at this resolution; we resolve it
pessimistically (stop first) by default — the honest choice.

Two implementations are provided and proven equivalent (see tests/):
  * run_backtest            — explicit bar-by-bar loop, O(n_bars); the primary path;
  * run_backtest_vectorized — forward exit search; equivalent, faster only when
                              max_hold is small/bounded (ATR strategies).

Reported equity conventions:
  * compounded, full-notional, one position at a time  -> matches the "% of equity"
    convention TradingView strategies use for their headline %;
  * daily realized-P&L on fixed notional               -> the regularly sampled
    series used for Sharpe / HAC t-stat / DSR (the decision metrics).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import stats as S

_TRADE_COLS = ["entry_time", "exit_time", "direction", "entry_px", "exit_px",
               "bars_held", "reason", "ret_gross", "ret_net"]


def _build_trades(ts, et, xt, dirs, epx, xpx, held, reason, cost_rt):
    if not et:
        return pd.DataFrame(columns=_TRADE_COLS)
    et = np.asarray(et); xt = np.asarray(xt)
    dirs = np.asarray(dirs, float)
    epx = np.asarray(epx, float); xpx = np.asarray(xpx, float)
    ret_gross = dirs * (xpx / epx - 1.0)
    ret_net = ret_gross - cost_rt
    return pd.DataFrame({
        "entry_time": ts[et], "exit_time": ts[xt], "direction": dirs.astype(int),
        "entry_px": epx, "exit_px": xpx, "bars_held": np.asarray(held, int),
        "reason": reason, "ret_gross": ret_gross, "ret_net": ret_net,
    })


def run_backtest_vectorized(df, signal, *, sl_pct=None, tp_pct=None, sl_dist=None, tp_dist=None,
                            cost_rt=0.0017, max_hold=None, allow_long=True, allow_short=True,
                            sl_first_on_tie=True):
    """
    Vectorised simulation. df has columns open/high/low/close (timestamp index).
    `signal` is the decision at each bar close (+1/-1/0); entry is at next bar open.

    Percentage mode: sl_pct/tp_pct (fractions of entry). Price-distance mode
    (ATR strategies): sl_dist/tp_dist arrays (price units, aligned to signal bar).
    """
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    ts = df.index
    sig = np.nan_to_num(np.asarray(signal, float), nan=0.0)
    n = len(c)
    pct_mode = sl_pct is not None
    if not pct_mode:
        if sl_dist is None or tp_dist is None:
            raise ValueError("Provide either sl_pct/tp_pct or sl_dist/tp_dist.")
        sl_dist = np.asarray(sl_dist, float); tp_dist = np.asarray(tp_dist, float)

    et, xt, dirs, epx, xpx, held, reason = [], [], [], [], [], [], []
    i = 0
    while i < n - 1:
        d = sig[i]
        if d > 0 and allow_long:
            direction = 1
        elif d < 0 and allow_short:
            direction = -1
        else:
            i += 1
            continue
        e = i + 1
        entry_px = o[e]
        if not np.isfinite(entry_px):
            i += 1
            continue
        if pct_mode:
            if direction > 0:
                sl_px, tp_px = entry_px * (1 - sl_pct), entry_px * (1 + tp_pct)
            else:
                sl_px, tp_px = entry_px * (1 + sl_pct), entry_px * (1 - tp_pct)
        else:
            ds, dt = sl_dist[i], tp_dist[i]
            if not (np.isfinite(ds) and np.isfinite(dt) and ds > 0 and dt > 0):
                i += 1
                continue
            if direction > 0:
                sl_px, tp_px = entry_px - ds, entry_px + dt
            else:
                sl_px, tp_px = entry_px + ds, entry_px - dt

        end = n - 1 if max_hold is None else min(e + max_hold - 1, n - 1)
        hh = h[e:end + 1]; ll = l[e:end + 1]
        if direction > 0:
            sl_mask, tp_mask = ll <= sl_px, hh >= tp_px
        else:
            sl_mask, tp_mask = hh >= sl_px, ll <= tp_px
        sidx = int(np.argmax(sl_mask)) if sl_mask.any() else None
        tidx = int(np.argmax(tp_mask)) if tp_mask.any() else None

        if sidx is None and tidx is None:
            xbar = end
            xp = c[end]
            rs = "time" if max_hold is not None else "open_end"
        else:
            if sidx is None:
                pick, off = "tp", tidx
            elif tidx is None:
                pick, off = "sl", sidx
            elif sidx < tidx:
                pick, off = "sl", sidx
            elif tidx < sidx:
                pick, off = "tp", tidx
            else:
                pick, off = ("sl", sidx) if sl_first_on_tie else ("tp", tidx)
            xbar = e + off
            xp = sl_px if pick == "sl" else tp_px
            rs = pick

        et.append(e); xt.append(xbar); dirs.append(direction)
        epx.append(entry_px); xpx.append(xp); held.append(xbar - e + 1); reason.append(rs)
        i = xbar  # a signal at the exit bar may trigger a new entry next bar

    return _build_trades(ts, et, xt, dirs, epx, xpx, held, reason, cost_rt)


def run_backtest(df, signal, *, sl_pct=None, tp_pct=None, sl_dist=None,
                 tp_dist=None, cost_rt=0.0017, max_hold=None,
                 allow_long=True, allow_short=True, sl_first_on_tie=True):
    """Primary engine: explicit bar-by-bar loop, O(n_bars). df has columns
    open/high/low/close (timestamp index); `signal` is the decision at each bar
    close (+1/-1/0), executed at the next bar's open."""
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    ts = df.index
    sig = np.nan_to_num(np.asarray(signal, float), nan=0.0)
    n = len(c)
    pct_mode = sl_pct is not None
    if not pct_mode:
        sl_dist = np.asarray(sl_dist, float); tp_dist = np.asarray(tp_dist, float)

    et, xt, dirs, epx, xpx, held, reason = [], [], [], [], [], [], []
    pos = 0; entry_px = sl_px = tp_px = 0.0; entry_i = 0; bars = 0; pend = 0; sig_i = -1
    for t in range(n):
        if pos == 0 and pend != 0:
            ok = pct_mode or (np.isfinite(sl_dist[sig_i]) and np.isfinite(tp_dist[sig_i])
                              and sl_dist[sig_i] > 0 and tp_dist[sig_i] > 0)
            if ok and np.isfinite(o[t]):
                pos, entry_px, entry_i, bars = pend, o[t], t, 0
                if pct_mode:
                    if pos > 0:
                        sl_px, tp_px = entry_px * (1 - sl_pct), entry_px * (1 + tp_pct)
                    else:
                        sl_px, tp_px = entry_px * (1 + sl_pct), entry_px * (1 - tp_pct)
                else:
                    ds, dt = sl_dist[sig_i], tp_dist[sig_i]
                    if pos > 0:
                        sl_px, tp_px = entry_px - ds, entry_px + dt
                    else:
                        sl_px, tp_px = entry_px + ds, entry_px - dt
            pend = 0
        if pos != 0:
            bars += 1
            exited, xr, xp = False, "", 0.0
            if pos > 0:
                hit_sl, hit_tp = l[t] <= sl_px, h[t] >= tp_px
            else:
                hit_sl, hit_tp = h[t] >= sl_px, l[t] <= tp_px
            if hit_sl and hit_tp:
                xp, xr, exited = (sl_px, "sl", True) if sl_first_on_tie else (tp_px, "tp", True)
            elif hit_sl:
                xp, xr, exited = sl_px, "sl", True
            elif hit_tp:
                xp, xr, exited = tp_px, "tp", True
            if (not exited) and (max_hold is not None) and (bars >= max_hold):
                xp, xr, exited = c[t], "time", True
            if exited:
                et.append(entry_i); xt.append(t); dirs.append(pos)
                epx.append(entry_px); xpx.append(xp); held.append(bars); reason.append(xr)
                pos = 0
        if pos == 0 and pend == 0:
            s = sig[t]
            if s > 0 and allow_long:
                pend, sig_i = 1, t
            elif s < 0 and allow_short:
                pend, sig_i = -1, t
    if pos != 0:
        et.append(entry_i); xt.append(n - 1); dirs.append(pos)
        epx.append(entry_px); xpx.append(c[n - 1]); held.append(bars); reason.append("open_end")
    return _build_trades(ts, et, xt, dirs, epx, xpx, held, reason, cost_rt)


def _trading_days_per_year(index):
    days = pd.DatetimeIndex(pd.DatetimeIndex(index).normalize().unique())
    span_years = max((index[-1] - index[0]).days / 365.25, 1e-9)
    return days, span_years, len(days) / span_years


def daily_realized_returns(trades, df):
    """Per-day realized P&L on fixed notional, indexed over the data's trading days."""
    days, _, _ = _trading_days_per_year(df.index)
    if trades.empty:
        return pd.Series(0.0, index=days)
    s = (pd.Series(trades["ret_net"].to_numpy(float),
                   index=pd.DatetimeIndex(trades["exit_time"]).normalize())
         .groupby(level=0).sum())
    return s.reindex(days, fill_value=0.0)


def compute_metrics(trades, df, *, n_trials=1, label="", bootstrap=True):
    """Bundle headline + significance metrics for a single backtest run.

    `bootstrap=False` skips the (expensive) stationary bootstrap — use it for
    per-instrument sweeps and reserve the bootstrap for pooled/portfolio series.
    """
    close = df["close"].to_numpy(float)
    index = df.index
    days, span_years, tdays_yr = _trading_days_per_year(index)
    bh = float(close[-1] / close[0] - 1.0)
    base = {"label": label, "n_trades": int(len(trades)), "buy_hold_return": bh,
            "trading_days_per_year": round(tdays_yr, 1), "span_years": round(span_years, 2)}
    if trades.empty:
        base.update({k: float("nan") for k in [
            "total_return", "cagr", "sharpe", "sortino", "max_drawdown", "profit_factor",
            "win_rate", "expectancy", "hac_mean", "hac_tstat", "wf_score", "dsr",
            "bootstrap_p", "avg_bars_held", "pct_long", "frac_tp", "frac_sl", "frac_time"]})
        base["fold_sharpes"] = []
        return base

    rn = trades["ret_net"].to_numpy(float)
    eq = np.cumprod(1 + rn)
    total_ret = float(eq[-1] - 1)
    dr = daily_realized_returns(trades, df).to_numpy(float)

    folds = S.fold_metrics(dr, n_folds=5, periods_per_year=tdays_yr)
    dsr = S.deflated_sharpe_ratio(dr, n_trials=n_trials, periods_per_year=tdays_yr)
    hac_mean, hac_t = S.hac_tstat(dr, lags=6)
    mdd, _ = S.max_drawdown(eq)
    base.update({
        "total_return": total_ret,
        "cagr": S.cagr(total_ret, span_years),
        "sharpe": S.sharpe_ratio(dr, tdays_yr),
        "sortino": S.sortino_ratio(dr, tdays_yr),
        "max_drawdown": mdd,
        "profit_factor": S.profit_factor(rn),
        "win_rate": S.win_rate(rn),
        "expectancy": S.expectancy(rn),
        "avg_bars_held": float(trades["bars_held"].mean()),
        "pct_long": float((trades["direction"] > 0).mean()),
        "hac_mean": hac_mean,
        "hac_tstat": hac_t,
        "wf_score": folds["wf_score"],
        "fold_sharpes": folds["fold_sharpes"],
        "dsr": dsr.get("dsr", float("nan")),
        "sr_annual_obs": dsr.get("sr_annual", float("nan")),
        "sr0_annual_deflation": dsr.get("sr0_annual", float("nan")),
        "bootstrap_p": S.stationary_bootstrap_pvalue(dr) if bootstrap else float("nan"),
        "frac_tp": float((trades["reason"] == "tp").mean()),
        "frac_sl": float((trades["reason"] == "sl").mean()),
        "frac_time": float((trades["reason"] == "time").mean()),
    })
    return base


def equity_curves(trades, df):
    """Daily compounded strategy equity vs buy & hold, for plotting/reporting."""
    days, _, _ = _trading_days_per_year(df.index)
    if trades.empty:
        strat = pd.Series(1.0, index=days)
    else:
        dr = daily_realized_returns(trades, df)
        strat = (1 + dr).cumprod()
    close = df["close"]
    bh = close.groupby(close.index.normalize()).last().reindex(days).ffill()
    bh = bh / bh.iloc[0]
    return pd.DataFrame({"strategy": strat, "buy_hold": bh})
