"""
build_intraday_cache.py — resample true-UTC M1 indices to 15min & 30min bars (READ-ONLY source).

For v2 space C (sub-60min index intraday reversion). Source: data/deep_history_utc/{US500,US100,
US30,GER40}_M1.csv. Output: research/ftmo_candidate_funnel_v2/cache/{SYM}_{15min,30min}.parquet
with bar-start timestamp (true UTC), OHLC, median spread (points), n_bars. Tiny stub bars dropped.
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
SRC = REPO / "data" / "deep_history_utc"
OUT = REPO / "research" / "ftmo_candidate_funnel_v2" / "cache"
OUT.mkdir(parents=True, exist_ok=True)
INDEX = ["US500", "US100", "US30", "GER40"]
FREQS = {"15min": (15, 5), "30min": (30, 10)}    # freq -> (minutes, min_bars_to_keep)


def build(sym: str):
    t0 = time.time()
    p = SRC / f"{sym}_M1.csv"
    df = pd.read_csv(p, usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
                     dtype={"open": "float32", "high": "float32", "low": "float32",
                            "close": "float32", "spread": "float32"}, engine="c")
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"]).set_index(ts).sort_index()
    df["spread_pos"] = df["spread"].where(df["spread"] > 0)
    for fname, (mins, minbars) in FREQS.items():
        g = df.resample(f"{mins}min")
        bar = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"),
                    close=("close", "last"), spread_med=("spread_pos", "median"),
                    n_bars=("close", "size")).dropna(subset=["close"])
        bar = bar[bar["n_bars"] >= minbars].copy()
        floor = float(np.nanmedian(df["spread_pos"].to_numpy()))
        bar["spread_med"] = bar["spread_med"].fillna(floor)
        bar = bar.reset_index().rename(columns={"index": "ts", "timestamp_utc": "ts"})
        bar.columns = ["ts", "open", "high", "low", "close", "spread_med", "n_bars"]
        bar.to_parquet(OUT / f"{sym}_{fname}.parquet", index=False)
        print(f"[{sym} {fname}] {len(bar):>7d} bars {bar.ts.min().date()}..{bar.ts.max().date()} "
              f"floor={floor:.0f}pts", flush=True)
    print(f"  {sym} done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    for s in INDEX:
        build(s)
    print("DONE ->", OUT, flush=True)
