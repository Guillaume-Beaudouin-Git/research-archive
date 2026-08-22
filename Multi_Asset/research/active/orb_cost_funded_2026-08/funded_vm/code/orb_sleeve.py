"""Descriptifs de la sleeve ORB par colonne de coût et par fenêtre funded.

Sert à interpréter la grille : la colonne de coût n'agit sur l'étage funded QUE
par (i) le R moyen posté au segment 22:05 et (ii) le dip adverse 1.31 x risk$
tenu contre les règles entre 15:30 et 22:05 (celui-là est INDÉPENDANT du coût).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
import engine_v22 as V   # noqa: E402
E = V.E
OUT = Path(__file__).resolve().parent.parent / "out"

WINS = (("IS", "2013-10-01", "2017-12-31"), ("OOS", "2020-01-02", "2024-06-30"),
        ("ALL", "2010-01-01", "2026-12-31"))
led = pd.read_parquet(V.LEDGER)
lev = (led["entry"] / (led["entry"] - led["stop_eff"]).abs()).astype(float)
c_era = V._implied_era_cost(led, lev)
rows = []
for cost in ("era", 1.0, 1.8, 2.2, 3.0):
    if cost == "era":
        R = pd.read_parquet(E.CACHE / "orb_e7_Rera.parquet")["R"]
    else:
        R = led["r_gross"].astype(float) - float(cost) * 1e-4 * lev + 0.015
    R.index = led.index
    for win, lo, hi in WINS:
        s = R.loc[lo:hi].dropna()
        if len(s) < 10:
            continue
        x = sm.OLS(s.values, np.ones(len(s))).fit(
            cov_type="HAC", cov_kwds={"maxlags": 6})
        rows.append(dict(cost=str(cost), win=win, n=len(s), mean_R=s.mean(),
                         t_hac=float(x.tvalues[0]), sd_R=s.std(),
                         hit=(s > 0).mean(),
                         # $ posté par an à risk$ = 0.25% x 10k = $25
                         usd_per_yr=25.0 * s.mean() * len(s) /
                         ((s.index[-1] - s.index[0]).days / 365.25)))
O = pd.DataFrame(rows)
O.to_csv(OUT / "orb_sleeve_descriptives.csv", index=False)
print(O.to_string(index=False))
print("\ncoût era implicite (bps RT) par fenêtre :")
for win, lo, hi in WINS:
    c = c_era.loc[(led.index >= lo) & (led.index <= hi)] if False else \
        pd.Series(c_era.values, index=led.index).loc[lo:hi]
    if len(c):
        print(f"  {win}: n={len(c)} p25={np.percentile(c,25):.2f} "
              f"p50={np.percentile(c,50):.2f} p75={np.percentile(c,75):.2f} "
              f"moy={c.mean():.2f}")
print(f"\ndip adverse tenu contre les règles 15:30->22:05 : "
      f"1.31 x $25 = ${1.31*25:.2f} soit "
      f"{1.31*25/500*100:.1f}% du budget daily de $500 (indépendant du coût ORB)")
