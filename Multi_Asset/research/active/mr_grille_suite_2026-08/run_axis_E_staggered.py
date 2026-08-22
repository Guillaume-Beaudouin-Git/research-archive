"""
Axis E — staggered (pyramided) entries. PREREGISTRATION.md §3 Axis E.
Conditioner: SMA20 z-score (canonical). SCALE_2STEP (1sigma/2sigma, 50/50) and
SCALE_3STEP (1sigma/2sigma/3sigma, 1/3 each), exit TIME_ONLY H=8 bars from the
FIRST fill. 9 instruments x 2 variants = 18 cells. The single full-size z0=2.0
CROSS/TIME_ONLY_H8 baseline is NOT re-run here -- it is Block 3 of
mr_intraday_grille_2026-08 (TIME_ONLY_H8 row), cited for comparison in RAPPORT.md.

Simplification flagged: round-trip cost is applied once per assembled position
(as if it were a single execution), not once per fill -- a multi-fill cost model
would charge slightly MORE for the staggered variants (more executions = more
spread paid), so this simplification is optimistic for Axis E, not pessimistic;
noted in RAPPORT.md rather than built (out of scope for a first pass).
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


def run_episodes(df15: pd.DataFrame, dist_arr: np.ndarray, no_entry: np.ndarray,
                 rungs: list[float], weights: list[float], H: int):
    n = len(df15)
    close = df15["close"].to_numpy(float)
    open_ = df15["open"].to_numpy(float)
    idx = df15.index
    trades = []
    i = 0
    in_ep = False
    direction = 0.0
    fills: list[tuple] = []
    filled = 0
    exit_bar = -1
    first_fill_bar = -1
    while i < n - 1:
        if not in_ep:
            zi = dist_arr[i]
            if (not no_entry[i]) and np.isfinite(zi) and abs(zi) >= rungs[0]:
                direction = 1.0 if zi <= -rungs[0] else -1.0
                first_fill_bar = i + 1
                if first_fill_bar >= n:
                    break
                fills = [(open_[first_fill_bar], weights[0])]
                filled = 1
                exit_bar = min(first_fill_bar + H - 1, n - 1)
                in_ep = True
            i += 1
            continue
        # in episode: maybe add the next rung
        if filled < len(rungs) and (i + 1) <= exit_bar and (i + 1) < n:
            zi = dist_arr[i]
            need = rungs[filled]
            cond = np.isfinite(zi) and ((direction > 0 and zi <= -need) or (direction < 0 and zi >= need))
            if cond and not no_entry[i]:
                fills.append((open_[i + 1], weights[filled]))
                filled += 1
        if i >= exit_bar:
            exit_px = close[exit_bar]
            wsum = sum(w for _, w in fills)
            ret = sum(w * direction * (exit_px / fp - 1.0) for fp, w in fills) / wsum
            trades.append((idx[first_fill_bar], idx[exit_bar], direction, ret, wsum, len(fills)))
            in_ep = False
        i += 1
    return trades


def run_variant(sym: str, df15: pd.DataFrame, rungs, weights, label: str) -> dict:
    close = df15["close"]
    dist = E0.dist_zscore(close, 20)
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    b2e = E0.bars_to_session_end(df15)
    no_entry = b2e <= H_BACKSTOP

    trades_raw = run_episodes(df15, d, no_entry, rungs, weights, H_BACKSTOP)
    if not trades_raw:
        return CM.compute_metrics(pd.DataFrame(columns=["direction", "ret_gross"]), None, 0, None, N_TRIALS)
    et, xt, dirs, rets, wsums, nfills = zip(*trades_raw)
    trades = pd.DataFrame({"entry_time": pd.DatetimeIndex(et), "exit_time": pd.DatetimeIndex(xt),
                          "direction": np.asarray(dirs, float), "ret_gross": np.asarray(rets, float),
                          "wsum": wsums, "nfills": nfills})

    bpy = DX.bars_per_year(df15)
    scale = E0.vol_target_scale(df15, bars_per_year=bpy)
    cost = DX.COST_RT_BPS[sym] / 1e4
    days = pd.DatetimeIndex(df15["session_date"].drop_duplicates().to_numpy())
    out = CM.compute_metrics(trades, scale, cost, days, N_TRIALS)
    out["avg_wsum"] = float(np.mean(wsums))
    out["frac_all_rungs_filled"] = float(np.mean(np.asarray(nfills) == len(rungs)))
    return out


def main():
    t0 = time.time()
    rows = []
    variants = [
        ("SCALE_2STEP", [1.0, 2.0], [0.5, 0.5]),
        ("SCALE_3STEP", [1.0, 2.0, 3.0], [1 / 3, 1 / 3, 1 / 3]),
    ]
    for sym in DX.INSTRUMENTS:
        df15 = DX.load15(sym)
        for label, rungs, weights in variants:
            res = run_variant(sym, df15, rungs, weights, label)
            res.update(dict(block="E_staggered_entry", sym=sym, freq="15min", entry=label,
                           exit="TIME_ONLY_H8", threshold="1/2/3sigma" if label == "SCALE_3STEP" else "1/2sigma"))
            rows.append(res)
        print(f"  {sym} done ({time.time()-t0:.1f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv("axis_E_results.csv", index=False)
    print(f"Wrote {len(out)} rows -> axis_E_results.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
