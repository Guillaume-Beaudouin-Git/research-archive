"""
build_cache.py — resample true-UTC M1 deep history to daily bars (READ-ONLY on source).

Source : data/deep_history_utc/<SYM>_M1.csv  (timestamp_utc is TRUE UTC; per-bar `spread`
         in MT5 points; schema open,high,low,close,tick_volume,spread,real_volume).
Output : research/ftmo_candidate_funnel/cache/<SYM>_daily.parquet
         + cache/spread_floors.json  (per-instrument median spread>0, used as cost floor)
         + cache/cache_manifest.json

Daily bars use a 22:00-UTC-anchored trading day (NY 17:00 close convention): a bar at
HH>=22:00 UTC belongs to the NEXT calendar day. This avoids (a) Sunday-evening stub bars and
(b) splitting the 24h FX session at 00:00 UTC — both of which inflate the bar count (~310/yr)
and the kurtosis under naive UTC-date grouping. Sat/Sun trading-days (rare late-Friday bars)
are dropped. The M1 files are time-sorted & monotonic (MANIFEST gate), so within each
trading-day 'first'=open, 'last'=close. high=max, low=min, spread_med = median(spread>0).

BTC: panels/btc_full.csv (yfinance BTC-USD daily close, 2014+). Only close available ->
open/high/low set to close; flagged close_only. Crypto cost handled by bps model downstream.
"""
from __future__ import annotations
import json, time, sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
SRC = REPO / "data" / "deep_history_utc"
OUT = REPO / "research" / "ftmo_candidate_funnel" / "cache"
OUT.mkdir(parents=True, exist_ok=True)

FX = ["EURUSD","GBPUSD","USDJPY","AUDUSD","USDCHF","USDCAD","NZDUSD","EURGBP","EURJPY","AUDJPY"]
METAL = ["XAUUSD"]
INDEX = ["US500","US100","US30","GER40"]
MT5_SYMS = FX + METAL + INDEX


def build_one(sym: str) -> dict:
    t0 = time.time()
    p = SRC / f"{sym}_M1.csv"
    # read only needed cols; floats as float32 to cap memory, timestamp as raw string
    df = pd.read_csv(
        p,
        usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
        dtype={"open": "float32", "high": "float32", "low": "float32",
               "close": "float32", "spread": "float32"},
        engine="c",
    )
    # 22:00-UTC-anchored trading day (HH>=22 -> next day). Vectorised datetime parse.
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    tday = (ts + pd.Timedelta(hours=2)).dt.normalize()
    sp_pos = df["spread"].where(df["spread"] > 0)  # NaN where spread==0
    g = pd.DataFrame({
        "date": tday,
        "open": df["open"], "high": df["high"], "low": df["low"], "close": df["close"],
        "spread_pos": sp_pos, "spread_raw": df["spread"],
    })
    g = g[g["date"].dt.dayofweek < 5]              # drop Sat/Sun trading-days
    daily = g.groupby("date", sort=True).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        spread_med=("spread_pos", "median"),
        spread_p90=("spread_pos", lambda s: s.quantile(0.90)),
        n_bars=("close", "size"),
    ).reset_index()
    daily = daily.sort_values("date").reset_index(drop=True)  # date already datetime64
    # global spread floor (median of positive spreads across full history)
    floor = float(np.nanmedian(sp_pos.to_numpy())) if sp_pos.notna().any() else 0.0
    daily["spread_med"] = daily["spread_med"].fillna(floor)
    daily["spread_p90"] = daily["spread_p90"].fillna(daily["spread_med"])
    daily["close_only"] = False
    daily.to_parquet(OUT / f"{sym}_daily.parquet", index=False)
    dt = time.time() - t0
    info = {"sym": sym, "rows_m1": int(len(df)), "rows_daily": int(len(daily)),
            "date_min": str(daily.date.min().date()), "date_max": str(daily.date.max().date()),
            "spread_floor_pts": floor, "secs": round(dt, 1)}
    print(f"[{sym}] {info['rows_m1']:>8d} M1 -> {info['rows_daily']:>5d} daily | "
          f"{info['date_min']}..{info['date_max']} | floor={floor:.1f}pts | {dt:.0f}s", flush=True)
    return info


def build_btc() -> dict:
    t0 = time.time()
    p = REPO / "data" / "panels" / "btc_full.csv"
    df = pd.read_csv(p)
    df.columns = ["date", "close"]
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"]).sort_values("date").reset_index(drop=True)
    daily = pd.DataFrame({
        "date": df["date"], "open": df["close"], "high": df["close"],
        "low": df["close"], "close": df["close"],
        "spread_med": np.nan, "spread_p90": np.nan, "n_bars": 1, "close_only": True,
    })
    daily.to_parquet(OUT / "BTCUSD_daily.parquet", index=False)
    info = {"sym": "BTCUSD", "rows_m1": 0, "rows_daily": int(len(daily)),
            "date_min": str(daily.date.min().date()), "date_max": str(daily.date.max().date()),
            "spread_floor_pts": None, "secs": round(time.time() - t0, 1)}
    print(f"[BTCUSD] daily close-only {info['rows_daily']} rows | "
          f"{info['date_min']}..{info['date_max']} | {info['secs']}s", flush=True)
    return info


def main():
    manifest, floors = [], {}
    for sym in MT5_SYMS:
        try:
            info = build_one(sym)
            manifest.append(info)
            floors[sym] = info["spread_floor_pts"]
        except Exception as e:  # noqa
            print(f"[{sym}] FAILED: {e}", flush=True)
            manifest.append({"sym": sym, "error": str(e)})
    manifest.append(build_btc())
    (OUT / "spread_floors.json").write_text(json.dumps(floors, indent=2))
    (OUT / "cache_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("\nDONE. cache ->", OUT, flush=True)


if __name__ == "__main__":
    main()
