"""
Axis C — sub-5-minute bars (1-min, 3-min). PREREGISTRATION.md §3 Axis C.
Canonical SMA20 z-score / CROSS entry, exit in {ATR_BRACKET_SYM 1x (native-bar
resolution -- IS M1 for the 1-min case, flagged artifact-exposed-but-untested for
3-min), TIME_ONLY} x H=8 NATIVE bars. 9 instruments x 2 freq x 2 exits = 36 cells.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd

import dataload_ext as DX

E0 = DX.E0
ind = DX.ind

N_TRIALS = 115
H_BACKSTOP = 8  # native bars, not minutes -- per PREREGISTRATION.md Axis C


def run_freq(sym: str, freq: str) -> list[dict]:
    df = DX.load_native(sym, freq)
    bpy = DX.bars_per_year(df)
    scale = E0.vol_target_scale(df, bars_per_year=bpy)
    cost = DX.COST_RT_BPS[sym] / 1e4
    close = df["close"]
    dist = E0.dist_zscore(close, 20)
    atr20 = ind.atr(df["high"], df["low"], df["close"], n=20)
    b2e = E0.bars_to_session_end(df)
    ne = b2e <= H_BACKSTOP
    d = np.nan_to_num(dist.to_numpy(float), nan=1e9)
    long_m, short_m = E0.entry_cross(d, 2.0, "signed")
    sig = E0.signal_from_masks(long_m & ~ne, short_m & ~ne, np.zeros_like(ne, dtype=bool))

    rows = []
    sl_b, tp_b = E0.exit_atr_bracket(atr20, 1.0, 1.0)
    sl_t, tp_t = E0.exit_time_only(len(df))
    for ename, sl, tp in (("ATR_BRACKET_SYM_1x_H8", sl_b, tp_b), ("TIME_ONLY_H8", sl_t, tp_t)):
        res = E0.run_cell(df, sig, sl, tp, H_BACKSTOP, scale, cost, bpy, n_trials=N_TRIALS)
        res.update(dict(block="C_subminute", sym=sym, freq=freq, entry="CROSS", exit=ename,
                       k=20, threshold=2.0))
        rows.append(res)
    return rows


def main():
    t0 = time.time()
    rows = []
    for sym in DX.INSTRUMENTS:
        for freq in ("1min", "3min"):
            rows.extend(run_freq(sym, freq))
        print(f"  {sym} done ({time.time()-t0:.1f}s)", flush=True)

    out = pd.DataFrame(rows)
    out.to_csv("axis_C_results.csv", index=False)
    print(f"Wrote {len(out)} rows -> axis_C_results.csv ({time.time()-t0:.1f}s total)")


if __name__ == "__main__":
    main()
