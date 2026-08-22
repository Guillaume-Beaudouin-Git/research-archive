"""
Q1 (measure-first): does CONTINUATION have a gross edge at some scale (M5/M15/M30/H1)?
- AC(1) of within-session returns (positive = continuation).
- Conditional post-breakout forward return (Donchian-20, hold H=8 bars, two-sided) vs spread.
ratio = |continuation bps| / RT spread bps. If <1 everywhere => net breakout impossible.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

DEEP = Path(__file__).resolve().parents[2] / "data" / "deep_history_utc"
DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2, "EURUSD": 5, "GBPUSD": 5, "XAUUSD": 2}
INDICES = ["US100", "US500", "US30", "GER40", "XAUUSD"]; FX = ["EURUSD", "GBPUSD"]
SESS = {**{s: ("13:30", "20:00") for s in INDICES}, **{s: ("07:00", "16:00") for s in FX}}
SCALES = ["5min", "15min", "30min", "1h"]
N, H = 20, 8


def read_m1(sym):
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
                     dtype={c: "float64" for c in ["open", "high", "low", "close", "spread"]})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    return df.drop(columns=["timestamp_utc"])


def prep(df1, freq, sym):
    d = (df1.resample(freq).agg({"open": "first", "high": "max", "low": "min",
                                 "close": "last", "spread": "mean"}).dropna(subset=["close"]))
    st, en = SESS[sym]; t = d.index.time
    d = d[(t >= pd.Timestamp(st).time()) & (t < pd.Timestamp(en).time())].copy()
    d["sd"] = d.index.normalize()
    return d


def hac_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 20 or x.std() == 0: return np.nan, np.nan
    r = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(r.params[0]), float(r.tvalues[0])


def analyze(d, pt):
    r = d["close"].pct_change()
    first = (d.groupby("sd").cumcount() == 0).values
    r = r.mask(first)
    ac1 = float(pd.Series(r).autocorr(lag=1))
    rh = d["high"].rolling(N).max().shift(1)
    rl = d["low"].rolling(N).min().shift(1)
    up = (d["close"] > rh).values
    dn = (d["close"] < rl).values
    entry = d["open"].shift(-1)
    exit_ = d["close"].shift(-H)
    fwd = (exit_ / entry - 1.0).values
    g = d.groupby("sd")
    bte = (g["close"].transform("size") - 1 - g.cumcount()).values
    ok = (bte >= H) & np.isfinite(fwd)
    cont = np.where(up & ok, fwd, np.where(dn & ok, -fwd, np.nan))
    m, t = hac_t(cont)
    legup = np.nanmean(np.where(up & ok, fwd, np.nan))
    legdn = np.nanmean(np.where(dn & ok, -fwd, np.nan))
    spr = float((d["spread"] * pt / d["close"] * 1e4).replace(0, np.nan).median())
    nbrk = int(np.nansum((up | dn) & ok))
    return ac1, m * 1e4, t, legup * 1e4, legdn * 1e4, spr, nbrk


if __name__ == "__main__":
    print(f"{'sym':6} {'scale':5} | {'AC1':>7} | {'contBPS':>8} {'t':>6} {'legUp':>7} {'legDn':>7} "
          f"| {'spr':>5} {'ratio':>6} {'nbrk':>7}")
    print("-" * 86)
    for sym in INDICES + FX:
        df1 = read_m1(sym); pt = 10.0 ** (-DIGITS[sym])
        for f in SCALES:
            d = prep(df1, f, sym)
            ac1, cb, t, lu, ld, spr, nbrk = analyze(d, pt)
            ratio = abs(cb) / spr if spr and spr > 0 else float("nan")
            print(f"{sym:6} {f:5} | {ac1:>+7.3f} | {cb:>+8.2f} {t:>+6.1f} {lu:>+7.2f} {ld:>+7.2f} "
                  f"| {spr:>5.2f} {ratio:>6.2f} {nbrk:>7}")
        print()
