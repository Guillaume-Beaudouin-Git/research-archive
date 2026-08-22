"""Overnight sleeve rebuilt on CASH session times from M5 closes (CET).
US100: cash open 15:30, close 22:00 CET. GER40: Xetra open 09:00, close 17:30.
Verified target (OVERNIGHT_VERIFICATION_REPORT): NQ all-nights +4.9 bps t=4.04;
midweek (Tue/Wed open-days) ~+7.4/+8.7 bps gross; US100 CFD confirms +10.3 (Tue, 2021+).
"""
import numpy as np
import pandas as pd
import config as C

OUT = {}
for sym, (h_open, h_close) in {"US100": ("15:30", "22:00"),
                               "GER40": ("09:00", "17:30")}.items():
    m5 = pd.read_parquet(C.CACHE / f"{sym}_m5_close.parquet")["close"]
    df = m5.to_frame("px")
    df["d"] = df.index.date
    t = df.index.strftime("%H:%M")
    opens = df[t == h_open].set_index("d")["px"]
    closes = df[t == h_close].set_index("d")["px"]
    cal = pd.DataFrame({"open": opens, "close": closes}).dropna()
    cal.index = pd.to_datetime(cal.index)
    ov = (cal["open"] / cal["close"].shift(1) - 1) * 1e4   # bps, open-day indexed
    wd = ov.index.dayofweek
    res = {}
    for name, mask in {"all": np.ones(len(ov), bool), "Mon": wd == 0, "Tue": wd == 1,
                       "Wed": wd == 2, "Thu": wd == 3, "Fri": wd == 4}.items():
        x = ov[mask].dropna()
        x = x[x.abs() < 800]   # guard vs roll/holiday artifacts
        res[name] = dict(mean=x.mean(), t=x.mean() / x.std() * np.sqrt(len(x)), n=len(x))
    OUT[sym] = pd.DataFrame(res).T
    print(f"=== {sym} overnight (bps/night, {cal.index.min().date()}->{cal.index.max().date()}) ===")
    print(OUT[sym].round(2).to_string())
    # save the overnight return series for the sleeve
    ov.to_frame("ov_bps").to_parquet(C.CACHE / f"{sym}_overnight_bps.parquet")
print("\nsaved *_overnight_bps.parquet")
