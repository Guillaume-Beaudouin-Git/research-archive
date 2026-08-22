"""
Axis A — wider symmetric brackets (1x/2x/3x ATR20), M1-resolved exit.
PREREGISTRATION.md §3 Axis A. 9 instruments x 3 multiples = 27 cells.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

import dataload_ext as DX
import m1_resolve as MR
import cellmetrics as CM

E0 = DX.E0
ind = DX.ind

N_TRIALS = 115
H_BACKSTOP_15 = 8
W_MINUTES = H_BACKSTOP_15 * 15  # 120


def candidates_for(df15: pd.DataFrame):
    close = df15["close"]
    dist = E0.dist_zscore(close, 20)
    atr20 = ind.atr(df15["high"], df15["low"], df15["close"], n=20)
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    long_m, short_m = E0.entry_cross(d, 2.0, "signed")
    b2e = E0.bars_to_session_end(df15)
    no_entry = b2e <= H_BACKSTOP_15
    long_m = long_m & ~no_entry
    short_m = short_m & ~no_entry
    return long_m, short_m, atr20


def run_cell_m1_bracket(sym: str, df15: pd.DataFrame, long_m, short_m, atr20, sl_mult: float,
                        tp_mult: float, ts1, ts1_dt, o1, h1, l1, c1, map15to1):
    idx15 = np.where(long_m | short_m)[0]
    if idx15.size == 0:
        return CM.compute_metrics(pd.DataFrame(columns=["direction", "ret_gross"]), None, 0, None, N_TRIALS)
    direction = np.where(long_m[idx15], 1.0, -1.0)
    sl_arr = (sl_mult * atr20).to_numpy(float)
    tp_arr = (tp_mult * atr20).to_numpy(float)

    et, xt, dirs, epx, xpx, reason = [], [], [], [], [], []
    next_allowed = -1
    n15 = len(df15)
    for k in range(idx15.size):
        i = idx15[k]
        e15 = i + 1
        if e15 >= n15:
            continue
        idx1 = map15to1[e15]
        if idx1 < 0 or idx1 <= next_allowed:
            continue
        sl_d = sl_arr[i]; tp_d = tp_arr[i]
        if not (np.isfinite(sl_d) and np.isfinite(tp_d) and sl_d > 0 and tp_d > 0):
            continue
        res = MR.resolve_bracket_one(idx1, direction[k], sl_d, tp_d, o1, h1, l1, c1, W_MINUTES)
        if res is None:
            continue
        et.append(df15.index[e15]); xt.append(ts1_dt[res["exit_idx"]])
        dirs.append(direction[k]); epx.append(res["entry_px"]); xpx.append(res["exit_px"])
        reason.append(res["reason"])
        next_allowed = res["exit_idx"]

    trades = CM.build_trades(et, xt, dirs, epx, xpx, reason)
    bpy = DX.bars_per_year(df15)
    scale = E0.vol_target_scale(df15, bars_per_year=bpy)
    cost = DX.COST_RT_BPS[sym] / 1e4
    days = pd.DatetimeIndex(df15["session_date"].drop_duplicates().to_numpy())
    out = CM.compute_metrics(trades, scale, cost, days, N_TRIALS)
    if len(trades):
        hold_sec = (pd.DatetimeIndex(trades["exit_time"])
                   - pd.DatetimeIndex(trades["entry_time"])).total_seconds()
        out["avg_hold_min"] = float(np.asarray(hold_sec, dtype=float).mean() / 60.0)
        out["frac_sl"] = float((trades["reason"] == "sl").mean())
        out["frac_tp"] = float((trades["reason"] == "tp").mean())
        out["frac_time"] = float((trades["reason"] == "time").mean())
    return out


def main():
    t0 = time.time()
    rows = []
    for sym in DX.INSTRUMENTS:
        df15 = DX.load15(sym)
        long_m, short_m, atr20 = candidates_for(df15)
        ts1, ts1_dt, o1, h1, l1, c1 = DX.m1_arrays(sym)
        ts15 = df15.index.values.astype("datetime64[ns]").astype(np.int64)
        map15to1 = DX.map_15to1(ts15, ts1)
        for mult in (1.0, 2.0, 3.0):
            res = run_cell_m1_bracket(sym, df15, long_m, short_m, atr20, mult, mult,
                                      ts1, ts1_dt, o1, h1, l1, c1, map15to1)
            res.update(dict(block="A_bracket_wide", sym=sym, freq="15min->M1exit",
                           bracket_mult=mult, entry="CROSS", exit=f"M1_BRACKET_SYM_{mult}x_H8"))
            rows.append(res)
        print(f"  {sym} done ({time.time()-t0:.1f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv("axis_A_results.csv", index=False)
    print(f"Wrote {len(out)} rows -> axis_A_results.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
