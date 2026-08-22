"""
Q2: Donchian breakout backtest (defined-risk, positive-skew exit: sl=1xATR, tp=3xATR,
EOD time-stop). Two-sided by construction. Gross two-sided + net + SKEW + m, per
instrument & pooled. Reuses the audited-equivalent engine. Caches resamples for fast reruns.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as sstats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
from engine import backtest as BT, stats as S, indicators as ind

DEEP = HERE.parents[1] / "data" / "deep_history_utc"
CACHE = HERE / "_cache"; CACHE.mkdir(exist_ok=True)
DIGITS = {"US100": 2, "US500": 2, "US30": 2, "GER40": 2, "EURUSD": 5, "GBPUSD": 5, "XAUUSD": 2}
INDICES = ["US100", "US500", "US30", "GER40", "XAUUSD"]; FX = ["EURUSD", "GBPUSD"]
SESS = {**{s: ("13:30", "20:00") for s in INDICES}, **{s: ("07:00", "16:00") for s in FX}}
SESS_BARS = {"5min": {"idx": 78, "fx": 108}, "15min": {"idx": 26, "fx": 36},
             "30min": {"idx": 13, "fx": 18}, "1h": {"idx": 7, "fx": 9}}
PPY = 252.0
N_TRIALS = 145
STRESS = {"idx": 0.0002, "fx": 0.0001}


def get(sym, freq):
    p = CACHE / f"{sym}_{freq}.parquet"
    if p.exists():
        return pd.read_parquet(p)
    df = pd.read_csv(DEEP / f"{sym}_M1.csv",
                     usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
                     dtype={c: "float64" for c in ["open", "high", "low", "close", "spread"]})
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    d = (df.resample(freq).agg({"open": "first", "high": "max", "low": "min",
                                "close": "last", "spread": "mean"}).dropna(subset=["close"]))
    st, en = SESS[sym]; t = d.index.time
    d = d[(t >= pd.Timestamp(st).time()) & (t < pd.Timestamp(en).time())].copy()
    d.to_parquet(p)
    return d


def donchian_sig(d, N, volfilter=False):
    rh = d["high"].rolling(N).max().shift(1)
    rl = d["low"].rolling(N).min().shift(1)
    sig = np.where(d["close"] > rh, 1.0, np.where(d["close"] < rl, -1.0, 0.0))
    if volfilter:
        atr = ind.atr(d["high"], d["low"], d["close"], n=N)
        sig = np.where(atr > atr.rolling(100, min_periods=50).median(), sig, 0.0)
    atr = ind.atr(d["high"], d["low"], d["close"], n=N)
    return sig, atr.to_numpy()


def daily(trades, c, days):
    if trades.empty:
        return pd.Series(0.0, index=days)
    ret = trades["ret_gross"].to_numpy() - c
    day = pd.DatetimeIndex(trades["exit_time"]).normalize()
    return pd.Series(ret, index=day).groupby(level=0).sum().reindex(days, fill_value=0.0)


def run(sym, freq, N, volfilter):
    d = get(sym, freq)
    cls = "idx" if sym in INDICES else "fx"
    sig, atr = donchian_sig(d, N, volfilter)
    mh = SESS_BARS[freq][cls]
    tr = BT.run_backtest_vectorized(d, sig, sl_dist=1.0 * atr, tp_dist=3.0 * atr,
                                    cost_rt=0.0, max_hold=mh, allow_long=True, allow_short=True)
    if len(tr) < 30:
        return None
    pt = 10.0 ** (-DIGITS[sym])
    cost = float((d["spread"] * pt / d["close"]).replace(0, np.nan).median())
    days = pd.DatetimeIndex(d.index.normalize().unique())
    rg = tr["ret_gross"].to_numpy()
    dg = daily(tr, 0.0, days); dn = daily(tr, cost, days); dS = daily(tr, STRESS[cls], days)
    _, gt = S.hac_tstat(dg.to_numpy(), 6)
    longs = rg[tr["direction"].to_numpy() > 0]; shorts = rg[tr["direction"].to_numpy() < 0]
    return dict(sym=sym, freq=freq, N=N, vf=volfilter, n=len(tr),
                sr_gross=S.sharpe_ratio(dg.to_numpy(), PPY), gt=gt,
                sr_net=S.sharpe_ratio(dn.to_numpy(), PPY),
                sr_stress=S.sharpe_ratio(dS.to_numpy(), PPY),
                leg_long_bps=np.nanmean(longs) * 1e4, leg_short_bps=np.nanmean(shorts) * 1e4,
                skew=float(sstats.skew(rg)), frac_sl=float((tr["reason"] == "sl").mean()),
                frac_tp=float((tr["reason"] == "tp").mean()), cost_bps=cost * 1e4,
                _dn=dn)


CONFIGS = [("15min", 20, False), ("30min", 20, False), ("1h", 20, False),
           ("5min", 20, False), ("30min", 20, True), ("30min", 10, False)]

if __name__ == "__main__":
    pool = {}
    for (freq, N, vf) in CONFIGS:
        tag = f"{freq} D{N}{'+vf' if vf else ''}"
        print(f"\n#### {tag} ####")
        print(f"{'sym':6} | {'n':>5} {'SRgr':>6} {'gT':>5} {'legL':>6} {'legS':>6} | "
              f"{'skew':>5} {'fSL':>4} {'fTP':>4} | {'cost':>4} {'SRnet':>6} {'SRstr':>6}")
        series = []
        for sym in INDICES + FX:
            r = run(sym, freq, N, vf)
            if r is None:
                print(f"{sym:6} | (insufficient)"); continue
            series.append(r["_dn"])
            print(f"{sym:6} | {r['n']:>5} {r['sr_gross']:>+6.2f} {r['gt']:>+5.1f} "
                  f"{r['leg_long_bps']:>+6.1f} {r['leg_short_bps']:>+6.1f} | {r['skew']:>+5.1f} "
                  f"{r['frac_sl']:>4.2f} {r['frac_tp']:>4.2f} | {r['cost_bps']:>4.2f} "
                  f"{r['sr_net']:>+6.2f} {r['sr_stress']:>+6.2f}")
        if series:
            mat = pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
            _, pt_ = S.hac_tstat(mat.to_numpy(), 6)
            dsr = S.deflated_sharpe_ratio(mat.to_numpy(), n_trials=N_TRIALS, periods_per_year=PPY)
            print(f"{'POOL':6} | net SR {S.sharpe_ratio(mat.to_numpy(), PPY):+.2f} (HACt {pt_:+.1f}) "
                  f"DSR(N=145) {dsr.get('dsr', float('nan')):.3f}")
    print("\ndone")
