"""
Build NY-day (17:00 ET roll, DST-aware) daily OHLC bars from true-UTC M1 data.
Caches to scratchpad parquet, not tracked in git (data governance: caches are local).
Signal T-1 / trade T convention downstream depends on this being the REAL FX trading
day (L52/L56: exchange clock with DST, never UTC calendar day).
"""
import pandas as pd
import numpy as np
import sys

DEEP_HIST = "<HOME>/Desktop/Algo_claude/data/deep_history_utc"
CACHE = "<SCRATCH>"

def build_daily(pair: str) -> pd.DataFrame:
    path = f"{DEEP_HIST}/{pair}_M1.csv"
    df = pd.read_csv(path, usecols=["timestamp_utc", "open", "high", "low", "close"],
                      parse_dates=["timestamp_utc"])
    df["timestamp_utc"] = df["timestamp_utc"].dt.tz_localize("UTC")
    df = df.set_index("timestamp_utc").sort_index()
    # NY trading-day roll at 17:00 America/New_York (DST-aware, per L52/L56)
    ny = df.index.tz_convert("America/New_York")
    shifted = ny - pd.Timedelta(hours=17)
    trading_day = shifted.normalize().tz_localize(None)
    df["trading_day"] = trading_day
    daily = df.groupby("trading_day").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        n_bars=("close", "size"),
    )
    # drop degenerate days (holiday remnants, <100 bars out of ~1440 possible)
    daily = daily[daily["n_bars"] >= 100].copy()
    daily["ret"] = np.log(daily["close"] / daily["close"].shift(1))
    return daily

if __name__ == "__main__":
    pairs = sys.argv[1:] or ["EURUSD", "USDJPY", "AUDUSD", "NZDUSD", "GBPUSD", "USDCAD", "USDCHF"]
    for p in pairs:
        d = build_daily(p)
        out = f"{CACHE}/{p}_daily_ny17.parquet"
        d.to_parquet(out)
        print(p, d.shape, d.index.min(), d.index.max(), "->", out)
