"""Build hourly bars (true UTC index) from the canonical M1 estate.

Reads `data/deep_history_utc/<INST>_M1.csv` READ-ONLY from the main working dir
(caches are gitignored and absent from a fresh worktree) and writes one parquet
per instrument into a session-private cache directory.

Hourly bar convention: the bar labelled T covers [T, T+1h) in UTC. `close` is the
last M1 close inside it. A trade "entered at local hour h" uses the close of the
bar labelled (h-1) local, i.e. the price observable AT h:00. See build_map.py.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

SRC = "<HOME>/Desktop/Algo_claude/data/deep_history_utc"
CACHE = os.environ.get(
    "GROSSMAP_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/grossmap_cache",
)

INSTRUMENTS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "EURGBP", "EURJPY", "AUDJPY",
    "US500", "US100", "US30", "GER40",
    "XAUUSD", "XAGUSD", "COPPER",
    "UKOIL", "USOIL",
]


def build(inst: str) -> pd.DataFrame:
    path = f"{SRC}/{inst}_M1.csv"
    df = pd.read_csv(path, usecols=["timestamp_utc", "open", "high", "low", "close", "spread"])
    df["ts"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"]).set_index("ts").sort_index()

    # zero-range diagnostic (L60): share of M1 bars with high == low
    zero_range = float((df["high"].to_numpy() == df["low"].to_numpy()).mean())

    df["sp_zero"] = (df["spread"] == 0).astype("float32")
    g = df.resample("1h")
    out = pd.DataFrame(
        {
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "nbars": g["close"].count(),
            "spread_med": g["spread"].median(),
            "spread_zero_frac": g["sp_zero"].mean(),
        }
    )
    out = out[out["nbars"] > 0]
    out.attrs["zero_range_m1"] = zero_range
    return out


def main() -> None:
    os.makedirs(CACHE, exist_ok=True)
    diag = []
    for inst in INSTRUMENTS:
        dst = f"{CACHE}/{inst}_H1.parquet"
        if os.path.exists(dst):
            print(f"{inst}: cached", flush=True)
            continue
        t0 = time.time()
        out = build(inst)
        out.to_parquet(dst)
        diag.append((inst, out.attrs["zero_range_m1"], len(out), str(out.index.min()), str(out.index.max())))
        print(f"{inst}: {len(out)} H1 bars  zero_range_m1={out.attrs['zero_range_m1']:.3f}  "
              f"{time.time() - t0:.0f}s", flush=True)
    if diag:
        pd.DataFrame(diag, columns=["instrument", "zero_range_m1_frac", "n_h1", "start", "end"]).to_csv(
            f"{CACHE}/_build_diag.csv", index=False
        )


if __name__ == "__main__":
    sys.exit(main())
