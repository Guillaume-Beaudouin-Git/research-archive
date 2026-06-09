"""
run_btc_refine.py — refine BTC intraday momentum with regime filters (anti-overfit)
====================================================================================
Candidate: BTCUSD momentum (120-min, z-breakout follow, intraday-flat, hard stop).
Two pre-registered regime filters, each tied to a SPECIFIC failure mode of the candidate:
  V (vol regime)   : skip extreme-vol bars — the -2..-4% losing days (reduced-floor breach)
                     and the 2022 bear chop happen in vol spikes.
  T (trend align)  : take a breakout only with the higher-TF trend — avoid counter-trend
                     whipsaws (2022); in a downtrend it takes only shorts.
Tuned on IS only; judged on the untouched hold-out by P(pass)@3% floor + 2022-bear maxDD
(NOT in-sample Sharpe). on/off to isolate each. A filter that only helps IS = overfit, rejected.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO))
from strategy.fx_data import load_mt5_panel                              # noqa: E402
from strategy.intraday_fx_mr import build_bars, add_mr_signal           # noqa: E402
from strategy.fx_data import to_daily_returns                           # noqa: E402
from engine.cfd_costs import CFDCostModel                               # noqa: E402
from engine.ftmo_first_passage import combined_pass_prob_empirical      # noqa: E402

IS = ("2022-01-01", "2024-12-31"); OOS = ("2025-01-01", "2026-05-29")
DF = load_mt5_panel("BTCUSD")


def make_bars(span):
    b = add_mr_signal(build_bars(DF.loc[span[0]:span[1]], freq="120min", hours=(0, 21)), window=16)
    # higher-TF trend (causal): sign of D-bar return; vol regime (causal): trailing realised vol
    b = b.copy()
    b["ret"] = b["close"].pct_change()
    b["rvol"] = b["ret"].rolling(20).std().shift(1)
    return b


def momentum_filtered(b, z_entry=2.0, z_exit=0.5, stop=0.02, daily_stop=0.02, markup=3.0,
                      vol_q=None, trend_d=None):
    idx = b.index; close = b["close"].values; z = b["z"].values; day = idx.normalize().values
    rvol = b["rvol"].values
    vol_thr = (b["rvol"].rolling(250).quantile(vol_q).shift(1).values
               if vol_q is not None else None)
    trend = (np.sign(b["close"].values - np.concatenate([np.full(trend_d, np.nan), b["close"].values[:-trend_d]]))
             if trend_d is not None else None)
    cm = CFDCostModel("BTCUSD", markup=markup)
    rt = np.asarray(cm.rt_cost_return(b["spread"].values, close))
    n = len(b); gross = np.zeros(n); cost = np.zeros(n); pos = 0; tpnl = 0.0
    for i in range(1, n):
        r = close[i] / close[i - 1] - 1.0
        gross[i] = pos * r
        if pos != 0:
            tpnl += pos * r
        is_last = (i == n - 1) or (day[i + 1] != day[i] if i + 1 < n else True)
        np_ = pos
        if pos != 0 and (tpnl <= -stop or abs(z[i]) < z_exit):
            np_ = 0
        if is_last:
            np_ = 0
        if np_ == 0 and not is_last and z[i] == z[i]:
            vol_ok = True if vol_thr is None else (rvol[i] == rvol[i] and vol_thr[i] == vol_thr[i] and rvol[i] < vol_thr[i])
            long_ok = vol_ok and (True if trend is None else trend[i] > 0)
            short_ok = vol_ok and (True if trend is None else trend[i] < 0)
            if z[i] > z_entry and long_ok:
                np_ = 1
            elif z[i] < -z_entry and short_ok:
                np_ = -1
        if np_ != pos:
            cost[i] += abs(np_ - pos) * 0.5 * rt[i]
            if pos == 0 and np_ != 0:
                tpnl = 0.0
        pos = np_
    g = to_daily_returns(pd.Series(gross, index=idx))
    c = to_daily_returns(pd.Series(cost, index=idx)).reindex(g.index).fillna(0.0)
    trail = g.rolling(63).std().shift(1)
    scale = (0.01 / trail).clip(upper=8.0).fillna(0.0)
    net = ((g - c) * scale).dropna()
    return net


def metrics(net):
    r = net.dropna().values
    if len(r) < 20 or r.std() == 0:
        return {"sharpe": 0.0, "maxdd": np.nan}
    eq = np.cumsum(r); peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(252)), "maxdd": float((peak - eq).max())}


def ppass(net, floor=0.03, sigma=0.006):
    if net.std() == 0:
        return 0.0
    return combined_pass_prob_empirical((net / net.std() * sigma).values, n_paths=10000,
                                        seed=1, daily_floor=floor)["p_combined"]


def main() -> int:
    bIS, bOOS = make_bars(IS), make_bars(OOS)
    bBEAR = make_bars(("2022-01-01", "2022-12-31"))
    print("=" * 92)
    print("BTC momentum refinement — anti-overfit (tune IS, judge hold-out @3% floor + 2022 bear)")
    print("=" * 92)
    print(f"{'config':26} {'IS_sh':>6} {'OOS_sh':>7} {'OOS_pass@3%':>11} {'bear_maxDD%':>11}")

    def row(name, **kw):
        nis, noos, nb = momentum_filtered(bIS, **kw), momentum_filtered(bOOS, **kw), momentum_filtered(bBEAR, **kw)
        print(f"{name:26} {metrics(nis)['sharpe']:>6.2f} {metrics(noos)['sharpe']:>7.2f} "
              f"{ppass(noos)*100:>10.0f}% {metrics(nb)['maxdd']*100:>10.1f}%")
        return metrics(nis), metrics(noos)

    row("base (no filter)")
    print("  -- Filter V (vol regime), tune vol_q on IS --")
    for q in [0.7, 0.8, 0.9]:
        row(f"  +V q={q}", vol_q=q)
    print("  -- Filter T (trend align), tune trend_d on IS --")
    for d in [12, 24, 48]:
        row(f"  +T d={d}", trend_d=d)
    print("  -- Both (IS-best of each) --")
    row("  +V0.8 +T24", vol_q=0.8, trend_d=24)
    print("\nKeep a filter ONLY if it raises hold-out P(pass)@3% and/or fixes the 2022 bear DD (>10%=breach),")
    print("not merely the in-sample Sharpe. Base bear DD ~11% (breach) is the bar to beat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
