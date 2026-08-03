"""TEST B, addendum — robustness of the delayed-entry version and its economics.

Reads the session tables written by test_b_subwindows.py (scratchpad only).
Nothing here re-chooses a window or a parameter: the delay ladder is the
pre-registered one, and every number is reported for the whole ladder.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT = Path(sys.argv[1]) / "testB"
DELAYS = (0, 1, 2, 3, 5, 10, 15, 20, 30)
COST_CENTRE, COST_TAIL = 1.84, 3.88


def hac(x) -> tuple[float, float, int]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 30:
        return (np.nan, np.nan, len(x))
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return (float(m.params[0]), float(m.tvalues[0]), len(x))


G = pd.read_parquet(OUT / "XAUUSD_sessions.parquet")
core = G.dropna(subset=["gap", "win_cap"])
post = core[core["year"] >= 2021]
pd.set_option("display.width", 260, "display.max_columns", 60)

# ------------------------------------------------------------------ first-hour share
print("=== B · how much of the 8h window lives in the first hour? (L56 re-examined) ===")
rows = []
for lab, g in (("full", core), ("pre2018", core[core.year < 2018]),
               ("2018_2020", core[(core.year >= 2018) & (core.year < 2021)]),
               ("post2021", post)):
    h1 = g["cum60"].mean()
    w = g["win_cap"].mean()
    rows.append(dict(sample=lab, N=len(g), hour1_bps=h1, window8h_bps=w,
                     hour1_share_pct=100 * h1 / w if w else np.nan,
                     first5min_bps=g["cum5"].mean(),
                     first5_share_pct=100 * g["cum5"].mean() / w if w else np.nan,
                     t_hour1=hac(g["cum60"])[1], t_first5=hac(g["cum5"])[1]))
S = pd.DataFrame(rows)
S.to_csv(OUT / "b_hour1_share.csv", index=False)
print(S.round(2).to_string(index=False))

# ------------------------------------------- robustness of the mean: trims, not top-cuts
print("\n=== B · KB5 revisited — the right robustness test for a symmetric-return sleeve ===")
rr = []
for lab, g in (("full", core), ("post2021", post)):
    for d in (0, 5, 10, 15):
        x = g[f"tailfix{d}"].dropna()
        lo, hi = x.quantile([0.05, 0.95])
        loW, hiW = x.quantile([0.005, 0.995])
        rr.append(dict(sample=lab, delay=d, n=len(x), mean=x.mean(),
                       median=x.median(), win_rate=(x > 0).mean(),
                       trim5_sym=x[(x > lo) & (x < hi)].mean(),
                       winsor_0p5=x.clip(loW, hiW).mean(),
                       drop_top5=x[x < hi].mean(), skew=x.skew()))
R = pd.DataFrame(rr)
R.to_csv(OUT / "b_robust.csv", index=False)
print(R.round(3).to_string(index=False))

# ---------------------------------------------------------------- year-by-year, delayed
print("\n=== B · year by year, entry delayed 10 min from the first executable print ===")
yy = core.groupby("year").agg(n=("tailfix10", "size"), mean=("tailfix10", "mean"),
                              wr=("tailfix10", lambda s: (s > 0).mean()))
yy["pos"] = yy["mean"] > 0
print(yy.round(2).to_string())
yy.to_csv(OUT / "b_by_year.csv")
print(f"positive years: full {int(yy['pos'].sum())}/{len(yy)} | "
      f"post-2021 {int(yy.loc[yy.index >= 2021, 'pos'].sum())}/{len(yy[yy.index >= 2021])}")

# ------------------------------------------------------------------------- economics
print("\n=== B · economics: gross, and net at both ends of the unresolved cost range ===")
ec = []
for lab, g in (("full", core), ("post2021", post)):
    yrs = (g.index[-1] - g.index[0]).days / 365.25
    n_yr = len(g) / yrs
    for d in DELAYS:
        m, t, n = hac(g[f"tailfix{d}"])
        sd = g[f"tailfix{d}"].std()
        for cost, ctag in ((COST_CENTRE, "1.84"), (COST_TAIL, "3.88")):
            net = m - cost
            ec.append(dict(sample=lab, delay=d, gross=m, t=t, cost=ctag, net_bps=net,
                           net_pct_yr=net * n_yr / 100,
                           SR_net=net / sd * np.sqrt(n_yr) if sd else np.nan,
                           cost_share_pct=100 * cost / m if m > 0 else np.nan))
E = pd.DataFrame(ec)
E.to_csv(OUT / "b_economics.csv", index=False)
print(E[E["sample"] == "post2021"].pivot(index="delay", columns="cost",
      values=["net_bps", "SR_net", "cost_share_pct"]).round(2).to_string())
print("\n(full sample, for reference)")
print(E[E["sample"] == "full"].pivot(index="delay", columns="cost",
      values=["net_bps", "SR_net", "cost_share_pct"]).round(2).to_string())

# ------------------------------------------- where does the window return actually sit?
print("\n=== B · segment decomposition of the 8h window (post-2021), bps ===")
seg = []
edges = [0, 5, 15, 30, 60]
for a, b in zip(edges[:-1], edges[1:]):
    m, t, n = hac(post[f"cum{b}"] - post[f"cum{a}"])
    seg.append(dict(segment=f"t0+{a} -> t0+{b} min", bps=m, t=t, N=n))
m, t, n = hac(post["win_cap"] - post["cum60"])
seg.append(dict(segment="t0+60 min -> window end (7h)", bps=m, t=t, N=n))
m, t, n = hac(post["gap"])
seg.append(dict(segment="GAP (untradable, dark period)", bps=m, t=t, N=n))
D = pd.DataFrame(seg)
D.to_csv(OUT / "b_segments.csv", index=False)
print(D.round(2).to_string(index=False))
