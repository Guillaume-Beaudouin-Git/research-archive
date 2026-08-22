"""
Q1 (autocorrelation vs cost, descriptive) + Q3 (cost wall across frequencies).
Measure-first: is a net 1-lag MR edge even POSSIBLE before building a strategy?
reversion amplitude = |AC(1)| x sigma_bar (bps) vs RT spread (bps). ratio<1 => impossible.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

DEEP = Path(__file__).resolve().parents[2] / "data" / "deep_history_utc"
DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2, "EURUSD": 5, "GBPUSD": 5}
INDICES = ["US100", "US500", "US30", "GER40"]
FX = ["EURUSD", "GBPUSD"]
SESS = {**{s: ("13:30", "20:00") for s in INDICES}, **{s: ("07:00", "16:00") for s in FX}}
FREQS = ["1min", "2min", "5min", "15min"]


def read_m1(sym):
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
                     dtype={c: "float64" for c in ["open", "high", "low", "close", "spread"]})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    return df.drop(columns=["timestamp_utc"])


def resample(df1, freq, sym):
    if freq == "1min":
        d = df1.copy()
    else:
        d = (df1.resample(freq).agg({"open": "first", "high": "max", "low": "min",
                                     "close": "last", "spread": "mean"})
               .dropna(subset=["close"]))
    st, en = SESS[sym]
    t = d.index.time
    d = d[(t >= pd.Timestamp(st).time()) & (t < pd.Timestamp(en).time())].copy()
    d["sd"] = d.index.normalize()
    return d


def ac(r, k):
    return float(pd.Series(r).autocorr(lag=k))


if __name__ == "__main__":
    print(f"{'sym':6} {'freq':5} | {'AC1':>7} {'AC2':>7} {'AC3':>7} | {'sig_bps':>7} "
          f"{'ampl_bps':>8} {'spr_bps':>7} | {'ratio':>6}")
    print("-" * 78)
    for sym in INDICES + FX:
        df1 = read_m1(sym)
        pt = 10.0 ** (-DIGITS[sym])
        for f in FREQS:
            d = resample(df1, f, sym)
            r = d["close"].pct_change()
            first = d.groupby("sd").cumcount() == 0
            r = r.mask(first.values)                      # kill cross-session returns
            a1, a2, a3 = ac(r, 1), ac(r, 2), ac(r, 3)
            sig = float(r.std()) * 1e4
            ampl = abs(a1) * sig
            spr = float((d["spread"] * pt / d["close"] * 1e4).replace(0, np.nan).median())
            ratio = ampl / spr if spr and spr > 0 else float("nan")
            print(f"{sym:6} {f:5} | {a1:>+7.3f} {a2:>+7.3f} {a3:>+7.3f} | {sig:>7.2f} "
                  f"{ampl:>8.3f} {spr:>7.3f} | {ratio:>6.2f}")
        print()
