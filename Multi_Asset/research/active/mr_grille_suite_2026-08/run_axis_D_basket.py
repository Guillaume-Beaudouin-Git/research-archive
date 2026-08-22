"""
Axis D — basket-relative index spread. PREREGISTRATION.md §3 Axis D.
One-vs-three multilateral spread (NOT the already-closed pairwise index
cointegration axis -- pairs_cointegration_2026-08 covers that). 4 indices x 2
windows(k) x 2 exits = 16 cells.

The spread is a cumulative-log-return series (can be negative, not price-like),
so trades use ADDITIVE P&L (direction * (exit_level - entry_level)), not the
ratio-based ret_gross the rest of the grid uses for real price series -- this
module runs its own small forward-scan resolver rather than reusing
engine.backtest (which assumes multiplicative/price semantics).

Side note found while building this: because the "spread" updates once per bar
(a single point, not an OHLC range), a single scalar cannot simultaneously clear
both an upper (tp) and a lower (sl) symmetric threshold -- the tie-break ambiguity
that drives the tight-bracket artifact elsewhere in this programme is structurally
absent here. The bracket variant is still labelled PROVISIONAL per the
pre-registration: there is no real intrabar path to confirm what the spread did
*between* 15-min prints, only that no tie-break bias is possible.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

import dataload_ext as DX
import cellmetrics as CM

E0 = DX.E0

N_TRIALS = 115
H_BACKSTOP = 8
IDX4 = ["US100", "US500", "US30", "GER40"]

TARGET_VOL = 0.15
VOL_K = 20
CAP = 3.0


def load_aligned():
    frames = {s: DX.load15(s) for s in IDX4}
    common = frames[IDX4[0]].index
    for s in IDX4[1:]:
        common = common.intersection(frames[s].index)
    common = common.sort_values()
    logret = pd.DataFrame({s: np.log(frames[s]["close"].reindex(common)).diff() for s in IDX4})
    session_date = frames[IDX4[0]]["session_date"].reindex(common)
    return logret, session_date, common


def spread_level(logret: pd.DataFrame, sym: str):
    others = [c for c in logret.columns if c != sym]
    basket_ret = logret[others].mean(axis=1)
    r = (logret[sym] - basket_ret).fillna(0.0)
    return r.cumsum(), r


def scan_exits(level: np.ndarray, idx15: np.ndarray, direction: np.ndarray,
              sl_dist: np.ndarray, tp_dist: np.ndarray, H: int):
    """Forward scan on a single-valued (no intrabar range) series -- tie-free by
    construction (see module docstring). Mirrors the shared engine's max_hold /
    one-position-at-a-time discipline."""
    et_i, xt_i, dirs, epx, xpx, reason = [], [], [], [], [], []
    next_allowed = -1
    n = len(level)
    for k in range(idx15.size):
        i = idx15[k]
        e = i + 1
        if e >= n or e <= next_allowed:
            continue
        sl_d = sl_dist[i]; tp_d = tp_dist[i]
        if not (np.isfinite(sl_d) and np.isfinite(tp_d) and sl_d > 0 and tp_d > 0):
            continue
        entry_level = level[e]
        end = min(e + H - 1, n - 1)
        seg = level[e:end + 1]
        d = direction[k]
        if d > 0:
            tp_lvl = entry_level + tp_d; sl_lvl = entry_level - sl_d
            hit_tp = seg >= tp_lvl; hit_sl = seg <= sl_lvl
        else:
            tp_lvl = entry_level - tp_d; sl_lvl = entry_level + sl_d
            hit_tp = seg <= tp_lvl; hit_sl = seg >= sl_lvl
        tp_off = int(np.argmax(hit_tp)) if hit_tp.any() else None
        sl_off = int(np.argmax(hit_sl)) if hit_sl.any() else None
        if tp_off is None and sl_off is None:
            xoff = end - e; rs = "time"; xpv = level[end]
        elif sl_off is None:
            xoff = tp_off; rs = "tp"; xpv = tp_lvl
        elif tp_off is None:
            xoff = sl_off; rs = "sl"; xpv = sl_lvl
        else:
            xoff, rs = (sl_off, "sl") if sl_off <= tp_off else (tp_off, "tp")
            xpv = sl_lvl if rs == "sl" else tp_lvl
        xidx = e + xoff
        et_i.append(e); xt_i.append(xidx); dirs.append(d); epx.append(entry_level)
        xpx.append(xpv); reason.append(rs)
        next_allowed = xidx
    return et_i, xt_i, dirs, epx, xpx, reason


def run_cell(sym, level: pd.Series, ret: pd.Series, session_date: pd.Series, bpy: float,
            k: int, ename: str, cost: float):
    dist = E0.dist_zscore(level, k)
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    long_m, short_m = E0.entry_cross(d, 2.0, "signed")
    idx15 = np.where(long_m | short_m)[0]
    direction = np.where(long_m[idx15], 1.0, -1.0)

    vol_proxy = ret.rolling(VOL_K, min_periods=VOL_K).std(ddof=0).to_numpy(float)
    n = len(level)
    if ename == "TIME_ONLY_H8":
        sl_dist = np.full(n, 1e6); tp_dist = np.full(n, 1e6)
    else:
        sl_dist = 1.0 * vol_proxy; tp_dist = 1.0 * vol_proxy

    lvl_arr = level.to_numpy(float)
    et_i, xt_i, dirs, epx, xpx, reason = scan_exits(lvl_arr, idx15, direction, sl_dist, tp_dist, H_BACKSTOP)

    idx_arr = level.index
    entry_time = idx_arr[et_i]; exit_time = idx_arr[xt_i]
    trades = pd.DataFrame({
        "entry_time": entry_time, "exit_time": exit_time,
        "direction": np.asarray(dirs, float), "ret_gross": np.asarray(dirs, float) * (np.asarray(xpx) - np.asarray(epx)),
        "reason": reason,
    })

    # vol-target scale: the spread's own rolling realized vol of its bar increments,
    # same TARGET_VOL/K/CAP constants as the rest of the grid (engine_lib.vol_target_scale),
    # adapted because `ret` IS already the per-bar return (no pct_change of a price needed).
    rv = ret.rolling(VOL_K, min_periods=VOL_K).std(ddof=0) * np.sqrt(bpy)
    scale = (TARGET_VOL / rv).shift(1).clip(upper=CAP).reindex(level.index)

    days = pd.DatetimeIndex(session_date.dropna().drop_duplicates().to_numpy())
    out = CM.compute_metrics(trades, scale, cost, days, N_TRIALS)
    if len(trades):
        out["frac_sl"] = float((trades["reason"] == "sl").mean())
        out["frac_tp"] = float((trades["reason"] == "tp").mean())
        out["frac_time"] = float((trades["reason"] == "time").mean())
    return out


def main():
    t0 = time.time()
    logret, session_date, common = load_aligned()
    bars_per_day = session_date.groupby(session_date).size().median()
    bpy = float(bars_per_day) * 252.0

    rows = []
    for sym in IDX4:
        level, ret = spread_level(logret, sym)
        cost = DX.COST_RT_BPS[sym] / 1e4
        for k in (20, 50):
            for ename in ("TIME_ONLY_H8", "BRACKET_1xVOLPROXY_H8_PROVISIONAL"):
                res = run_cell(sym, level, ret, session_date, bpy, k, ename, cost)
                res.update(dict(block="D_basket_spread", sym=sym, freq="15min", k=k,
                               threshold=2.0, entry="CROSS", exit=ename,
                               provisional=(ename != "TIME_ONLY_H8")))
                rows.append(res)
        print(f"  {sym} done ({time.time()-t0:.1f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv("axis_D_results.csv", index=False)
    print(f"Wrote {len(out)} rows -> axis_D_results.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
