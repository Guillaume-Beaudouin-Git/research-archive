"""
Data loader for the intraday-momentum FTMO study (momentum_intraday_2026-08).

Same conventions as `mr_intraday_grille_2026-08/dataload.py` (session windows, cost table,
digit conventions) so the two families are directly comparable — the only difference is that
this worktree does not carry the gitignored `data/deep_history_utc/` cache, so DEEP points at
the MAIN working dir by absolute path (read-only), per CLAUDE.md's worktree-isolation rule.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MAIN = Path("<HOME>/Desktop/Algo_claude")   # main dir, read-only
DEEP = MAIN / "data" / "deep_history_utc"
CACHE = HERE / "_cache"
CACHE.mkdir(exist_ok=True)

INDICES = ["US100", "US500", "US30", "GER40"]
FX = ["EURUSD", "GBPUSD", "USDJPY"]
FX_CROSS = ["EURJPY", "EURGBP", "AUDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
METALS = ["XAUUSD", "XAGUSD"]
CORE9 = INDICES + FX + METALS
ALL = CORE9 + FX_CROSS

DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2,
          "EURUSD": 5, "GBPUSD": 5, "USDJPY": 3,
          "XAUUSD": 2, "XAGUSD": 3,
          "EURJPY": 3, "EURGBP": 5, "AUDJPY": 3, "AUDUSD": 5,
          "USDCAD": 5, "USDCHF": 5, "NZDUSD": 5}

SESSION = {s: ("13:30", "20:00") for s in INDICES}
SESSION.update({s: ("07:00", "16:00") for s in FX + FX_CROSS})
SESSION.update({s: ("12:00", "20:00") for s in METALS})

# session bar count at 15-min (mode, verified this session: US100 26, EURUSD 36, XAUUSD 32)
BARS_PER_DAY = {}
BARS_PER_DAY.update({s: 26 for s in INDICES})
BARS_PER_DAY.update({s: 36 for s in FX + FX_CROSS})
BARS_PER_DAY.update({s: 32 for s in METALS})

# Native RT cost, bps. Core9 measured 2026-08-19 (mr_intraday_grille_2026-08/dataload.py);
# FX_CROSS from mr_univers_complet_2026-08/RAPPORT.md §1.1 (own-measurement column).
COST_RT_BPS = {
    "US100": 1.045, "GER40": 1.017, "US500": 1.07, "US30": 0.86,
    "EURUSD": 0.313, "GBPUSD": 0.338, "USDJPY": 0.379,
    "XAUUSD": 2.037, "XAGUSD": 7.05,
    "EURJPY": 0.457, "EURGBP": 0.608, "AUDJPY": 0.654, "AUDUSD": 0.602,
    "USDCAD": 0.427, "USDCHF": 0.651, "NZDUSD": 0.874,
}

L33B_GROSS_FLOOR_BPS = 1.4  # recalibrated gate (mandate §2), reported not enforced


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
    # keep only FULL sessions (>= 90% of the mode bar count) so max_hold scalars
    # (§ engine_lib bars_to_session_end guard) never silently overshoot a truncated day
    bpd = agg.groupby("session_date").size()
    full_days = bpd[bpd >= 0.9 * BARS_PER_DAY[symbol]].index
    agg = agg[agg["session_date"].isin(full_days)].copy()
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
    print(f"{'sym':7} {'bars':>9} {'from':>12} {'to':>12} {'bars/day':>9} {'n_days':>7} "
          f"{'zero_vol_frac':>13}")
    for s in ALL:
        df = build(s, force=force)
        bpd = df.groupby("session_date").size()
        zv = (df["tick_volume"] == 0).mean()
        print(f"{s:7} {len(df):>9} {str(df.index.min().date()):>12} {str(df.index.max().date()):>12} "
              f"{bpd.median():>9.0f} {bpd.shape[0]:>7} {zv:>13.3f}")
