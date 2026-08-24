"""Hard intraday stop + USDA-skip transforms for SOYBEAN (series-level, engine unchanged).

Adapted from asia_stop.py (validated in the asia funded study). Builds the K-scaled,
optionally stopped and/or USDA-skipped aday-indexed (net, low, traded) series fed to
soy_fp / soy_inject (which then run with lev=1.0, since K is baked here).

  net_K = K * net_simple ; low_K = K * low_frac           (from soy_series; account fraction)
  V1 stop -X (account fraction): triggered = low_K <= -X
     stopped_net = -X if triggered else net_K   (exit at the stop, miss the recovery)
     stopped_low = -X if triggered else low_K
  V2 skip USDA: on report/day-after mornings -> net=low=0, traded=False (flat that day)
Edge-erosion of the stop is read off post-stop Sharpe + alpha_given_up vs protection.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import soy_series as SS

_BASE: dict = {}


def base(spread_bps=2.0):
    if spread_bps not in _BASE:
        a = SS.build(spread_bps=spread_bps)
        _BASE[spread_bps] = (a["net_simple"].copy(), a["low_frac"].copy(),
                             a["is_usda"].astype(bool).copy())
    return _BASE[spread_bps]


def apply(K=1.0, X=None, skip_usda=False, spread_bps=2.0):
    """Return dict: K-scaled (+stop/+skip) aday-indexed net/low/traded + diagnostics.
    X=None -> no stop. X in account fraction (e.g. 0.025 = -2.5%)."""
    net_base, low_base, usda = base(spread_bps)
    net = K * net_base
    low = K * low_base
    triggered = pd.Series(False, index=net.index)
    agu = prot = 0.0
    if X is not None:
        triggered = (low <= -X)
        net_unstopped = net.copy()
        net = net.where(~triggered, -X)
        low = low.where(~triggered, -X)
        agu = float((net_unstopped - (-X)).where(triggered & (net_unstopped > -X), 0.0).sum())
        prot = float(((-X) - net_unstopped).where(triggered & (net_unstopped < -X), 0.0).sum())
    traded = pd.Series(True, index=net.index)
    if skip_usda:
        net = net.where(~usda, 0.0)
        low = low.where(~usda, 0.0)
        traded = traded & ~usda
    return dict(net=net, low=low, traded=traded, triggered=triggered,
                trig_frac=float(triggered.mean()), n_trig=int(triggered.sum()),
                alpha_given_up=agu, protection=prot,
                n_skip=int(usda.sum()) if skip_usda else 0)


if __name__ == "__main__":
    print("=== stop sweep (K=1, spread 2bp) ===")
    for X in (None, 0.015, 0.02, 0.025, 0.035):
        r = apply(K=1.0, X=X)
        n = r["net"]; sh = n.mean() / n.std() * np.sqrt(252) if n.std() > 0 else float("nan")
        tag = "no-stop" if X is None else f"stop -{X*100:.1f}%"
        print(f"{tag:>12}: trig {r['trig_frac']*100:4.1f}%  Sharpe {sh:5.2f}  mean {n.mean()*1e4:+.2f}bp  "
              f"alpha_gup {r['alpha_given_up']*100:+5.1f}%  protect {r['protection']*100:+5.1f}%  "
              f"worst {n.min()*100:.2f}%")
    print("\n=== skip USDA (K=1, spread 2bp) ===")
    for sk in (False, True):
        r = apply(K=1.0, X=None, skip_usda=sk)
        n = r["net"][r["traded"]] if sk else r["net"]
        sh = n.mean() / n.std() * np.sqrt(252)
        print(f"skip_usda={sk}: n_traded {int(r['traded'].sum())}  Sharpe {sh:5.2f}  "
              f"mean {n.mean()*1e4:+.2f}bp  worst {n.min()*100:.2f}%  n_skip {r['n_skip']}")
