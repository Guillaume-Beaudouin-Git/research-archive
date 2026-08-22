#!/usr/bin/env python3
"""TSMOM iteration: multi-lookback blend, trend-strength filter, compliance-clean
(decorrelated) universe, vol-target/port-vol sweep. Find the best FTMO config."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from tsmom_engine import load_basket, stats, ftmo_daily


def tsmom_ml(px, lookbacks=(30,60,120,250), target_vol=0.10, inst=None, theta=0.0,
             cost_bps=2.0, port_vol=0.10):
    inst = inst or list(px.columns)
    px = px[inst].dropna(how="all")
    rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)
    # multi-lookback blended signal in [-1,1]
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)
    if theta > 0:
        sig = sig.where(sig.abs() >= theta, 0.0)
    w = (target_vol / rv).clip(upper=5.0)
    pos = (sig * w).shift(1)
    gross = (pos * rets).sum(axis=1)
    pv = gross.rolling(60).std() * np.sqrt(252)
    port = gross * (port_vol / pv).clip(upper=3.0).shift(1)
    turn = pos.diff().abs().sum(axis=1)
    return (port - turn * cost_bps*1e-4).dropna()


def best_fp(sr):
    best = (0, None)
    for L in (2,3,4,5,6,8):
        r = ftmo_daily(sr, L)
        if r["p_funded"] > best[0]: best = (r["p_funded"], r)
    return best[1]


def main():
    px = load_basket()
    decorr = ["US500","GLD","SLV","USO","BTC","ETH"]      # compliance-clean (1 equity)
    core5  = ["US500","GER40","GLD","SLV","USO"]
    print("=== ITERATION: multi-lookback + filter + universe ===")
    configs = []
    for inst,iname in [(core5,"core5"),(decorr,"decorr6")]:
        for lb in [(60,120,250),(30,60,120,250),(120,250)]:
            for theta in (0.0, 0.34, 0.5):
                for pv in (0.10, 0.15):
                    port = tsmom_ml(px, lookbacks=lb, inst=inst, theta=theta, port_vol=pv)
                    s = stats(port.values)
                    fp = best_fp(port.values)
                    calmar = s["ann"]/abs(s["maxdd"]) if s["maxdd"] else 0
                    configs.append((iname,lb,theta,pv,s,fp,calmar))
    configs.sort(key=lambda c: c[5]["p_funded"], reverse=True)
    print("top 8 by FTMO p(funded):")
    for iname,lb,theta,pv,s,fp,cal in configs[:8]:
        print(f"  {iname} lb{lb} θ{theta} pv{pv}: Sh {s['sharpe']:+.2f} skew {s['skew']:+.2f} "
              f"maxDD {s['maxdd']}% Calmar {cal:.2f} | p(funded) {fp['p_funded']*100:.0f}% bust {fp['bust']*100:.0f}% (L{fp['L']})")
    # detail on the best
    iname,lb,theta,pv,s,fp,cal = configs[0]
    print(f"\nBEST: {iname} lb{lb} θ{theta} pv{pv} -> {s}")
    port = tsmom_ml(px, lookbacks=lb, inst=(decorr if iname=='decorr6' else core5), theta=theta, port_vol=pv)
    by = port.groupby(port.index.year).apply(lambda x:round((np.prod(1+x.values)-1)*100,0))
    print("  by-year:", {int(y):v for y,v in by.items()})
    print("  full leverage sweep:")
    for L in (2,3,4,5,6,8): print("   ", ftmo_daily(port.values, L))


if __name__ == "__main__":
    main()
