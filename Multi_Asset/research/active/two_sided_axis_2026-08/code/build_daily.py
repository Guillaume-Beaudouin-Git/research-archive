"""Build daily bars anchored on the FTMO swap-charge instant.

00:00 broker time (EET/EEST) == 17:00 America/New_York year-round, which is
exactly the instant the overnight financing is posted. Anchoring the daily bar
there makes "one bar == one swap night" true by construction (L56: exchange
clock with its DST, never UTC).

Reads the PRIVATE hourly cache built by awk from data/deep_history_utc (true
UTC), never data/panels/m5_indices (EET mislabelled UTC).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path(os.environ.get(
    "TS_CACHE",
    "<SCRATCH>"
    "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/ts_cache",
))

UNIVERSE = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "EURGBP", "EURJPY", "AUDJPY",
    "US500", "US100", "US30", "GER40",
    "XAUUSD", "XAGUSD", "COPPER",
    "UKOIL", "USOIL",
]

ANCHOR_TZ = "America/New_York"
ANCHOR_HOUR = 16  # close of the 16:00 NY bar == price at 17:00 NY == 00:00 broker


def _read_h1(sym: str) -> pd.DataFrame:
    df = pd.read_csv(
        CACHE / f"{sym}_H1.csv",
        usecols=["timestamp_utc", "open", "high", "low", "close"],
        parse_dates=["timestamp_utc"],
        date_format="%Y.%m.%d %H:%M:%S",
    )
    df = df.set_index("timestamp_utc").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.index = df.index.tz_localize("UTC")
    return df


def zero_range_share(sym: str) -> pd.Series:
    """L60 control: share of hourly bars with high == low (settlement prints)."""
    h = _read_h1(sym)
    z = (h["high"] == h["low"]).astype(float)
    return z.groupby(h.index.year).mean()


def daily_on_swap_clock(sym: str) -> pd.DataFrame:
    """One row per swap night: close at 17:00 NY, plus that session's range."""
    h = _read_h1(sym)
    loc = h.tz_convert(ANCHOR_TZ)
    anchor = loc[loc.index.hour == ANCHOR_HOUR]
    out = pd.DataFrame({"close": anchor["close"].to_numpy()},
                       index=pd.DatetimeIndex(anchor.index.normalize().tz_localize(None)))
    out = out[~out.index.duplicated(keep="last")]
    out = out[out["close"] > 0]
    # realised vol of the session that just ended, from hourly log returns
    lr = np.log(loc["close"]).diff()
    day = pd.DatetimeIndex(loc.index.normalize().tz_localize(None))
    rv = lr.groupby(day).std()
    out["rv_h1"] = rv.reindex(out.index)
    out["logret"] = np.log(out["close"]).diff()
    return out.dropna(subset=["logret"])


def build_all(verbose: bool = True) -> pd.DataFrame:
    px, diag = {}, []
    for s in UNIVERSE:
        d = daily_on_swap_clock(s)
        px[s] = d["logret"]
        z = zero_range_share(s)
        diag.append({
            "symbol": s, "n_days": len(d),
            "start": d.index.min().date(), "end": d.index.max().date(),
            "zero_range_h1_share": float(z.mean()),
            "zero_range_worst_year": float(z.max()),
            "zero_range_worst_yr_label": int(z.idxmax()),
        })
        if verbose:
            print(f"{s:8s} n={len(d):5d} {d.index.min().date()}..{d.index.max().date()} "
                  f"zero-range h1 {z.mean():.3%}")
    R = pd.DataFrame(px).sort_index()
    return R, pd.DataFrame(diag)


if __name__ == "__main__":
    R, diag = build_all()
    R.to_parquet(CACHE / "daily_logret_swapclock.parquet")
    diag.to_csv(CACHE / "l60_zero_range_diag.csv", index=False)
    print(diag.to_string(index=False))
