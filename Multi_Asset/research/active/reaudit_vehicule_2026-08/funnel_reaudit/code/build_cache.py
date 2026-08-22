"""Build M1 parquet caches (2019+) from data/deep_history_utc CSVs (TRUE UTC).

Read-only on data/. Writes only to the scratch CACHE_DIR.
Needed because the funnel's original inputs (data/panels/m5_indices/*_M1.csv,
data/ftmo_research/, Forex/data/cache/dukascopy_m5/) were deleted by the
2026-06-10 P2 cleanup. deep_history_utc is the canonical replacement.
"""
from __future__ import annotations

import os
import sys

import pandas as pd

DEEP = "<HOME>/Desktop/Algo_claude/data/deep_history_utc"
CACHE_DIR = ("<SCRATCH>"
             "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/cache")

SYMBOLS = ["USDJPY", "GBPUSD", "EURGBP", "EURJPY", "AUDUSD", "NZDUSD",
           "USDCAD", "USDCHF", "XAGUSD", "USOIL", "UKOIL"]

START = pd.Timestamp("2019-01-01")


def build(sym: str) -> None:
    out = os.path.join(CACHE_DIR, f"{sym}_m1_utc.parquet")
    if os.path.exists(out):
        print(f"{sym}: cached", flush=True)
        return
    src = os.path.join(DEEP, f"{sym}_M1.csv")
    if not os.path.exists(src):
        print(f"{sym}: SOURCE MISSING", flush=True)
        return
    parts = []
    reader = pd.read_csv(src, usecols=["timestamp_utc", "open", "high", "low", "close"],
                         chunksize=2_000_000)
    for ch in reader:
        ts = pd.to_datetime(ch["timestamp_utc"], format="%Y.%m.%d %H:%M:%S",
                            errors="coerce")
        ch = ch.assign(ts=ts).dropna(subset=["ts"])
        ch = ch[ch["ts"] >= START]
        if len(ch):
            parts.append(ch[["ts", "open", "high", "low", "close"]])
    if not parts:
        print(f"{sym}: EMPTY after {START.date()}", flush=True)
        return
    df = pd.concat(parts).set_index("ts").sort_index()
    df = df[~df.index.duplicated(keep="first")].astype("float32")
    df.index.name = "timestamp_utc"
    df.to_parquet(out)
    print(f"{sym}: {len(df):,} rows  {df.index[0]} -> {df.index[-1]}", flush=True)


if __name__ == "__main__":
    os.makedirs(CACHE_DIR, exist_ok=True)
    todo = sys.argv[1:] or SYMBOLS
    for s in todo:
        build(s)
