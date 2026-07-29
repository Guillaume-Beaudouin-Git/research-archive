"""Assemble the per-symbol daily caches into one aligned panel + quality audit.

Calendar policy (a choice that matters, declared here):

* the master calendar is the set of **weekdays** on which at least one FX pair
  printed a full session. Saturdays and Sundays are excluded; the Sunday-evening
  FX reopen therefore lands inside Monday's close-to-close return, which is where
  a holder actually experiences it.
* an instrument that does not trade on a master date (index holiday, commodity
  holiday) has its close **forward-filled**: its return that day is 0, the
  position is still held, and swap is still charged. That is what a real holder
  experiences; dropping the date instead would silently delete holiday risk and
  holiday carry.
* a session is treated as non-trading when its bar count is below 20% of the
  instrument's rolling-median bar count (the density criterion the deep-history
  MANIFEST itself uses to flag holes).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "cache"

UNIVERSE = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    "US30", "US100", "US500", "GER40",
    "XAUUSD", "XAGUSD", "COPPER",
    "UKOIL", "USOIL", "NGAS",
]
FX = UNIVERSE[:7]
START, END = "2013-10-01", "2026-06-05"
WARMUP_START = "2013-01-01"          # 120d momentum + 60d vol need ~9 months of run-up
DENSITY_FLOOR = 0.20


def load_raw() -> dict[str, pd.DataFrame]:
    out = {}
    for sym in UNIVERSE:
        df = pd.read_parquet(CACHE / f"daily_{sym}.parquet")
        df = df.set_index("date").sort_index()
        out[sym] = df
    return out


def build(quality: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (panel, quality_report).

    ``panel`` is a MultiIndex-column frame (symbol, field) on the master calendar,
    fields = open/high/low/close/spread_med/spread_p95/traded.
    """
    raw = load_raw()
    rep = []

    # --- master calendar: weekdays where a majority of FX pairs had a full session
    dens = {}
    for sym, df in raw.items():
        med = df["n_bars"].rolling(63, min_periods=10).median().bfill()
        dens[sym] = (df["n_bars"] >= DENSITY_FLOOR * med)
    fx_ok = pd.concat([dens[s] for s in FX], axis=1).fillna(False)
    cal = fx_ok.index[fx_ok.sum(axis=1) >= 4]
    cal = cal[cal.dayofweek < 5]
    cal = cal[(cal >= WARMUP_START) & (cal <= END)]

    frames = {}
    for sym, df in raw.items():
        d = df.reindex(cal)
        traded = dens[sym].reindex(cal).fillna(False)
        # a low-density or missing session is not a tradable session
        for col in ("open", "high", "low", "close"):
            d[col] = d[col].where(traded).ffill()
        d["spread_med"] = d["spread_med"].where(traded).ffill()
        d["spread_p95"] = d["spread_p95"].where(traded).ffill()
        d["traded"] = traded.astype(float)
        frames[sym] = d[["open", "high", "low", "close",
                         "spread_med", "spread_p95", "traded"]]
        sub = d.loc[START:]
        rep.append({
            "symbol": sym,
            "first": df.index.min().date(), "last": df.index.max().date(),
            "sessions": int(sub["traded"].sum()),
            "non_traded_days": int((sub["traded"] == 0).sum()),
            "non_traded_pct": round(100 * (sub["traded"] == 0).mean(), 2),
            "close_nan": int(sub["close"].isna().sum()),
            "spread_med_bps_2013_26": np.nan,   # filled by the caller (needs costs.py)
            "median_bars_per_session": float(df["n_bars"].median()),
        })

    panel = pd.concat(frames, axis=1)
    panel.columns.names = ["symbol", "field"]
    return panel, pd.DataFrame(rep)


def closes(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.xs("close", level=1, axis=1)[UNIVERSE]


def opens(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.xs("open", level=1, axis=1)[UNIVERSE]


def traded(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.xs("traded", level=1, axis=1)[UNIVERSE]
