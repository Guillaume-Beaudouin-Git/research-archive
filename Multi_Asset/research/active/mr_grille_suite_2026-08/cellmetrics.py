"""
Shared metrics helper: turns a trades DataFrame (entry_time/exit_time/direction/
ret_gross) into the same gross/long/short/net/HAC/DSR/WF bundle the prior grid's
engine_lib.run_cell produces, by reusing engine_lib.trade_daily / leg_metrics
directly (no reimplementation of the significance machinery).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import dataload_ext as DX

E0 = DX.E0


def build_trades(entry_time, exit_time, direction, entry_px, exit_px, reason) -> pd.DataFrame:
    entry_time = pd.DatetimeIndex(entry_time)
    exit_time = pd.DatetimeIndex(exit_time)
    direction = np.asarray(direction, float)
    entry_px = np.asarray(entry_px, float)
    exit_px = np.asarray(exit_px, float)
    ret_gross = direction * (exit_px / entry_px - 1.0)
    return pd.DataFrame({"entry_time": entry_time, "exit_time": exit_time,
                        "direction": direction.astype(int), "entry_px": entry_px,
                        "exit_px": exit_px, "ret_gross": ret_gross,
                        "reason": np.asarray(reason)})


def compute_metrics(trades: pd.DataFrame, scale: pd.Series, cost_rt: float,
                    days: pd.DatetimeIndex, n_trials: int) -> dict:
    n_trades = int(len(trades))
    out = {"n_trades": n_trades}
    if n_trades < 10:
        out.update({k: float("nan") for k in
                   ["gross_sr", "gross_t", "gross_wf", "gross_dsr", "gross_bps_per_trade",
                    "long_sr", "long_t", "short_sr", "short_t", "net_sr", "net_t",
                    "avg_bars_held", "win_rate"]})
        return out

    def leg(sub):
        if sub.empty:
            return dict(sharpe=float("nan"), hac_t=float("nan"), dsr=float("nan"), wf=float("nan"))
        dr = E0.trade_daily(sub, scale, 0.0, days)
        return E0.leg_metrics(dr, E0.PPY_DAILY, n_trials)

    g_both = leg(trades)
    g_long = leg(trades[trades["direction"] > 0])
    g_short = leg(trades[trades["direction"] < 0])
    net_dr = E0.trade_daily(trades, scale, cost_rt, days)
    net = E0.leg_metrics(net_dr, E0.PPY_DAILY, n_trials)
    gross_bps = float(trades["ret_gross"].mean() * 1e4)
    out.update({
        "gross_sr": g_both["sharpe"], "gross_t": g_both["hac_t"], "gross_wf": g_both["wf"],
        "gross_dsr": g_both["dsr"], "gross_bps_per_trade": gross_bps,
        "long_sr": g_long["sharpe"], "long_t": g_long["hac_t"],
        "short_sr": g_short["sharpe"], "short_t": g_short["hac_t"],
        "net_sr": net["sharpe"], "net_t": net["hac_t"],
        "win_rate": float((trades["ret_gross"] > 0).mean()),
    })
    return out
