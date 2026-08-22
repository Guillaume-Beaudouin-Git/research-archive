"""Consolidated tear-sheets + figures for silver (recent regime) and WTI overnight edges."""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import numpy as np, pandas as pd, statsmodels.api as sm
from scipy import stats as sst

HERE = Path(__file__).resolve().parent; RES = HERE / "results"
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S
spec = importlib.util.spec_from_file_location("iz", HERE.parent / "gold_research" / "intraday.py")
iz = importlib.util.module_from_spec(spec); spec.loader.exec_module(iz)
ANN = 252.0; ON = [23, 0, 1, 2, 3, 4, 5, 6]


def vt(w):
    rv = w.rolling(20, min_periods=20).std().shift(1)
    return (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def wins(s):
    return s.clip(s.quantile(0.005), s.quantile(0.995))


def shp(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def mdd(r):
    eq = np.cumprod(1 + np.asarray(r)); return float((eq / np.maximum.accumulate(eq) - 1).min())


def analyse(sym, lo, title, spreads=(2, 3, 5, 7)):
    piv = iz.hourly_pivot(sym, anchor_hour=13).loc[lo:]
    w = wins(iz.win_ret(piv, ON)); sc = vt(w)
    g = (sc * w).dropna(); r = g.to_numpy()
    eq = (1 + g).cumprod()
    print(f"\n===== {title} ({lo}+) =====  n={len(r)}")
    print(f"  gross Sharpe {shp(r):.2f} | Sortino {S.sortino_ratio(r,ANN):.2f} | HAC t {S.hac_tstat(r)[1]:.2f} "
          f"| DSR {S.deflated_sharpe_ratio(r,25,periods_per_year=ANN)['dsr']:.2f} | maxDD {mdd(r):.1%} "
          f"| annret {r.mean()*ANN:+.1%} | skew {sst.skew(r):+.2f} | gross_bps {r.mean()*1e4:.2f}")
    net = {sp: round(shp((sc * w - sc.abs() * sp * 1e-4).dropna().to_numpy()), 2) for sp in spreads}
    print(f"  net Sharpe by RT spread: {net}  (break-even ~{r.mean()*1e4:.1f} bp)")
    sd = data.load_h1(sym)["close"].groupby(lambda x: x.normalize()).last().pct_change()
    xy = pd.concat([g.rename("s"), sd.reindex(g.index).rename("m")], axis=1).dropna()
    ols = sm.OLS(xy["s"].to_numpy(), sm.add_constant(xy["m"].to_numpy())).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    print(f"  beta {ols.params[1]:+.3f} | R^2 {ols.rsquared:.3f} | alpha t {ols.tvalues[0]:+.2f}")
    # MC
    n = len(r); rng = np.random.default_rng(7); B = 1500; p = 0.1; sh = np.empty(B)
    for b in range(B):
        idx = np.empty(n, int); i = rng.integers(0, n)
        for k in range(n):
            idx[k] = i; i = rng.integers(0, n) if rng.random() < p else (i + 1) % n
        sh[b] = shp(r[idx])
    print(f"  MC gross: Sharpe median {np.median(sh):.2f} [5th {np.percentile(sh,5):.2f}] | P(SR>1) {np.mean(sh>1):.0%}")
    yr = g.groupby(g.index.year).apply(lambda s: shp(s) if len(s) > 40 else np.nan).dropna()
    return g, eq, yr, sh


fig, ax = plt.subplots(2, 2, figsize=(13, 8))
for col, (sym, lo, title) in enumerate([("XAGUSD", "2014", "SILVER overnight (recent regime)"),
                                        ("USOIL", "2013", "WTI overnight")]):
    g, eq, yr, sh = analyse(sym, lo, title)
    _, dd = S.max_drawdown(eq.to_numpy())
    ax[0, col].plot(eq.index, eq.values, color="seagreen", lw=1.2); ax[0, col].set_yscale("log")
    ax[0, col].set_title(f"{title} — gross equity"); ax[0, col].grid(alpha=0.25)
    ax[1, col].bar(yr.index, yr.values, color=["seagreen" if v > 0 else "indianred" for v in yr.values])
    ax[1, col].axhline(0, color="black", lw=0.8); ax[1, col].set_title(f"per-year gross Sharpe ({int((yr>0).sum())}/{len(yr)} +)"); ax[1, col].grid(alpha=0.25, axis="y")
fig.tight_layout(); fig.savefig(RES / "fig_silver_wti.png", dpi=120); plt.close(fig)
print("\nsaved fig_silver_wti.png")
