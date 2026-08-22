"""
Data loader for the intraday-MR exhaustive-grid study (mr_intraday_grille_2026-08).

Resamples the repo's canonical true-UTC deep_history M1 series (read-only) to intraday
bars, filters to each instrument's liquid session window, and caches per-instrument
parquet locally (gitignored). Adds metals (XAUUSD/XAGUSD) and a 60-min frequency on
top of the conventions already used by yt_strategy_replications/intraday_mr_ftmo.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]                      # .../Algo_claude
DEEP = REPO / "data" / "deep_history_utc"
CACHE = HERE / "_cache"
CACHE.mkdir(exist_ok=True)

INDICES = ["US100", "US500", "US30", "GER40"]
FX = ["EURUSD", "GBPUSD", "USDJPY"]
METALS = ["XAUUSD", "XAGUSD"]
ALL = INDICES + FX + METALS

DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2,
          "EURUSD": 5, "GBPUSD": 5, "USDJPY": 3,
          "XAUUSD": 2, "XAGUSD": 3}

SESSION = {s: ("13:30", "20:00") for s in INDICES}
SESSION.update({s: ("07:00", "16:00") for s in FX})
SESSION.update({s: ("12:00", "20:00") for s in METALS})  # COMEX/NY metals overlap

# Native RT cost, bps (see PREREGISTRATION.md §2 for provenance of each number).
COST_RT_BPS = {
    "US100": 1.045, "GER40": 1.017, "US500": 1.07, "US30": 0.86,
    "EURUSD": 0.313, "GBPUSD": 0.338, "USDJPY": 0.379,
    "XAUUSD": 2.037, "XAGUSD": 7.05,
}
COST_PROVENANCE = {
    "US100": "measured 2026-08-19", "GER40": "measured 2026-08-19",
    "US500": "derived: COST_AUDIT 1.82 x ratio(GER40 new/old=0.588)",
    "US30": "derived: COST_AUDIT 1.47 x ratio(GER40 new/old=0.588)",
    "USDJPY": "measured 2026-08-19",
    "EURUSD": "derived: catalog 1.127 x ratio(USDJPY new/catalog=0.278)",
    "GBPUSD": "derived: catalog 1.217 x ratio(USDJPY new/catalog=0.278)",
    "XAUUSD": "measured 2026-08-19",
    "XAGUSD": "derived: gross_surface_map 6.37 x ratio(XAUUSD new/COST_AUDIT=1.107)",
}


def _session_mask(idx: pd.DatetimeIndex, start: str, end: str) -> np.ndarray:
    t = idx.time
    s = pd.Timestamp(start).time(); e = pd.Timestamp(end).time()
    return (t >= s) & (t < e)


def build(symbol: str, bar: str = "15min", force: bool = False) -> pd.DataFrame:
    out = CACHE / f"{symbol}_{bar}.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    usecols = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"]
    df = pd.read_csv(DEEP / f"{symbol}_M1.csv", usecols=usecols,
                     dtype={"open": "float64", "high": "float64", "low": "float64",
                            "close": "float64", "tick_volume": "float64", "spread": "float64"})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"])
    agg = (df.resample(bar)
             .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                   "tick_volume": "sum", "spread": "mean"})
             .dropna(subset=["open", "high", "low", "close"]))
    st, en = SESSION[symbol]
    agg = agg[_session_mask(agg.index, st, en)].copy()
    pt = 10.0 ** (-DIGITS[symbol])
    agg["spread_bps"] = (agg["spread"] * pt) / agg["close"] * 1e4
    agg["session_date"] = agg.index.normalize()
    agg.to_parquet(out)
    return agg


def load(symbol: str, bar: str = "15min", start=None, end=None) -> pd.DataFrame:
    df = build(symbol, bar)
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


if __name__ == "__main__":
    force = "--force" in sys.argv
    print("Cache build + volume-profile sanity check (peak hour should sit inside the declared "
          "session window; a mistimed peak = clock bug, per L52/L56).")
    print(f"{'sym':7} {'bar':6} {'bars':>9} {'from':>12} {'to':>12} {'bars/day':>9} "
          f"{'peak_hr_utc':>11} {'med_spr_bps':>11}")
    for bar in ["15min", "60min"]:
        for s in ALL:
            df = build(s, bar=bar, force=force)
            rng = df.index
            bpd = df.groupby("session_date").size()
            vol_by_hr = df.groupby(df.index.hour)["tick_volume"].sum()
            peak_hr = int(vol_by_hr.idxmax()) if len(vol_by_hr) else -1
            print(f"{s:7} {bar:6} {len(df):>9} {str(rng.min().date()):>12} {str(rng.max().date()):>12} "
                  f"{bpd.median():>9.0f} {peak_hr:>11} {df['spread_bps'].median():>11.4f}")
