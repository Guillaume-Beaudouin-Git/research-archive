"""
build_intraday_cache.py — resample M1 deep_history_utc FX to 15-min bars + verify TRUE UTC.

READ-ONLY on source (data/deep_history_utc/*.csv). Writes ONLY under
Forex/research/active/fx_intraday_deepdive/cache/.

For each instrument:
  * stream the M1 CSV, parse the fixed-format timestamp, resample to 15-min OHLC bars with
    median M1 spread (points), summed tick_volume, and M1 bar-count per bar -> parquet.
  * emit a TRUE-UTC diagnostic (no strategy returns, pure data structure):
      - mean spread (points) and mean tick_volume by UTC hour-of-day,
      - bar-count by (day-of-week, hour) to locate the FX weekend close/open seam.
    True UTC predicts: spread MIN + volume MAX in the London/NY overlap (UTC 12-16), spread
    MAX at the 21:00-22:00 UTC rollover, weekend gap Fri ~21:00 UTC -> Sun ~21:00-22:00 UTC.
"""
from __future__ import annotations
import sys, json, time
from pathlib import Path
import numpy as np
import pandas as pd

SRC = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc")
CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

FX = ["EURUSD", "GBPUSD", "EURGBP", "NZDUSD", "USDCHF", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "AUDJPY"]
EXTRA = ["XAUUSD"]                       # goal: "check XAUUSD" — cached as contrast, not primary FX
UNIVERSE = FX + EXTRA

USECOLS = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"]
DT = {"open": np.float64, "high": np.float64, "low": np.float64, "close": np.float64,
      "tick_volume": np.int64, "spread": np.int32}


def build_one(sym: str) -> dict:
    src = SRC / f"{sym}_M1.csv"
    out = CACHE / f"{sym}_15min.parquet"
    t0 = time.time()
    df = pd.read_csv(src, usecols=USECOLS, dtype=DT, engine="c")
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"])
    df.index = pd.DatetimeIndex(ts)

    # ── TRUE-UTC diagnostic on the raw M1 (no returns) ────────────────────────
    hour = df.index.hour
    dow = df.index.dayofweek                         # Mon=0 .. Sun=6
    spread_by_hour = df.groupby(hour)["spread"].mean().round(2)
    vol_by_hour = df.groupby(hour)["tick_volume"].mean().round(0)
    cnt = pd.Series(1, index=df.index).groupby([dow, hour]).size()
    # weekend seam: last UTC hour with bars on Friday, first on Sunday
    fri_hours = sorted(h for (d, h) in cnt.index if d == 4 and cnt[(d, h)] > 50)
    sun_hours = sorted(h for (d, h) in cnt.index if d == 6 and cnt[(d, h)] > 50)
    sat_bars = int(sum(cnt[(d, h)] for (d, h) in cnt.index if d == 5))
    diag = {
        "rows_m1": int(len(df)),
        "first": str(df.index[0]), "last": str(df.index[-1]),
        "spread_by_utc_hour_pts": {int(k): float(v) for k, v in spread_by_hour.items()},
        "vol_by_utc_hour": {int(k): float(v) for k, v in vol_by_hour.items()},
        "spread_min_hour": int(spread_by_hour.idxmin()), "spread_max_hour": int(spread_by_hour.idxmax()),
        "vol_max_hour": int(vol_by_hour.idxmax()), "vol_min_hour": int(vol_by_hour.idxmin()),
        "friday_last_active_utc_hour": (fri_hours[-1] if fri_hours else None),
        "sunday_first_active_utc_hour": (sun_hours[0] if sun_hours else None),
        "saturday_bars": sat_bars,
    }

    # ── 15-min resample (label = bar start, UTC) ──────────────────────────────
    key = df.index.floor("15min")
    agg = df.groupby(key).agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
        spread_med=("spread", "median"), tick_vol=("tick_volume", "sum"), n_m1=("close", "size"),
    )
    agg.index.name = "ts"
    agg = agg.reset_index()
    agg.to_parquet(out, index=False)
    diag["bars_15min"] = int(len(agg))
    diag["secs"] = round(time.time() - t0, 1)
    return diag


def main():
    pairs = sys.argv[1:] if len(sys.argv) > 1 else UNIVERSE
    verif = {}
    vfile = CACHE / "utc_verification.json"
    if vfile.exists():
        verif = json.loads(vfile.read_text())
    for sym in pairs:
        out = CACHE / f"{sym}_15min.parquet"
        if out.exists() and sym in verif:
            print(f"[skip] {sym} (cached)"); continue
        print(f"[build] {sym} ...", flush=True)
        d = build_one(sym)
        verif[sym] = d
        vfile.write_text(json.dumps(verif, indent=2))
        print(f"   {sym}: {d['rows_m1']:,} M1 -> {d['bars_15min']:,} 15min | "
              f"{d['first']}..{d['last']} | spread_min_h={d['spread_min_hour']} "
              f"vol_max_h={d['vol_max_hour']} fri_close_h={d['friday_last_active_utc_hour']} "
              f"sun_open_h={d['sunday_first_active_utc_hour']} sat_bars={d['saturday_bars']} "
              f"| {d['secs']}s", flush=True)
    print("\nDONE. utc_verification.json written.")


if __name__ == "__main__":
    main()
