"""Clarify silver (sub-periods, winsor sensitivity) and validate the WTI overnight edge."""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S
spec = importlib.util.spec_from_file_location("iz", HERE.parent / "gold_research" / "intraday.py")
iz = importlib.util.module_from_spec(spec); spec.loader.exec_module(iz)
ANN = 252.0
ON = [23, 0, 1, 2, 3, 4, 5, 6]


def vt(w):
    rv = w.rolling(20, min_periods=20).std().shift(1)
    return (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def wins(s, q=0.005):
    return s.clip(s.quantile(q), s.quantile(1 - q))


def shp(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if len(x) > 5 and x.std() > 0 else np.nan


def strat(piv, hours, winsor=True, start=None):
    w = iz.win_ret(piv, hours)
    if winsor:
        w = wins(w)
    return (vt(w) * w).dropna()


print("===== SILVER sub-period & winsor sensitivity (overnight 23-07, swap-free) =====")
ag = iz.hourly_pivot("XAGUSD", anchor_hour=13)
for lo in ["2003", "2007", "2014", "2018"]:
    s_w = strat(ag.loc[lo:], ON, winsor=True)
    s_nw = strat(ag.loc[lo:], ON, winsor=False)
    print(f"  {lo}+ : winsor Sharpe {shp(s_w):+.2f} | no-winsor {shp(s_nw):+.2f} | n={len(s_w)}")
sg = strat(ag, ON, winsor=True)
yr = sg.groupby(sg.index.year).apply(lambda s: shp(s) if len(s) > 40 else np.nan).dropna()
print("  per-year (winsor):", " ".join(f"{y}:{v:+.1f}" for y, v in yr.items()))

print("\n===== WTI overnight 23-07 — validation =====")
oil = iz.hourly_pivot("USOIL", anchor_hour=13)
g = strat(oil, ON, winsor=True); r = g.to_numpy()
eq = (1 + g).cumprod(); mdd, _ = S.max_drawdown(eq.to_numpy())
print(f"  gross Sharpe {shp(r):.2f} | HAC t {S.hac_tstat(r)[1]:.2f} | DSR {S.deflated_sharpe_ratio(r,25,periods_per_year=ANN)['dsr']:.2f} "
      f"| maxDD {mdd:.1%} | skew {pd.Series(r).skew():+.2f}")
yro = g.groupby(g.index.year).apply(lambda s: shp(s) if len(s) > 40 else np.nan).dropna()
print("  per-year:", " ".join(f"{y}:{v:+.1f}" for y, v in yro.items()), f"({int((yro>0).sum())}/{len(yro)} +)")
# neighbourhood
print("  neighbourhood (gross Sharpe):")
for start in [22, 23, 0]:
    row = [shp(strat(oil, [(start + i) % 24 for i in range(L)], winsor=True)) for L in [6, 8, 10]]
    tag = " (start22=holds across rollover, pays swap)" if start == 22 else ""
    print(f"    start {start:02d}: " + " ".join(f"{v:+.2f}" for v in row) + tag)
# beta vs WTI daily
od = data.load_h1("USOIL")["close"].groupby(lambda x: x.normalize()).last().pct_change()
xy = pd.concat([g.rename("s"), od.reindex(g.index).rename("m")], axis=1).dropna()
ols = sm.OLS(xy["s"].to_numpy(), sm.add_constant(xy["m"].to_numpy())).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
print(f"  beta vs WTI {ols.params[1]:+.3f} | R^2 {ols.rsquared:.3f} | alpha t {ols.tvalues[0]:+.2f}")
print("  net Sharpe by RT spread:", {sp: round(shp((vt(wins(iz.win_ret(oil, ON))) * wins(iz.win_ret(oil, ON)) - vt(wins(iz.win_ret(oil, ON))).abs() * sp * 1e-4).dropna().to_numpy()), 2) for sp in [2, 3, 4, 5, 6]})
