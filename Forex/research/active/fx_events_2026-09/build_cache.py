"""Build M1 parquet caches for pairs missing from scratchpad cache, matching existing schema."""
import pandas as pd
import sys
import time

CACHE_DIR = "<SCRATCH>"
SRC_DIR = "<HOME>/Desktop/Algo_claude/data/deep_history_utc"

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "XAUUSD", "US30"]

for pair in PAIRS:
    out_path = f"{CACHE_DIR}/{pair}_M1.parquet"
    t0 = time.time()
    src = f"{SRC_DIR}/{pair}_M1.csv"
    df = pd.read_csv(
        src,
        usecols=["timestamp_utc", "open", "high", "low", "close"],
        dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64"},
    )
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.set_index("timestamp_utc").sort_index()
    df.to_parquet(out_path)
    print(f"{pair}: {len(df)} rows, {time.time()-t0:.1f}s -> {out_path}")
