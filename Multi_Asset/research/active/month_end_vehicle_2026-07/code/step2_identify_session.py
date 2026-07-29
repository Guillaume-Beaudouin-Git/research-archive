"""Step 2 — identify what yfinance's daily Open/Close mean for ZN=F.

The whole intraday/overnight verdict hinges on this: if daily-Open is the 18:00 ET
Globex open, then "open->close" is the entire 23h session and the split says
nothing about a daily-flat propfirm. If it is the 08:20/09:30 ET US-session open,
the split is exactly the propfirm question.

Method: for each date in the overlap window, find which hourly bar's open/close
best matches the daily Open/Close (min median |diff| in ticks).
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
DATA = BASE / "data"


def load_h1(name: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"h1_{name}.parquet")
    idx = pd.to_datetime(df.index, utc=True).tz_convert("America/New_York")
    df = df.set_axis(idx).sort_index()
    return df


def load_daily(name: str) -> pd.DataFrame:
    df = pd.read_parquet(DATA / f"daily_{name}.parquet")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df.sort_index()


def match(h1: pd.DataFrame, daily: pd.DataFrame, field: str, hcol: str) -> pd.DataFrame:
    """Median |daily[field] - h1[hcol] at hour h| by hour-of-day, in 1/64 pts (ticks)."""
    h1 = h1.copy()
    h1["date"] = h1.index.normalize().tz_localize(None)
    h1["hour"] = h1.index.hour
    rows = []
    for hh, g in h1.groupby("hour"):
        s = g.set_index("date")[hcol]
        s = s[~s.index.duplicated(keep="first")]
        j = daily[field].reindex(s.index).dropna()
        s = s.reindex(j.index)
        d = (j - s).abs().dropna()
        if len(d) < 60:
            continue
        rows.append(dict(hour_et=hh, n=len(d), med_abs_ticks=float(d.median()) * 64,
                         frac_exact=float((d < 1 / 128).mean())))
    return pd.DataFrame(rows).sort_values("med_abs_ticks")


def prev_session_match(h1: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Same, but testing hours of the PREVIOUS calendar day (Globex evening 18:00-23:00)."""
    h1 = h1.copy()
    # CME trading day D runs 18:00 ET (D-1) -> 17:00 ET (D)
    h1["date"] = (h1.index + pd.Timedelta(hours=7)).normalize().tz_localize(None)
    h1["hour"] = h1.index.hour
    rows = []
    for hh, g in h1.groupby("hour"):
        s = g.set_index("date")["Open"]
        s = s[~s.index.duplicated(keep="first")]
        j = daily["Open"].reindex(s.index).dropna()
        s = s.reindex(j.index)
        d = (j - s).abs().dropna()
        if len(d) < 60:
            continue
        rows.append(dict(hour_et=hh, n=len(d), med_abs_ticks=float(d.median()) * 64,
                         frac_exact=float((d < 1 / 128).mean())))
    return pd.DataFrame(rows).sort_values("med_abs_ticks")


if __name__ == "__main__":
    for name, dname in (("ZNF", "ZNF"), ("TLT", "TLT")):
        h1 = load_h1(name)
        daily = load_daily(dname)
        print("=" * 76)
        print(f"{name}: hourly {h1.index[0]} -> {h1.index[-1]}  (bars stamped at bar START, ET)")
        print(f"  hours present: {sorted(set(h1.index.hour))}")
        print(f"\n  -- daily OPEN vs hourly open, calendar-day alignment (top 5)")
        print(match(h1, daily, "Open", "Open").head(5).to_string(index=False))
        print(f"\n  -- daily CLOSE vs hourly close, calendar-day alignment (top 5)")
        print(match(h1, daily, "Close", "Close").head(5).to_string(index=False))
        if name == "ZNF":
            print(f"\n  -- daily OPEN vs hourly open, CME-trading-day alignment (18:00 ET prev day) (top 5)")
            print(prev_session_match(h1, daily).head(5).to_string(index=False))
        print()
