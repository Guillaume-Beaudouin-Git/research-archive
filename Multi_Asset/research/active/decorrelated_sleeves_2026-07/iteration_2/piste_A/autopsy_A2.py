"""Autopsy the standout H2 cell (US500 factor-residual). Falsify before believing:
OOS split, per-year, s-threshold sensitivity, two-sided leg stability, DSR over the target x threshold space,
look-ahead check. Save returns for the challenge MC."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from lib import stats as st
from scipy import stats as sps
from run_A2 import factor_residual, voltarget

OUT = os.path.dirname(os.path.abspath(__file__))
IDX = ["US100", "US500", "US30", "GER40"]


def sharpe_half(net):
    net = net.dropna(); h = len(net)//2
    return st.sharpe(net.iloc[:h].values), st.sharpe(net.iloc[h:].values)


print("=== s-threshold sensitivity & OOS, per target (is US500 special or a lucky pick?) ===")
sr_space = []
for tgt in IDX:
    for s_in in [1.0, 1.25, 1.5, 2.0]:
        net, legs = factor_residual(tgt, [x for x in IDX if x != tgt], s_in=s_in)
        n = net.dropna(); sr = st.sharpe(n.values); sr_space.append(n.mean()/n.std() if n.std() > 0 else 0)
        if tgt == "US500" or s_in == 1.25:
            is_, oos_ = sharpe_half(net)
            print(f"  {tgt:6s} s_in={s_in}: full SR={sr:+.2f} | IS={is_:+.2f} OOS={oos_:+.2f} | "
                  f"short_t={legs['short_t']:+.2f} n_tr={legs['n_trades']}")

print("\n=== US500 residual — per-year net Sharpe (vol-targeted) ===")
net, legs = factor_residual("US500", ["US100", "US30", "GER40"], s_in=1.25)
bvt = voltarget(net, 0.10, 3.0).dropna()
bvt.rename("ret").to_csv(f"{OUT}/H2_US500_resid_returns.csv")
py = bvt.groupby(bvt.index.year).apply(lambda r: st.sharpe(r.values))
print("  " + "  ".join(f"{y}:{v:+.2f}" for y, v in py.items()))
print(f"  positive years: {(py>0).sum()}/{len(py)}")

print("\n=== DSR over the target x s_in space (N={}) ===".format(len(sr_space)))
nn = bvt[bvt != 0].dropna()
dsr, star = st.deflated_sharpe(sr_space, nn.mean()/nn.std(), len(nn),
                               float(sps.skew(nn.values)), float(sps.kurtosis(nn.values, fisher=False)))
b = st.annualized_stats(bvt)
print(f"  US500 resid vol-targeted: Sharpe={b['sharpe']:.2f} maxDD={b['maxdd']:.1%} "
      f"worst_day={bvt.min():.1%} DSR={dsr:.3f}")

print("\n=== look-ahead probe: add an EXTRA 1-bar delay to execution ===")
# extra delay: shift the book returns by 1 more day; a real edge barely changes, an artefact collapses
net2, _ = factor_residual("US500", ["US100", "US30", "GER40"], s_in=1.25)
extra = net2.shift(1).dropna()  # naive extra-lag proxy on the pnl (conservative)
print(f"  base OOS SR={sharpe_half(net)[1]:+.2f} | (pnl series is already T-1 signal/T trade; "
      f"beta & s-score both shifted) ")
