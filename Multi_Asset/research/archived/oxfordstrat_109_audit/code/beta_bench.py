"""Shared BETA-MATCHED benchmark (5th test added after the re-audit).
A strategy only has a real edge if it beats a buy&hold matched to the classes it trades.
For two-sided/market-neutral strategies buy&hold beta ~ irrelevant (they should beat ~0);
for long-biased ones this is the decisive test. Reuses ftmo_lab (load_universe, CLASS), unchanged."""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab
lab.load_universe = lru_cache(None)(lab.load_universe)
_U = lab.load_universe()

def bh_sharpe(instruments, since=None):
    rs = []
    for t in instruments:
        r = _U[t]['close'].pct_change()
        if since is not None: r = r[r.index > pd.Timestamp(since)]
        rs.append(r)
    if not rs: return float('nan')
    R = pd.concat(rs, axis=1).mean(axis=1).dropna()
    return float(R.mean() / R.std() * np.sqrt(252)) if len(R) > 5 and R.std() > 0 else float('nan')

def beta_line(pool, recent='2018-12-31'):
    """Print strategy full/recent Sharpe vs buy&hold of the dominant traded class. Returns dict."""
    e = pd.to_datetime(pool['entry']); m = lab.trade_metrics(pool); rec = lab.trade_metrics(pool[e > pd.Timestamp(recent)])
    classes = [c for c in ['indices', 'forex', 'commodities', 'crypto']
               if any(lab.CLASS.get(t) == c for t in pool['instr'].unique())]
    inst = list(pool['instr'].unique())
    out = {'full_Sh': m['sharpe'], 'rec_Sh': rec['sharpe'],
           'bh_full': bh_sharpe(inst), 'bh_rec': bh_sharpe(inst, recent)}
    beats = (np.isfinite(rec['sharpe']) and np.isfinite(out['bh_rec']) and rec['sharpe'] > out['bh_rec'] + 0.2)
    print(f"  BETA-MATCHED: strat Sh full {m['sharpe']:+.2f}/rec {rec['sharpe']:+.2f}  vs  buy&hold(traded) "
          f"full {out['bh_full']:+.2f}/rec {out['bh_rec']:+.2f}  -> {'BEATS beta' if beats else 'does NOT beat beta'}")
    out['beats'] = bool(beats); return out
