"""
Q3 confirmation: apply the pre-registered L25 two-sided gate (drop one-legged beta-traps),
add walk-forward (5 folds) + an unconditional-drift control (is the SHORT leg really alpha,
not beta?). Clean two-sided book = GER40, XAUUSD, EURUSD, GBPUSD. Cache is prebuilt.
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

CACHE = HERE / "_cache"
DIGITS = {"GER40": 2, "XAUUSD": 2, "EURUSD": 5, "GBPUSD": 5, "US100": 2}
BOOK = ["GER40", "XAUUSD", "EURUSD", "GBPUSD"]
FXSET = {"EURUSD", "GBPUSD"}
SESS_BARS = {"30min": {"idx": 13, "fx": 18}, "1h": {"idx": 7, "fx": 9}}
PPY = 252.0; N_TRIALS = 145
STRESS = {"idx": 0.0002, "fx": 0.0001}
CONFIGS = [("30min", 20), ("30min", 10), ("1h", 20)]


def donchian(d, N):
    rh = d["high"].rolling(N).max().shift(1); rl = d["low"].rolling(N).min().shift(1)
    sig = np.where(d["close"] > rh, 1.0, np.where(d["close"] < rl, -1.0, 0.0))
    atr = ind.atr(d["high"], d["low"], d["close"], n=N).to_numpy()
    return sig, atr


def daily(tr, c, days):
    if tr.empty:
        return pd.Series(0.0, index=days)
    ret = tr["ret_gross"].to_numpy() - c
    day = pd.DatetimeIndex(tr["exit_time"]).normalize()
    return pd.Series(ret, index=day).groupby(level=0).sum().reindex(days, fill_value=0.0)


def bh_drift_sr(d):
    """Unconditional vol-targeted buy&hold SR over session days (beta benchmark)."""
    r = d["close"].pct_change().fillna(0.0)
    dd = r.groupby(d.index.normalize()).sum()
    return S.sharpe_ratio(dd.to_numpy(), PPY)


if __name__ == "__main__":
    for (freq, N) in CONFIGS:
        print(f"\n#### two-sided book — {freq} Donchian{N} (sl1xATR tp3xATR, EOD) ####")
        print(f"{'sym':6} | {'n':>5} {'netSR':>6} {'strSR':>6} {'WF':>4} {'skew':>5} "
              f"{'legL':>6} {'legS':>6} | {'B&H_SR':>6} (drift control)")
        netser = []; strser = []
        for sym in BOOK:
            d = pd.read_parquet(CACHE / f"{sym}_{freq}.parquet")
            cls = "fx" if sym in FXSET else "idx"
            sig, atr = donchian(d, N)
            tr = BT.run_backtest_vectorized(d, sig, sl_dist=1.0*atr, tp_dist=3.0*atr,
                                            cost_rt=0.0, max_hold=SESS_BARS[freq][cls],
                                            allow_long=True, allow_short=True)
            if len(tr) < 30:
                print(f"{sym:6} | insufficient"); continue
            pt = 10.0 ** (-DIGITS[sym])
            cost = float((d["spread"]*pt/d["close"]).replace(0, np.nan).median())
            days = pd.DatetimeIndex(d.index.normalize().unique())
            dn = daily(tr, cost, days); dS = daily(tr, STRESS[cls], days)
            netser.append(dn); strser.append(dS)
            rg = tr["ret_gross"].to_numpy()
            wf = S.fold_metrics(dn.to_numpy(), 5, PPY)["wf_score"]
            lL = np.nanmean(rg[tr["direction"].to_numpy() > 0])*1e4
            lS = np.nanmean(rg[tr["direction"].to_numpy() < 0])*1e4
            print(f"{sym:6} | {len(tr):>5} {S.sharpe_ratio(dn.to_numpy(),PPY):>+6.2f} "
                  f"{S.sharpe_ratio(dS.to_numpy(),PPY):>+6.2f} {wf:>4.0%} {sstats.skew(rg):>+5.1f} "
                  f"{lL:>+6.1f} {lS:>+6.1f} | {bh_drift_sr(d):>+6.2f}")
        if netser:
            mat = pd.concat(netser, axis=1).fillna(0.0).mean(axis=1)
            matS = pd.concat(strser, axis=1).fillna(0.0).mean(axis=1)
            _, t = S.hac_tstat(mat.to_numpy(), 6)
            dsr = S.deflated_sharpe_ratio(mat.to_numpy(), n_trials=N_TRIALS, periods_per_year=PPY)
            wf = S.fold_metrics(mat.to_numpy(), 5, PPY)
            print(f"{'BOOK':6} | net SR {S.sharpe_ratio(mat.to_numpy(),PPY):+.2f} (HACt {t:+.1f}) "
                  f"stressSR {S.sharpe_ratio(matS.to_numpy(),PPY):+.2f} | WF {wf['wf_score']:.0%} "
                  f"folds {wf['fold_sharpes']} | DSR(N=145) {dsr.get('dsr',float('nan')):.3f}")
    print("\ndone")
