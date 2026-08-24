"""Hard intraday stop transform for ASIA_23_8 (series-level, engine unchanged).

Stop level -X% is in ACCOUNT fraction (at sizing K). Per aday:
  acct_low = K * low_base               (intraday MTM low, net of half-spread; from asia_series)
  triggered = acct_low <= -X            (the position's MTM reached -X intraday)
  stopped_net = -X if triggered else K * net_base   (exit at the stop, miss the rest)
  stopped_low = -X if triggered else K * low_base
Edge-erosion mechanism quantified: on triggered days where the unstopped CLOSE recovered
above -X, alpha given up = K*net_base - (-X) (> 0). On days the close was worse, the stop
protects. Net effect read off the post-stop Sharpe.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asia_series as ASER

_BASE = {}


def base(spread_bps=1.5):
    if spread_bps not in _BASE:
        a = ASER.build(spread_bps=spread_bps)
        _BASE[spread_bps] = (a["net_simple"].copy(), a["low_frac"].copy())
    return _BASE[spread_bps]


def apply_stop(K=1.0, X=None, spread_bps=1.5):
    """Return dict with stopped/unstopped aday-indexed series + diagnostics.
    X=None -> no stop (just K-scaled)."""
    net_base, low_base = base(spread_bps)
    net_K = K * net_base
    low_K = K * low_base
    if X is None:
        return dict(net=net_K, low=low_K, triggered=pd.Series(False, index=net_K.index),
                    trig_frac=0.0, alpha_given_up=0.0, protection=0.0)
    triggered = (low_K <= -X)
    net = net_K.where(~triggered, -X)
    low = low_K.where(~triggered, -X)
    agu = (net_K - (-X)).where(triggered & (net_K > -X), 0.0)        # alpha lost on recoveries
    prot = ((-X) - net_K).where(triggered & (net_K < -X), 0.0)       # loss avoided on bad closes
    return dict(net=net, low=low, triggered=triggered,
                trig_frac=float(triggered.mean()),
                alpha_given_up=float(agu.sum()), protection=float(prot.sum()),
                n_trig=int(triggered.sum()))


if __name__ == "__main__":
    for X in (None, 0.015, 0.025, 0.035):
        r = apply_stop(K=1.0, X=X)
        tag = "no-stop" if X is None else f"stop -{X*100:.1f}%"
        print(f"{tag:>12}: trig {r['trig_frac']*100:4.1f}%  mean {r['net'].mean()*1e4:+.2f}bp  "
              f"alpha_given_up {r['alpha_given_up']*100:+.1f}%  protection {r['protection']*100:+.1f}%  "
              f"net_sum {r['net'].sum()*100:+.0f}%")
