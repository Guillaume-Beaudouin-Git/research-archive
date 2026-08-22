"""Read each M1 once, write all needed scale parquets (session-filtered) to _cache."""
import sys
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
DEEP = HERE.parents[1] / "data" / "deep_history_utc"
CACHE = HERE / "_cache"; CACHE.mkdir(exist_ok=True)
INDICES = ["US100", "US500", "US30", "GER40", "XAUUSD"]; FX = ["EURUSD", "GBPUSD"]
SESS = {**{s: ("13:30", "20:00") for s in INDICES}, **{s: ("07:00", "16:00") for s in FX}}

for sym in sys.argv[1].split(","):
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
                     dtype={c: "float64" for c in ["open", "high", "low", "close", "spread"]})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    st, en = SESS[sym]
    for f in ["5min", "15min", "30min", "1h"]:
        d = (df.resample(f).agg({"open": "first", "high": "max", "low": "min",
                                 "close": "last", "spread": "mean"}).dropna(subset=["close"]))
        t = d.index.time
        d = d[(t >= pd.Timestamp(st).time()) & (t < pd.Timestamp(en).time())].copy()
        d.to_parquet(CACHE / f"{sym}_{f}.parquet")
    print(sym, "cached")
