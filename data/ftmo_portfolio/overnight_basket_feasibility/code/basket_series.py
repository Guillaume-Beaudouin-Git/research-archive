"""Equal-risk overnight-drift BASKET series + DIVERSIFIED intraday low.

Combines the per-sleeve overnight_series at equal weight (1/N of VT'd sleeves = equal-risk, causal).
  basket_net[d]  = sum_i w_i * net_i[d]                       (0 where sleeve absent)
  basket_low[d]  = min over the 23:00-07:00 hourly grid of  sum_i w_i * dip_i,h   - sum_i w_i*half_spread_i
                   where dip_i,h = pos_i * (exp(lp_i,h) - 1)  (RAW account-fraction MtM dip at hour h)
This is the DIVERSIFIED low: min(sum of weighted paths) << sum(individual mins) when imperfectly
correlated — the basket's claimed benefit, tested honestly (raw paths = what the account sees).
Soybean contributes 0 before its 01:00 entry (NaN lp -> 0 dip). N = number of CONFIGURED sleeves
(fixed weight; absent sleeves just contribute less -> basket is partial in early years, reported).

Optional V1 hard stop -X account-fraction baked at K (in basket_inject), not here.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overnight_series as OS

GRID = OS.GRID
LP = [f"lp_{h}" for h in GRID]
ANN = 252.0


def build(sleeves=("GOLD", "SILVER", "WTI"), spread_bps=2.0, winsorise=True):
    N = len(sleeves)
    w = 1.0 / N
    per = {nm: OS.build(nm, spread_bps=spread_bps, winsorise=winsorise) for nm in sleeves}
    idx = sorted(set().union(*[d.index for d in per.values()]))
    idx = pd.DatetimeIndex(idx)

    basket_net = pd.Series(0.0, index=idx)
    n_active = pd.Series(0, index=idx)
    dip_grid = pd.DataFrame(0.0, index=idx, columns=LP)     # weighted summed dip per grid hour
    half = pd.Series(0.0, index=idx)
    pernet = {}
    for nm, d in per.items():
        d = d.reindex(idx)
        net_i = d["net_simple"].fillna(0.0)
        basket_net = basket_net + w * net_i
        active = d["pos"].notna()
        n_active = n_active + active.astype(int)
        pernet[nm] = net_i
        pos_i = d["pos"].fillna(0.0)
        for c in LP:
            dip = pos_i * (np.exp(d[c]) - 1.0)              # raw account-frac dip at hour h; NaN where no bar
            dip_grid[c] = dip_grid[c] + w * dip.fillna(0.0)
    # half-spread: w * half_spread_i on active days
    half = pd.Series(0.0, index=idx)
    sp_half = spread_bps * 1e-4 / 2.0
    for nm, d in per.items():
        d = d.reindex(idx)
        half = half + w * d["pos"].notna().astype(float) * sp_half

    basket_low = dip_grid.min(axis=1) - half
    basket_low = np.minimum(basket_low, basket_net)         # low can't exceed the close P&L
    out = pd.DataFrame({"basket_net": basket_net, "basket_low": basket_low,
                        "n_active": n_active})
    out = out[out["n_active"] > 0]
    for nm in sleeves:
        out[f"net_{nm}"] = pernet[nm].reindex(out.index)
    out.attrs["sleeves"] = list(sleeves)
    return out


def align_to_book(series: pd.Series, book_dates) -> np.ndarray:
    s = series.groupby(series.index.normalize()).sum()
    return s.reindex(book_dates).fillna(0.0).to_numpy(float)


if __name__ == "__main__":
    for sl in [("GOLD", "SILVER", "WTI"), ("GOLD", "SILVER", "WTI", "SOYBEAN"), ("SILVER", "WTI")]:
        d = build(sl, 2.0)
        r = d["basket_net"].to_numpy()
        sh = r.mean() / r.std() * np.sqrt(ANN)
        eq = np.cumprod(1 + r); mdd = (eq / np.maximum.accumulate(eq) - 1).min()
        # sum-of-individual-mins vs diversified-min (diversification check)
        print(f"{'+'.join(sl):28s} n={len(d):4d} | basket net Sh {sh:.2f} | maxDD(close) {mdd*100:.1f}% | "
              f"mean {r.mean()*1e4:+.2f}bp | worst close {r.min()*100:.2f}% | worst intraday-low {d['basket_low'].min()*100:.2f}%")
