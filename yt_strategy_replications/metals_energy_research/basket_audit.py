"""
Audit the overnight-drift FAMILY (gold, silver, WTI, soybean): are they 4 diversified
edges or one common factor? Cross-correlation, equal-risk basket, PCA.
Run: python basket_audit.py
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent; RES = HERE / "results"
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


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def overnight(sym, hours, anchor, lo=None, shift_to_morning=True):
    piv = iz.hourly_pivot(sym, anchor_hour=anchor)
    if lo:
        piv = piv.loc[lo:]
    w = wins(iz.win_ret(piv, hours))
    g = (vt(w) * w).dropna()
    if shift_to_morning and anchor == 13:   # label by the morning the window exits
        g.index = g.index + pd.Timedelta(days=1)
    return g


series = {
    "GOLD": overnight("XAUUSD", [23, 0, 1, 2, 3, 4, 5, 6], 13),
    "SILVER": overnight("XAGUSD", [23, 0, 1, 2, 3, 4, 5, 6], 13, lo="2014"),
    "WTI": overnight("USOIL", [23, 0, 1, 2, 3, 4, 5, 6], 13),
    "SOYBEAN": overnight("SOYBEAN", [1, 2, 3, 4, 5, 6], 0, shift_to_morning=False),
}
df = pd.DataFrame(series).dropna()
print(f"common dates: {len(df)}  {df.index.min().date()}->{df.index.max().date()}")

corr = df.corr()
print("\n=== cross-correlation of the 4 overnight strategies (gross daily) ===")
print(corr.round(2).to_string())
off = corr.where(~np.eye(4, dtype=bool))
print(f"average pairwise correlation: {np.nanmean(off.to_numpy()):.2f}")

print("\n=== single vs equal-risk basket ===")
for k in df:
    print(f"  {k:8s} Sharpe {sharpe(df[k].to_numpy()):.2f}")
w = 1.0 / df.std()
basket = (df * w).sum(axis=1) / w.sum()
print(f"  ---\n  AVG single Sharpe : {np.mean([sharpe(df[k].to_numpy()) for k in df]):.2f}")
print(f"  BEST single Sharpe: {max(sharpe(df[k].to_numpy()) for k in df):.2f}")
print(f"  BASKET Sharpe     : {sharpe(basket.to_numpy()):.2f}  (maxDD {S.max_drawdown((1+basket).cumprod().to_numpy())[0]:.1%})")

print("\n=== common-factor (PCA on standardised returns) ===")
z = (df - df.mean()) / df.std()
ev = np.sort(np.linalg.eigvalsh(z.cov().to_numpy()))[::-1]
print(f"  variance explained by PC1: {ev[0]/ev.sum():.0%}  (4 independent series -> ~25%)")
print(f"  eigenvalue spectrum (%): {[round(e/ev.sum()*100) for e in ev]}")
for k in df:
    others = df.drop(columns=[k]).mean(axis=1)
    print(f"  {k:8s} corr to mean-of-others: {df[k].corr(others):+.2f}")

# figure: basket equity vs singles + corr heatmap
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
for k in df:
    ax[0].plot(df.index, (1 + df[k]).cumprod().values, lw=0.9, alpha=0.7, label=k)
ax[0].plot(basket.index, (1 + basket).cumprod().values, lw=2.0, color="black", label="EQ-RISK BASKET")
ax[0].set_yscale("log"); ax[0].set_title("Overnight-drift family — gross equity (common window)"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.25)
im = ax[1].imshow(corr.to_numpy(), cmap="RdYlGn_r", vmin=-1, vmax=1)
ax[1].set_xticks(range(4)); ax[1].set_xticklabels(df.columns, fontsize=9); ax[1].set_yticks(range(4)); ax[1].set_yticklabels(df.columns, fontsize=9)
for i in range(4):
    for j in range(4):
        ax[1].text(j, i, f"{corr.to_numpy()[i,j]:.2f}", ha="center", va="center", fontsize=9)
ax[1].set_title("cross-correlation"); fig.colorbar(im, ax=ax[1])
fig.tight_layout(); fig.savefig(RES / "fig_basket_audit.png", dpi=120); plt.close(fig)
print("\nsaved fig_basket_audit.png")
