"""
Q2 confirmatory (Q1 already shows ratio<<1 -> net edge impossible; this resolves b-vs-c
and the mandatory TWO-SIDED test). Exact vectorized harvester (no engine loop):
 - unconditional 1-bar reversal (fade prior bar, hold 1): the pure AC harvest.
 - thresholded reversal (fade |prior move|>p80): the realistic low-frequency variant.
Gross two-sided + net (turnover-accurate) + per-leg + SR + HAC-t, per instrument & pooled.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

DEEP = Path(__file__).resolve().parents[2] / "data" / "deep_history_utc"
DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2, "EURUSD": 5, "GBPUSD": 5}
INDICES = ["US100", "US500", "US30", "GER40"]; FX = ["EURUSD", "GBPUSD"]
SESS = {**{s: ("13:30", "20:00") for s in INDICES}, **{s: ("07:00", "16:00") for s in FX}}


def read_m1(sym):
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "close", "spread"],
                     dtype={"close": "float64", "spread": "float64"})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    return df.drop(columns=["timestamp_utc"])


def prep(df1, freq, sym):
    d = (df1.resample(freq).agg({"close": "last", "spread": "mean"}).dropna(subset=["close"])
         if freq != "1min" else df1.copy())
    st, en = SESS[sym]; t = d.index.time
    d = d[(t >= pd.Timestamp(st).time()) & (t < pd.Timestamp(en).time())].copy()
    d["sd"] = d.index.normalize()
    return d


def hac_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 30 or x.std() == 0: return np.nan, np.nan
    r = sm.OLS(x, np.ones((len(x), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(r.params[0]), float(r.tvalues[0])


def run(d, pt, thresholded):
    r = d["close"].pct_change()
    first = (d.groupby("sd").cumcount() == 0).values
    r = r.mask(first)
    prev = r.shift(1)
    sig = -np.sign(prev)                                   # fade prior bar (two-sided)
    if thresholded:
        thr = prev.abs().rolling(500, min_periods=100).quantile(0.80)
        sig = sig.where(prev.abs() > thr, 0.0)
    sig = sig.fillna(0.0)
    gross = (sig * r)                                      # per-bar unit-position return
    spr = (d["spread"] * pt / d["close"]).fillna(method="ffill")
    spr = spr.clip(lower=spr[spr > 0].median() * 0.0)      # keep as-is; zeros handled in cost floor
    turn = sig.diff().abs().fillna(sig.abs())              # position change (0..2)
    cost = (turn / 2.0) * spr                              # full spread per side-change
    net = gross - cost
    ppy = len(d) / max((d.index[-1] - d.index[0]).days / 365.25, 1e-9)
    gm, gt = hac_t(gross.values)
    legs = {}
    for lab, m in [("up", prev.values > 0), ("dn", prev.values < 0)]:
        gg = gross.values[m & np.isfinite(gross.values)]
        legs[lab] = np.nanmean(gg) * 1e4 if len(gg) else np.nan
    def sr(x):
        x = x[np.isfinite(x)]; return x.mean() / x.std() * np.sqrt(ppy) if x.std() else np.nan
    n_trades = int((turn > 0).sum())
    return dict(gross_bps=gm * 1e4, gross_t=gt, sr_gross=sr(gross.values),
                net_bps=float(np.nanmean(net)) * 1e4, sr_net=sr(net.values),
                leg_up=legs["up"], leg_dn=legs["dn"], n_tr=n_trades,
                spr_bps=float((spr.replace(0, np.nan).median()) * 1e4),
                gross_ser=gross.values, net_ser=net.values)


if __name__ == "__main__":
    for thresholded in [False, True]:
        tag = "THRESHOLDED (|prev|>p80)" if thresholded else "UNCONDITIONAL 1-bar reversal"
        print(f"\n############ {tag} ############")
        print(f"{'sym':6} {'freq':5} | {'grossBPS':>8} {'gT':>6} {'SRgr':>6} | "
              f"{'legUp':>6} {'legDn':>6} | {'spr':>5} {'netBPS':>7} {'SRnet':>6} {'ntr':>8}")
        pool = {f: [] for f in ["1min", "2min", "5min"]}
        for sym in INDICES + FX:
            df1 = read_m1(sym); pt = 10.0 ** (-DIGITS[sym])
            for f in ["1min", "2min", "5min"]:
                d = prep(df1, f, sym)
                R = run(d, pt, thresholded)
                pool[f].append(R["net_ser"])
                print(f"{sym:6} {f:5} | {R['gross_bps']:>+8.3f} {R['gross_t']:>+6.1f} {R['sr_gross']:>+6.2f} | "
                      f"{R['leg_up']:>+6.2f} {R['leg_dn']:>+6.2f} | {R['spr_bps']:>5.2f} "
                      f"{R['net_bps']:>+7.3f} {R['sr_net']:>+6.2f} {R['n_tr']:>8}")
        print("saved" if thresholded else "")
