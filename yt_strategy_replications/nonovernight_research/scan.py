"""
Search for a NON-overnight intraday edge on gold/silver/WTI/soybean.
Hypotheses (all two-sided / event-driven -> orthogonal to the long overnight drift):
  H1 intraday momentum (pre-US -> US ; first-US -> rest-US)
  H2 intraday mean-reversion (fade the first-US move)
  H3 WTI EIA-inventory Wednesday post-release window
  H4 cross-asset lead-lag (gold pre-US -> silver US, and reverse)
All GROSS first (find structure); winsorised; HAC t and break-even reported.
Run: python scan.py
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import stats as S
spec = importlib.util.spec_from_file_location("iz", HERE.parent / "gold_research" / "intraday.py")
iz = importlib.util.module_from_spec(spec); spec.loader.exec_module(iz)
ANN = 252.0


def vt(w):
    rv = w.rolling(20, min_periods=20).std().shift(1)
    return (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def wins(s):
    return s.clip(s.quantile(0.005), s.quantile(0.995))


def shp(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def evalp(piv, sig_hours, trade_hours, direction=+1, label=""):
    sig = np.sign(wins(iz.win_ret(piv, sig_hours)))
    w = wins(iz.win_ret(piv, trade_hours))
    pos = (direction * sig).reindex(w.index).fillna(0.0) * vt(w)
    g = (pos * w).dropna(); r = g.to_numpy()
    return dict(label=label, n=len(r), gross_sharpe=round(shp(r), 2),
                hac_t=round(S.hac_tstat(r)[1], 2), be_bps=round(r.mean() * 1e4, 2)), g


# per-asset windows (UTC): preUS, US, firstUS, restUS
CFG = {
    "XAUUSD": dict(pre=list(range(0, 13)), us=list(range(13, 21)), first=[13, 14], rest=list(range(15, 21))),
    "XAGUSD": dict(pre=list(range(0, 13)), us=list(range(13, 21)), first=[13, 14], rest=list(range(15, 21))),
    "USOIL":  dict(pre=list(range(0, 13)), us=list(range(13, 20)), first=[13, 14], rest=list(range(15, 20))),
    "SOYBEAN": dict(pre=list(range(1, 13)), us=list(range(13, 19)), first=[13, 14], rest=list(range(15, 19))),
}
print("=== H1 momentum / H2 reversion (gross) ===")
print(f"{'asset':9s}{'strategy':22s}{'n':>6}{'grossSR':>9}{'HACt':>7}{'be_bps':>8}")
edges = {}
for sym, c in CFG.items():
    piv = iz.hourly_pivot(sym, anchor_hour=0)
    if sym == "XAGUSD":
        piv = piv.loc["2014":]
    for lab, sigh, trh, d in [
        ("MOM preUS->US", c["pre"], c["us"], +1),
        ("MOM firstUS->rest", c["first"], c["rest"], +1),
        ("REV firstUS->rest", c["first"], c["rest"], -1),
        ("REV preUS->US", c["pre"], c["us"], -1)]:
        m, g = evalp(piv, sigh, trh, d, lab)
        edges[(sym, lab)] = g
        print(f"{sym:9s}{lab:22s}{m['n']:6d}{m['gross_sharpe']:9.2f}{m['hac_t']:7.2f}{m['be_bps']:8.2f}")

# H3 WTI EIA Wednesday: post-release window vs non-Wed
print("\n=== H3 WTI EIA-day (Wednesday) effects (gross) ===")
oil = iz.hourly_pivot("USOIL", anchor_hour=0)
post = wins(iz.win_ret(oil, [15, 16, 17, 18, 19]))   # post-10:30 ET release window
dow = pd.Series(oil.index.dayofweek, index=oil.index)
for name, mask in [("Wed long post", dow == 2), ("non-Wed long post", dow != 2)]:
    sub = post[mask.reindex(post.index).fillna(False)]
    print(f"  {name:18s} n={len(sub):5d} grossSR {shp((vt(sub)*sub).dropna().to_numpy()):+.2f} mean_bps {sub.mean()*1e4:+.2f}")
# Wed: does the pre-release move predict the post-release move? (drift vs reversion)
pre = wins(iz.win_ret(oil, [13, 14]))
wed = (dow == 2).reindex(oil.index).fillna(False)
df = pd.concat([np.sign(pre).rename("s"), post.rename("p")], axis=1).dropna()
dfw = df[wed.reindex(df.index).fillna(False)]
print(f"  Wed MOM pre->post: grossSR {shp((dfw['s']*dfw['p']).to_numpy()):+.2f} | REV {shp((-dfw['s']*dfw['p']).to_numpy()):+.2f} (n={len(dfw)})")

# H4 cross-asset lead-lag gold<->silver
print("\n=== H4 cross-asset lead-lag (gross) ===")
gpre = np.sign(wins(iz.win_ret(iz.hourly_pivot("XAUUSD", 0), list(range(0, 13)))))
spre = np.sign(wins(iz.win_ret(iz.hourly_pivot("XAGUSD", 0), list(range(0, 13)))))
ag_us = wins(iz.win_ret(iz.hourly_pivot("XAGUSD", 0), list(range(13, 21))))
au_us = wins(iz.win_ret(iz.hourly_pivot("XAUUSD", 0), list(range(13, 21))))
for lab, sig, tr in [("gold_pre -> silver_US", gpre, ag_us), ("silver_pre -> gold_US", spre, au_us)]:
    d = pd.concat([sig.rename("s"), tr.rename("t")], axis=1).dropna()
    print(f"  {lab:24s} grossSR {shp((d['s']*d['t']*vt(d['t'])).to_numpy()):+.2f} (n={len(d)})")

# orthogonality check: correlate the best two-sided edge to a gold overnight proxy
import json
print("\n(Use --deep on the strongest |HACt|>2.5 candidate next.)")
