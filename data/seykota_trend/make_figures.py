"""Generate report figures (PNG, 150 dpi) from results/ CSVs."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RES, FIG = HERE / "results", HERE / "figures"
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "white", "axes.grid": True, "grid.alpha": 0.25,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
})
C = {"capped": "#1f4e79", "literal": "#c0504d", "spx": "#7f7f7f",
     "ew": "#9bbb59", "btc": "#e8a33d"}

eq_c = pd.read_csv(RES / "equity_extended_capped.csv", index_col=0, parse_dates=True)
eq_l = pd.read_csv(RES / "equity_extended.csv", index_col=0, parse_dates=True)
tr_c = pd.read_csv(RES / "trades_extended_capped.csv", parse_dates=["entry_date", "exit_date"])

daily = HERE / "daily"
spx = pd.read_parquet(daily / "US500.parquet")["close"]
universe = ["US500", "US100", "XAUUSD", "USOIL", "BTC", "ETH"]
closes = pd.DataFrame({s: pd.read_parquet(daily / f"{s}.parquet")["close"] for s in universe}).ffill()

w0, w1 = eq_c.index[0], eq_c.index[-1]
spx_w = spx[(spx.index >= w0) & (spx.index <= w1)]
spx_eq = spx_w / spx_w.iloc[0] * 100_000
cl_w = closes[(closes.index >= w0) & (closes.index <= w1)]
avail = cl_w.notna()
wts = avail.div(avail.sum(axis=1), axis=0).shift(1)
ew_eq = (1 + (cl_w.pct_change() * wts).sum(axis=1, min_count=1).fillna(0)).cumprod() * 100_000

# ---------------------------------------------------------------- fig 1
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(eq_c.index, eq_c["equity"], color=C["capped"], lw=1.6,
        label="Stratégie — cash account (gross ≤ 100%)")
ax.plot(eq_l.index, eq_l["equity"], color=C["literal"], lw=1.2, alpha=0.85,
        label="Stratégie — lecture littérale (levier)")
ax.plot(spx_eq.index, spx_eq, color=C["spx"], lw=1.2, label="US500 buy & hold")
ax.plot(ew_eq.index, ew_eq, color=C["ew"], lw=1.2, label="Panier EW-6 buy & hold")
ax.axvline(pd.Timestamp("2020-06-01"), color="k", ls="--", lw=0.8, alpha=0.6)
ax.text(pd.Timestamp("2020-07-15"), 130_000, "fenêtre vidéo →", fontsize=8, alpha=0.7)
ax.set_yscale("log")
ax.set_title("Courbes de capital, échelle log — univers vidéo (6 actifs), 2014–2026")
ax.set_ylabel("Equity ($, départ 100k)")
ax.legend(frameon=False, fontsize=8.5, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "fig1_equity.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- fig 2
fig, ax = plt.subplots(figsize=(10, 3.6))
for s, col, lab in [(eq_c["equity"], C["capped"], "Stratégie (cash account)"),
                    (spx_eq, C["spx"], "US500 B&H"), (ew_eq, C["ew"], "EW-6 B&H")]:
    dd = s / s.cummax() - 1
    ax.plot(dd.index, dd * 100, color=col, lw=1.1, label=lab)
ax.set_title("Drawdown (%)")
ax.legend(frameon=False, fontsize=8.5, loc="lower left")
fig.tight_layout(); fig.savefig(FIG / "fig2_drawdown.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- fig 3
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
pa = tr_c.groupby("symbol").pnl_net.sum().sort_values()
axes[0].barh(pa.index, pa / 1000, color=C["capped"])
axes[0].set_title("PnL net par actif (k$) — 2014–2026, cash account")
bydir = tr_c.groupby(["symbol", "direction"]).pnl_net.sum().unstack(fill_value=0) / 1000
bydir.columns = ["Short", "Long"] if -1 in tr_c.direction.values else bydir.columns
order = pa.index
x = np.arange(len(order))
axes[1].bar(x - 0.2, bydir.loc[order, "Long"], 0.38, color=C["capped"], label="Long")
axes[1].bar(x + 0.2, bydir.loc[order, "Short"], 0.38, color=C["literal"], label="Short")
axes[1].set_xticks(x, order, rotation=30)
axes[1].axhline(0, color="k", lw=0.7)
axes[1].set_title("PnL net par direction (k$)")
axes[1].legend(frameon=False, fontsize=8.5)
fig.tight_layout(); fig.savefig(FIG / "fig3_attribution.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- fig 4
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
axes[0].hist(tr_c.r_multiple, bins=60, color=C["capped"], alpha=0.9)
axes[0].axvline(0, color="k", lw=0.8)
axes[0].set_title(f"Distribution des trades en R (n={len(tr_c)})")
axes[0].set_xlabel("R-multiple (PnL / risque initial)")
wr = (tr_c.pnl_net > 0).mean()
axes[0].text(0.97, 0.95, f"Win rate: {wr:.0%}\nE[R]: {tr_c.r_multiple.mean():.2f}",
             transform=axes[0].transAxes, ha="right", va="top", fontsize=9,
             bbox=dict(fc="white", ec="0.8"))
cols = np.where(tr_c.pnl_net > 0, C["capped"], C["literal"])
axes[1].scatter(tr_c.holding_days, tr_c.r_multiple, s=8, c=cols, alpha=0.55)
axes[1].axhline(0, color="k", lw=0.7)
axes[1].set_title("R-multiple vs durée de détention")
axes[1].set_xlabel("Jours"); axes[1].set_ylabel("R")
fig.tight_layout(); fig.savefig(FIG / "fig4_trades.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- fig 5
m = eq_c["equity"].resample("ME").last().pct_change()
pv = m.to_frame("r")
pv["y"], pv["m"] = pv.index.year, pv.index.month
piv = pv.pivot_table(index="y", columns="m", values="r")
fig, ax = plt.subplots(figsize=(10, 4.2))
im = ax.imshow(piv.values * 100, cmap="RdYlGn", vmin=-15, vmax=15, aspect="auto")
ax.set_xticks(range(12), ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"])
ax.set_yticks(range(len(piv)), piv.index)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j] * 100
        if np.isfinite(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5)
ax.set_title("Rendements mensuels (%) — cash account, 2014–2026")
ax.grid(False)
fig.colorbar(im, ax=ax, shrink=0.8, label="%")
fig.tight_layout(); fig.savefig(FIG / "fig5_monthly.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- fig 6
g1 = pd.read_csv(RES / "sens_ema_breakout.csv").pivot(index="ema", columns="breakout", values="sharpe")
g2 = pd.read_csv(RES / "sens_stop_pyramid.csv").pivot(index="atr_stop_mult", columns="pyramid_step", values="sharpe")
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
for ax, g, t, (xl, yl) in [
    (axes[0], g1, "Sharpe — EMA × fenêtre breakout", ("Breakout (jours)", "EMA (jours)")),
    (axes[1], g2, "Sharpe — multiple ATR stop × pas pyramide", ("Pas pyramide (×ATR)", "Stop (×ATR)")),
]:
    im = ax.imshow(g.values, cmap="viridis", aspect="auto")
    ax.set_xticks(range(g.shape[1]), g.columns)
    ax.set_yticks(range(g.shape[0]), g.index)
    ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(t); ax.grid(False)
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            ax.text(j, i, f"{g.values[i, j]:.2f}", ha="center", va="center",
                    color="white", fontsize=8)
    sv = "(100, 20)" if "EMA" in t else "(3.0, 0.5)"
fig.suptitle("Sensibilité aux paramètres — cadre ▢ = paramètres de la vidéo", y=1.02, fontsize=10)
# mark video params
axes[0].add_patch(plt.Rectangle((0.5, 0.5), 1, 1, fill=False, ec="red", lw=2))
axes[1].add_patch(plt.Rectangle((0.5, 1.5), 1, 1, fill=False, ec="red", lw=2))
fig.tight_layout(); fig.savefig(FIG / "fig6_sensitivity.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------- fig 7
r = eq_c["equity"].pct_change()
roll_sharpe = r.rolling(365).mean() / r.rolling(365).std() * np.sqrt(365)
fig, axes = plt.subplots(2, 1, figsize=(10, 5.4), sharex=True)
axes[0].plot(roll_sharpe.index, roll_sharpe, color=C["capped"], lw=1.2)
axes[0].axhline(0, color="k", lw=0.7)
axes[0].set_title("Sharpe glissant 1 an — cash account")
axes[1].plot(eq_c.index, eq_c["gross_exposure"] * 100, color=C["btc"], lw=0.9)
axes[1].set_title("Exposition brute (% de l'equity)")
axes[1].set_ylabel("%")
fig.tight_layout(); fig.savefig(FIG / "fig7_rolling.png", dpi=150); plt.close(fig)

print("figures:", sorted(p.name for p in FIG.glob("*.png")))
