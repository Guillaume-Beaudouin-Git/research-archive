"""Fetch EIA official daily oil series for the backwardation_oil study.

Series (EIA dnav keyless XLS endpoints, point-in-time daily settles):
  RCLC1 - Cushing, OK WTI crude oil future contract 1 ($/bbl)
  RCLC2 - Cushing, OK WTI crude oil future contract 2 ($/bbl)
  RBRTE - Europe Brent spot price FOB ($/bbl)

Caches each as parquet in ./cache/. Per HYPOTHESIS.md S4, if this fetch fails
entirely the study HALTS (no proxy substitution).
"""
from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

CACHE = Path(__file__).resolve().parent / "cache"
SERIES = {"RCLC1": "rclc1", "RCLC2": "rclc2", "RBRTE": "rbrte"}
URL = "https://www.eia.gov/dnav/pet/hist_xls/{sid}d.xls"
UA = {"User-Agent": "Mozilla/5.0 (research; algo_claude backwardation_oil study)"}


def fetch_one(sid: str) -> pd.Series:
    req = urllib.request.Request(URL.format(sid=sid), headers=UA)
    raw = urllib.request.urlopen(req, timeout=60).read()
    xls = pd.ExcelFile(io.BytesIO(raw))
    sheet = [s for s in xls.sheet_names if s.lower().startswith("data")][0]
    df = xls.parse(sheet, skiprows=2)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    out = df.dropna().set_index("date")["value"].astype(float).sort_index()
    out.name = sid
    return out


def main() -> int:
    CACHE.mkdir(exist_ok=True)
    ok = True
    for sid, stem in SERIES.items():
        try:
            s = fetch_one(sid)
            s.to_frame().to_parquet(CACHE / f"{stem}.parquet")
            print(f"{sid}: {len(s)} rows, {s.index[0].date()} -> {s.index[-1].date()}, last={s.iloc[-1]:.2f}")
        except Exception as e:  # noqa: BLE001
            print(f"{sid}: FETCH FAILED -> {e}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
