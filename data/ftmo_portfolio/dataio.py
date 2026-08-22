"""Data IO: M1 (true UTC) -> CE(S)T-aligned daily bars + M5 closes, cached parquet.

Daily bar day d = [00:00 CE(S)T, 24:00) of day d  (matches FTMO daily-loss anchor).
Columns: open, high, low, close, spread_med_bps, spread_p75_bps, n_bars.
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

DATA = Path("/sessions/keen-clever-clarke/mnt/data")
M1_DIR = DATA / "deep_history_utc"
CACHE = DATA / "ftmo_portfolio" / "cache"
TZ = "Europe/Prague"

DTYPES = {"open": "float64", "high": "float64", "low": "float64",
          "close": "float64", "tick_volume": "int64", "spread": "int32"}

DIGITS = {"EURUSD":5,"GBPUSD":5,"USDCHF":5,"USDCAD":5,"AUDUSD":5,"NZDUSD":5,
          "EURGBP":5,"USDJPY":3,"EURJPY":3,"AUDJPY":3,
          "XAUUSD":2,"XAGUSD":3,"US500":2,"US100":2,"US30":2,"GER40":2,
          "UKOIL":3,"USOIL":3,"NGAS":3,"COCOA":1,"COFFEE":2,"SUGAR":2,
          "COTTON":2,"SOYBEAN":2,"COPPER":4,"DIESEL":2,"OJUICE":2}


def build_symbol(sym: str, m5: bool = True) -> None:
    f = M1_DIR / f"{sym}_M1.csv"
    if not f.exists():
        print(f"[{sym}] MISSING", flush=True); return
    df = pd.read_csv(f, usecols=["timestamp_utc","open","high","low","close","spread"],
                     dtype={"spread": "int32"})
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df.index = ts.dt.tz_convert(TZ)
    df = df.drop(columns=["timestamp_utc"]).sort_index()
    point = 10.0 ** (-DIGITS[sym])
    sp_bps = df["spread"].astype("float64") * point / df["close"] * 1e4
    g = df.groupby(df.index.date)
    daily = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(),
        "n_bars": g["close"].size(),
        "spread_med_bps": sp_bps.groupby(df.index.date).median(),
        "spread_p75_bps": sp_bps.groupby(df.index.date).quantile(0.75),
    })
    daily.index = pd.to_datetime(daily.index)
    daily.to_parquet(CACHE / f"{sym}_daily_cet.parquet")
    if m5:
        c5 = df["close"].resample("5min").last().dropna()
        c5.to_frame("close").to_parquet(CACHE / f"{sym}_m5_close.parquet")
    print(f"[{sym}] daily={len(daily)} {daily.index.min().date()}->{daily.index.max().date()}",
          flush=True)


if __name__ == "__main__":
    syms = sys.argv[1:] or list(DIGITS.keys())
    for s in syms:
        try:
            build_symbol(s)
        except Exception as e:
            print(f"[{s}] ERROR {e}", flush=True)
