#!/usr/bin/env python3
"""TSMOM v3 — risk overlays on the best v2 config (decorr6, lb(60,120,250), θ0.34)
to lift Calmar / FTMO p(funded): (a) equity-curve gate, (b) drawdown throttle,
(c) vol-spike de-risk. Goal: cut the maxDD that breaches the floor."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from tsmom_engine import load_basket, stats, ftmo_daily

DEC = ["US500","GLD","SLV","USO","BTC","ETH"]


def base_port(px, lookbacks=(60,120,250), inst=DEC, theta=0.34, port_vol=0.10, cost_bps=2.0,
              eq_gate=False, dd_throttle=False, vol_derisk=False):
    px = px[inst].dropna(how="all")
    rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std() * np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks) / len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    w = (0.10 / rv).clip(upper=5.0)
    pos = (sig * w).shift(1)
    gross = (pos * rets).sum(axis=1)
    pv = gross.rolling(60).std() * np.sqrt(252)
    port = (gross * (port_vol / pv).clip(upper=3.0).shift(1)).fillna(0.0)
    turn = pos.diff().abs().sum(axis=1)
    port = port - turn * cost_bps * 1e-4
    # --- overlays (all causal) ---
    if vol_derisk:
        rvol = port.rolling(20).std() * np.sqrt(252)
        port = port * (port_vol / rvol).clip(upper=1.0).shift(1).fillna(1.0)
    if eq_gate or dd_throttle:
        eq = (1 + port).cumprod()
        if eq_gate:
            ma = eq.rolling(100).mean()
            g = (eq > ma).astype(float).shift(1).fillna(1.0)      # de-risk below equity MA
            port = port * (0.4 + 0.6 * g)                          # 40% when below, 100% above
        if dd_throttle:
            dd = eq / eq.cummax() - 1
            thr = (1 + dd / 0.10).clip(0.3, 1.0).shift(1).fillna(1.0)  # cut as DD approaches 10%
            port = port * thr
    return port.dropna()


def fp_sweep(sr, name):
    print(f"  {name}: " + stats(sr.values, "").__str__())
    best = (0, None)
    for L in (2,3,4,5,6):
        r = ftmo_daily(sr.values, L)
        if r["p_funded"] > best[0]: best = (r["p_funded"], r)
    b = best[1]
    print(f"     best FTMO: p(funded) {b['p_funded']*100:.0f}% bust {b['bust']*100:.0f}% L{b['L']} med {b['med_mo']}mo "
          f"| multi-attempt 2x={1-(1-b['p_funded'])**2:.0%} 3x={1-(1-b['p_funded'])**3:.0%}")
    return best[0]


def main():
    px = load_basket()
    print("=== v3 risk overlays (best v2 base = decorr6 lb(60,120,250) θ0.34) ===")
    fp_sweep(base_port(px), "v2 base (no overlay)")
    fp_sweep(base_port(px, vol_derisk=True), "+ vol de-risk")
    fp_sweep(base_port(px, eq_gate=True), "+ equity-curve gate")
    fp_sweep(base_port(px, dd_throttle=True), "+ drawdown throttle")
    fp_sweep(base_port(px, eq_gate=True, vol_derisk=True), "+ eq-gate + vol-derisk")
    fp_sweep(base_port(px, dd_throttle=True, vol_derisk=True), "+ dd-throttle + vol-derisk")
    best = base_port(px, dd_throttle=True, vol_derisk=True)
    print("\nDetail best-overlay by-year:")
    by = best.groupby(best.index.year).apply(lambda x:round((np.prod(1+x.values)-1)*100,0))
    print(" ", {int(y):v for y,v in by.items()})
    print(" full sweep:")
    for L in (2,3,4,5,6,8): print("   ", ftmo_daily(best.values, L))


if __name__ == "__main__":
    main()
