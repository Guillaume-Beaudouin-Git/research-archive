#!/usr/bin/env python3
"""DECISIVE TEST (L33): TSMOM net of REAL per-night swap on held notional.
The original cost model charged turnover*2bps (wrong axis for a low-turnover,
position-HOLDING strategy). Here we charge swap on the gross notional of every
held leg, EVERY night, at per-leg rates. Sweep rates. Re-run FTMO first-passage."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
from tsmom_engine import load_basket

INST = ["US500", "GLD", "SLV", "USO", "BTC", "ETH"]
INIT, P1, P2, FLOOR, DAILY = 1e4, 1.10, 1.05, 9e3, 0.05


def strat_net(px, swap_bps, inst=INST, lookbacks=(60,120,250), theta=0.34, port_vol=0.10, cost_bps=2.0):
    px = px[inst].dropna(how="all"); rets = px.pct_change().clip(-0.5, 0.5)
    rv = rets.rolling(60).std()*np.sqrt(252)
    sig = sum(np.sign(px.pct_change(L)) for L in lookbacks)/len(lookbacks)
    sig = sig.where(sig.abs() >= theta, 0.0)
    pos = (sig*(0.10/rv).clip(upper=5.0)).shift(1)             # per-inst vol-targeted weight
    gross = (pos*rets).sum(1)
    scale = (port_vol/(gross.rolling(60).std()*np.sqrt(252))).clip(upper=3.0).shift(1)
    port = (gross*scale).fillna(0.0) - pos.diff().abs().sum(1)*cost_bps*1e-4
    mult_vd = (port_vol/(port.rolling(20).std()*np.sqrt(252))).clip(upper=1.0).shift(1).fillna(1.0)
    port = port*mult_vd
    eqc = (1+port).cumprod(); g = (eqc > eqc.rolling(100).mean()).astype(float).shift(1).fillna(1.0)
    mult_eg = 0.4 + 0.6*g
    port = port*mult_eg
    Stot = (scale.fillna(0.0)*mult_vd*mult_eg)                 # total book scaling at L=1
    # per-night swap on held notional, per leg
    swap = pd.Series(0.0, index=px.index)
    gnot = pd.Series(0.0, index=px.index)
    for c in inst:
        notion = pos[c].abs()*Stot                             # |notional| of leg c, L=1
        gnot += notion
        swap += notion * (swap_bps[c]*1e-4)
    net = (port - swap).dropna()
    return net, float(gnot.mean()), float(swap.dropna().mean()*252*100)   # net, avg gross notional, ann swap drag %


def fp(sr, L, cap=1260, step=8):
    N = len(sr); st = np.arange(0, N-5, step); f = b = 0; tt = []
    for a in st:
        eq, i, end, ok = INIT, a, min(a+cap, N), None
        while i < end:
            c = L*sr[i]
            if c <= -DAILY or eq*(1+c) < FLOOR: b += 1; ok = False; break
            eq *= 1+c
            if eq >= INIT*P1: ok = True; break
            i += 1
        if ok is not True: continue
        d1 = i-a; eq = INIT; i += 1
        while i < end:
            c = L*sr[i]
            if c <= -DAILY or eq*(1+c) < FLOOR: b += 1; break
            eq *= 1+c
            if eq >= INIT*P2: f += 1; tt.append(i-a); break
            i += 1
    n = len(st); return f/n, b/n, (np.median(tt)/21 if tt else None)


def sharpe(sr):
    nz = sr[sr != 0]; return sr.mean()/nz.std()*np.sqrt(252)


def main():
    px = load_basket()
    # per-leg per-night swap scenarios (bps of notional/night). Both directions (CFD markup).
    scen = {
      "0 swap-free (the 71% baseline)": dict(US500=0,GLD=0,SLV=0,USO=0,BTC=0,ETH=0),
      "LOW  (idx/metal 1.5, oil 2, crypto 5)": dict(US500=1.5,GLD=1.5,SLV=1.5,USO=2,BTC=5,ETH=5),
      "MID realistic (idx/metal 2.5, oil 3, crypto 12)": dict(US500=2.5,GLD=2.5,SLV=2.5,USO=3,BTC=12,ETH=12),
      "HIGH (idx/metal 4, oil 5, crypto 25)": dict(US500=4,GLD=4,SLV=4,USO=5,BTC=25,ETH=25),
    }
    print("TSMOM net-of-real-swap — DECISIVE TEST (L33)")
    print(f"{'swap scenario':48s} grossNotl  swapDrag%/yr@1.5x  Sharpe  p(fund)@1.5x  bust")
    for name, sw in scen.items():
        net, gnot, drag = strat_net(px, sw)
        f15, b15, med = fp(net.values, 1.5)
        print(f"{name:48s}  {gnot:4.2f}x    {drag*1.5:6.1f}%        {sharpe(net.values):+.2f}    {f15*100:4.0f}%       {b15*100:3.0f}%")
    # no-crypto core under MID swap (drops the worst-swap legs + broken USO)
    print("\nCore subsets under MID swap (drop crypto / drop oil):")
    for sub,lbl in [(["US500","GLD","SLV","USO"],"no-crypto"),(["US500","GLD","SLV"],"idx+metals only")]:
        sw = {c:(2.5 if c in('US500','GLD','SLV') else 3) for c in sub}
        net,gnot,drag = strat_net(px, sw, inst=sub)
        f15,b15,med = fp(net.values,1.5)
        print(f"  {lbl:16s}: grossNotl {gnot:.2f}x  drag {drag*1.5:.1f}%/yr@1.5x  Sharpe {sharpe(net.values):+.2f}  p(fund)@1.5x {f15*100:.0f}%  bust {b15*100:.0f}%")


if __name__ == "__main__":
    main()
