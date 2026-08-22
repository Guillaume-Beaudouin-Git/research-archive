"""
Data loader for the new-instrument sweep (mr_univers_complet_2026-08), FX-cross + energy/copper
branch. Reuses the exact resample/session/cache conventions of
`mr_intraday_grille_2026-08/dataload.py` (read only imported as a pattern, not the module itself,
to keep this study's cache writes confined to its own folder per the mandate's isolation rule).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
DEEP = REPO / "data" / "deep_history_utc"
CACHE = HERE / "_cache"
CACHE.mkdir(exist_ok=True)

FX_NEW = ["EURJPY", "EURGBP", "AUDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]

DIGITS = {"EURJPY": 3, "EURGBP": 5, "AUDJPY": 3, "AUDUSD": 5,
          "USDCAD": 5, "USDCHF": 5, "NZDUSD": 5}

# Same London/NY overlap window as the 3 already-tested majors (EURUSD/GBPUSD/USDJPY) — kept
# identical so the new-vs-old contrast is legible (PREREGISTRATION.md §1).
SESSION = {s: ("07:00", "16:00") for s in FX_NEW}

# Cost provenance: no direct 2026-08-19 measurement exists for these 7 crosses. USDJPY is the
# only FX pair with BOTH a catalog point (phase0_rt_cost_bps.csv=1.364) and a fresh measured
# point (0.379) -> ratio 0.278 (identical derivation `mr_intraday_grille_2026-08/PREREGISTRATION.md`
# §2 already used for EURUSD/GBPUSD). Applied uniformly to the catalog value of each new cross.
_CATALOG = {"EURJPY": 1.6421, "EURGBP": 2.1869, "AUDJPY": 2.3532, "AUDUSD": 2.1649,
            "USDCAD": 1.5374, "USDCHF": 2.3420, "NZDUSD": 3.1434}
_RATIO_USDJPY = 0.379 / 1.3643
COST_RT_BPS = {s: round(_CATALOG[s] * _RATIO_USDJPY, 4) for s in FX_NEW}
COST_PROVENANCE = {s: f"derived: catalog {_CATALOG[s]} x ratio(USDJPY new/catalog={_RATIO_USDJPY:.3f})"
                   for s in FX_NEW}

# Own-measurement cross-check this session (median real spread_bps from deep_history_utc,
# zero-spread bars excluded) -- reported alongside the derived figure, never silently substituted,
# so a reader can see both provenances at once.
MEASURED_SPREAD_BPS = {"EURJPY": 0.768, "EURGBP": 1.606, "AUDJPY": 1.769, "AUDUSD": 0.955,
                       "USDCAD": 0.584, "USDCHF": 1.402, "NZDUSD": 1.798}


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


def build_m1(symbol: str, force: bool = False) -> pd.DataFrame:
    """Session-filtered M1 frame, for the m1_resolve exit-resolution pass."""
    out = CACHE / f"{symbol}_1min.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    usecols = ["timestamp_utc", "open", "high", "low", "close"]
    df = pd.read_csv(DEEP / f"{symbol}_M1.csv", usecols=usecols,
                     dtype={"open": "float64", "high": "float64", "low": "float64", "close": "float64"})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"])
    st, en = SESSION[symbol]
    df = df[_session_mask(df.index, st, en)].copy()
    df["session_date"] = df.index.normalize()
    df.to_parquet(out)
    return df


def load(symbol: str, bar: str = "15min") -> pd.DataFrame:
    return build(symbol, bar)


if __name__ == "__main__":
    force = "--force" in sys.argv
    print("Cache build + volume-profile sanity check (L52/L56 clock discipline).")
    print(f"{'sym':7} {'bars':>9} {'from':>12} {'to':>12} {'bars/day':>9} {'peak_hr':>8} {'med_spr_bps':>11}")
    for s in FX_NEW:
        df = build(s, "15min", force=force)
        bpd = df.groupby("session_date").size()
        vol_by_hr = df.groupby(df.index.hour)["tick_volume"].sum()
        peak_hr = int(vol_by_hr.idxmax()) if len(vol_by_hr) else -1
        print(f"{s:7} {len(df):>9} {str(df.index.min().date()):>12} {str(df.index.max().date()):>12} "
              f"{bpd.median():>9.0f} {peak_hr:>8} {df['spread_bps'].median():>11.4f}")
