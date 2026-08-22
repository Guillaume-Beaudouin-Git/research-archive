"""
Axis B — trailing stop, M1-resolved. PREREGISTRATION.md §3 Axis B.
9 instruments x 2 trail multiples (1x/2x ATR20) = 18 cells. No fixed take-profit.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

import dataload_ext as DX
import m1_resolve as MR
import cellmetrics as CM
from run_axis_A_bracket import candidates_for, N_TRIALS, W_MINUTES

E0 = DX.E0


def run_cell_m1_trailing(sym, df15, long_m, short_m, atr20, trail_mult, ts1, ts1_dt, o1, h1, l1, c1, map15to1):
    idx15 = np.where(long_m | short_m)[0]
    direction = np.where(long_m[idx15], 1.0, -1.0)
    trail_arr = (trail_mult * atr20).to_numpy(float)

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
        td = trail_arr[i]
        if not (np.isfinite(td) and td > 0):
            continue
        res = MR.resolve_trailing_one(idx1, direction[k], td, o1, h1, l1, c1, W_MINUTES)
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
        hold_sec = (pd.DatetimeIndex(trades["exit_time"]) - pd.DatetimeIndex(trades["entry_time"])).total_seconds()
        out["avg_hold_min"] = float(np.asarray(hold_sec, dtype=float).mean() / 60.0)
        out["frac_trail"] = float((trades["reason"] == "trail").mean())
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
        for mult in (1.0, 2.0):
            res = run_cell_m1_trailing(sym, df15, long_m, short_m, atr20, mult,
                                       ts1, ts1_dt, o1, h1, l1, c1, map15to1)
            res.update(dict(block="B_trailing_stop", sym=sym, freq="15min->M1exit",
                           trail_mult=mult, entry="CROSS", exit=f"M1_TRAILING_{mult}xATR_H8"))
            rows.append(res)
        print(f"  {sym} done ({time.time()-t0:.1f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv("axis_B_results.csv", index=False)
    print(f"Wrote {len(out)} rows -> axis_B_results.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
