"""Génération des figures du rapport (matplotlib, sans seaborn)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

import data

FIG = Path(__file__).resolve().parent / "figures"
FIG.mkdir(exist_ok=True)

C_STRAT = "#1f4e79"   # bleu institutionnel
C_BENCH = "#9aa5b1"   # gris
C_ALT = "#c0504d"     # rouge brique
C_ALT2 = "#4e8542"    # vert
C_ALT3 = "#8064a2"    # violet

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "axes.titlesize": 10, "axes.titleweight": "bold",
    "legend.frameon": False,
})


def load_eq(name: str) -> pd.Series:
    s = pd.read_csv(name, index_col=0, parse_dates=True).iloc[:, 0]
    return s


def fig01_anatomie() -> None:
    etf = data.load_etf_closes()
    tr = pd.read_csv("trades_full_sleeves.csv", parse_dates=["entry_date", "exit_date"])
    cand = tr[(tr.symbol == "SPY") & (tr.entry_date > "2023-06-01") & (tr.entry_date < "2024-12-31")
              & (tr.ret > 0.015) & (tr.holding_days.between(6, 12))].iloc[0]
    c = etf["SPY"]
    a = cand.entry_date - pd.Timedelta(days=45)
    b = cand.exit_date + pd.Timedelta(days=30)
    w = c.loc[a:b]
    lo7 = c.rolling(7).min().loc[a:b]
    hi7 = c.rolling(7).max().loc[a:b]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(w.index, w.values, color=C_STRAT, lw=1.4, label="SPY (close)")
    ax.plot(lo7.index, lo7.values, color=C_ALT, lw=0.8, ls="--", label="Plus bas 7 j (close)")
    ax.plot(hi7.index, hi7.values, color=C_ALT2, lw=0.8, ls="--", label="Plus haut 7 j (close)")
    ax.scatter([cand.entry_date], [cand.entry_px], marker="^", s=90, color=C_ALT2,
               zorder=5, label=f"Entrée @ {cand.entry_px:.2f}")
    ax.scatter([cand.exit_date], [cand.exit_px], marker="v", s=90, color=C_ALT,
               zorder=5, label=f"Sortie @ {cand.exit_px:.2f}  ({cand.ret:+.1%})")
    ax.set_title("Anatomie d'un trade Double 7 — achat du creux 7 jours, revente sur le rebond")
    ax.legend(loc="lower right", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    fig.tight_layout(); fig.savefig(FIG / "fig01_anatomie_trade.png"); plt.close(fig)


def fig02_repro() -> None:
    s = load_eq("eq_repro_sleeves.csv"); v = load_eq("eq_repro_vol.csv")
    etf = data.load_etf_closes().loc[s.index[0]:s.index[-1]]
    bh = ((etf / etf.iloc[0]) * (100_000 / 3)).sum(axis=1)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    ax.plot(s.index, s.values / 1e3, color=C_STRAT, lw=1.3, label="Double 7 — equal sleeves")
    ax.plot(v.index, v.values / 1e3, color=C_ALT3, lw=1.1, label="Double 7 — vol-sized (stop ≈3 ATR)")
    ax.plot(bh.index, bh.values / 1e3, color=C_BENCH, lw=1.1, label="Buy & hold 1/3 SPY+QQQ+GLD")
    ax.set_ylabel("Équité (k$)"); ax.legend(fontsize=8)
    ax.set_title("Réplication de la configuration vidéo — 2020 → mai 2026 (100 k$, 5 bps/side)")
    dd = s / s.cummax() - 1
    ax2.fill_between(dd.index, dd.values * 100, 0, color=C_STRAT, alpha=0.55)
    ax2.set_ylabel("DD sleeves (%)")
    fig.tight_layout(); fig.savefig(FIG / "fig02_repro_equity.png"); plt.close(fig)


def fig03_full() -> None:
    s = load_eq("eq_full_sleeves.csv"); b = load_eq("eq_full_bh.csv")
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1.2]})
    ax.semilogy(s.index, s.values / 1e3, color=C_STRAT, lw=1.3, label="Double 7 sleeves (CAGR 4.6 %)")
    ax.semilogy(b.index, b.values / 1e3, color=C_BENCH, lw=1.1, label="Buy & hold 1/3 (CAGR 13.3 %)")
    ax.set_ylabel("Équité (k$, échelle log)"); ax.legend(fontsize=8, loc="upper left")
    ax.set_title("Échantillon complet 2005 → 2026 — la stratégie est rentable mais sous-performe le B&H")
    for eqq, col in [(s, C_STRAT), (b, C_BENCH)]:
        dd = eqq / eqq.cummax() - 1
        ax2.plot(dd.index, dd.values * 100, color=col, lw=0.9)
    ax2.set_ylabel("Drawdown (%)")
    fig.tight_layout(); fig.savefig(FIG / "fig03_full_equity.png"); plt.close(fig)


def fig04_annuel() -> None:
    res = json.load(open("results_extended.json"))
    py = pd.DataFrame(res["per_year"]).T
    py.index = py.index.astype(int)
    x = np.arange(len(py))
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.bar(x - 0.2, py.strategy * 100, 0.4, color=C_STRAT, label="Double 7 sleeves")
    ax.bar(x + 0.2, py.buyhold * 100, 0.4, color=C_BENCH, label="Buy & hold 1/3")
    ax.set_xticks(x); ax.set_xticklabels(py.index, rotation=60, fontsize=7)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_ylabel("Rendement annuel (%)"); ax.legend(fontsize=8)
    ax.set_title("Rendements par année civile — pertes limitées en 2008/2022, mais upside capté partiellement")
    fig.tight_layout(); fig.savefig(FIG / "fig04_annuel.png"); plt.close(fig)


def fig05_grid() -> None:
    g = pd.read_csv("grid_results.csv")
    fig, axes = plt.subplots(1, 3, figsize=(9.5, 3.3), sharey=True)
    vmin, vmax = g.sharpe.min(), g.sharpe.max()
    for ax, ma in zip(axes, (100, 150, 200)):
        sub = g[g.ma_len == ma].pivot(index="exit_lb", columns="entry_lb", values="sharpe")
        im = ax.imshow(sub.values, cmap="RdYlGn", vmin=vmin, vmax=vmax, origin="lower",
                       extent=[4.5, 10.5, 4.5, 10.5], aspect="auto")
        ax.set_title(f"SMA {ma}")
        ax.set_xlabel("Lookback entrée (j)")
        if ma == 100:
            ax.set_ylabel("Lookback sortie (j)")
        ax.grid(False)
        if ma == 200:
            ax.add_patch(plt.Rectangle((6.5, 6.5), 1, 1, fill=False, edgecolor="black", lw=1.8))
        for (i, j), val in np.ndenumerate(sub.values):
            ax.text(sub.columns[j], sub.index[i], f"{val:.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=axes, shrink=0.85, label="Sharpe 2005-2026")
    fig.suptitle("Sensibilité aux paramètres — toute la surface est positive (cadre noir: config 7/7/200)",
                 fontsize=10, fontweight="bold")
    fig.savefig(FIG / "fig05_grid_heatmap.png", bbox_inches="tight"); plt.close(fig)


def fig06_couts() -> None:
    c = pd.read_csv("cost_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.plot(c.slippage_bps, c.sharpe, "o-", color=C_STRAT, label="Sharpe")
    ax.set_xlabel("Slippage par côté (bps)"); ax.set_ylabel("Sharpe", color=C_STRAT)
    ax2 = ax.twinx(); ax2.spines.right.set_visible(True)
    ax2.plot(c.slippage_bps, c.cagr * 100, "s--", color=C_ALT, label="CAGR")
    ax2.set_ylabel("CAGR (%)", color=C_ALT); ax2.grid(False)
    ax.set_title("Sensibilité aux coûts — edge brut ≈ 60 bps/trade, break-even ≈ 30 bps/side")
    fig.tight_layout(); fig.savefig(FIG / "fig06_couts.png"); plt.close(fig)


def fig07_dist() -> None:
    tr = pd.read_csv("trades_full_sleeves.csv").dropna(subset=["pnl"])
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.6, 3.2))
    ax.hist(tr.ret * 100, bins=60, color=C_STRAT, alpha=0.85)
    ax.axvline(0, color="black", lw=0.7)
    ax.axvline(tr.ret.min() * 100, color=C_ALT, lw=1, ls="--")
    ax.text(tr.ret.min() * 100 + 0.5, ax.get_ylim()[1] * 0.7, "pire trade\n(QQQ 2008)\n-30.2 %",
            fontsize=7, color=C_ALT)
    ax.set_xlabel("Rendement par trade (%)"); ax.set_ylabel("Nombre de trades")
    ax.set_title("Distribution des 606 trades — WR 73.8 %, queue gauche épaisse")
    ax2.hist(tr.holding_days, bins=np.arange(0, 45, 2), color=C_ALT3, alpha=0.85)
    ax2.set_xlabel("Durée de détention (jours de bourse)")
    ax2.set_title("Durées — médiane ≈ 6 j, queue jusqu'à 40 j")
    fig.tight_layout(); fig.savefig(FIG / "fig07_distribution_trades.png"); plt.close(fig)


def fig08_rolling() -> None:
    s = load_eq("eq_full_sleeves.csv")
    r = s.pct_change().dropna()
    roll = np.sqrt(252) * r.rolling(252).mean() / r.rolling(252).std()
    expo = pd.read_csv("exposure_full.csv", index_col=0, parse_dates=True).iloc[:, 0]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    ax.plot(roll.index, roll.values, color=C_STRAT, lw=1.0, label="Sharpe glissant 252 j")
    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(roll.mean(), color=C_ALT, lw=0.8, ls="--", label=f"Moyenne ({roll.mean():.2f})")
    ax2 = ax.twinx(); ax2.grid(False); ax2.spines.right.set_visible(True)
    ax2.fill_between(expo.index, expo.values * 100, 0, color=C_BENCH, alpha=0.25, label="Exposition (%)")
    ax2.set_ylabel("Exposition brute (%)"); ax2.set_ylim(0, 130)
    ax.set_ylabel("Sharpe glissant"); ax.legend(fontsize=8, loc="upper left")
    ax.set_title("Sharpe glissant 1 an et exposition — edge intermittent, en sommeil hors stress")
    fig.tight_layout(); fig.savefig(FIG / "fig08_rolling_sharpe.png"); plt.close(fig)


def fig09_cfd() -> None:
    cfd = load_eq("eq_cfd_sleeves.csv")
    s = load_eq("eq_full_sleeves.csv").loc["2008-01-01":]
    s = s / s.iloc[0] * 100
    cfd = cfd / cfd.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(8, 3.3))
    ax.plot(s.index, s.values, color=C_STRAT, lw=1.2, label="ETF: SPY/QQQ/GLD (Sharpe 0.59)")
    ax.plot(cfd.index, cfd.values, color=C_ALT, lw=1.2, label="CFD: US500/US100/XAUUSD (Sharpe 0.61)")
    ax.set_ylabel("Équité (base 100, 2008)")
    ax.legend(fontsize=8)
    ax.set_title("Validation croisée inter-sources 2008 → 2026 — même logique, autre venue, même profil")
    fig.tight_layout(); fig.savefig(FIG / "fig09_cfd.png"); plt.close(fig)


def fig10_improvements() -> None:
    base = load_eq("eq_imp_base.csv")
    vt = load_eq("eq_imp_voltarget.csv")
    ts = load_eq("eq_imp_timestop.csv")
    combo = load_eq("eq_imp_combo_final.csv")
    res = json.load(open("results_improvements.json"))
    vix = json.load(open("results_vix.json"))
    fig, (ax, axb) = plt.subplots(1, 2, figsize=(9.5, 3.5), gridspec_kw={"width_ratios": [2, 1]})
    for eq, col, lbl in [(base, C_BENCH, "Base 7/7/200"),
                         (vt, C_STRAT, "Axe 1: vol target 18 %"),
                         (ts, C_ALT2, "Axe 2: time-stop 10 j"),
                         (combo, C_ALT, "Combo: VT 12 % + TS 10")]:
        ax.semilogy(eq.index, eq.values / 1e3, color=col, lw=1.1, label=lbl)
    ax.set_ylabel("Équité (k$, log)"); ax.legend(fontsize=7)
    ax.set_title("Courbes d'équité — base vs variantes 2005-2026")
    names = ["base_7_7_200", "axe1_voltarget12", "axe2_timestop10", "combo_voltarget12_ts10_full"]
    labels = ["Base", "VT 12 %", "TS 10 j", "Combo"]
    src = {**res, **vix["variants"]}
    sharpe = [src[n]["sharpe"] for n in names]
    calmar = [src[n]["calmar"] for n in names]
    x = np.arange(4)
    axb.bar(x - 0.18, sharpe, 0.36, color=C_STRAT, label="Sharpe")
    axb.bar(x + 0.18, calmar, 0.36, color=C_ALT2, label="Calmar")
    axb.set_xticks(x); axb.set_xticklabels(labels, fontsize=8)
    axb.legend(fontsize=7); axb.set_title("Risque-ajusté")
    fig.tight_layout(); fig.savefig(FIG / "fig10_ameliorations.png"); plt.close(fig)


def fig11_vix() -> None:
    vix = json.load(open("results_vix.json"))
    b = pd.DataFrame(vix["vix_buckets"])
    b[["n", "wr", "avg_ret"]] = b[["n", "wr", "avg_ret"]].astype(float)
    x = np.arange(len(b))
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    bars = ax.bar(x, b.avg_ret * 1e4, color=C_STRAT)
    for i, (n, v) in enumerate(zip(b.n, b.avg_ret * 1e4)):
        ax.text(i, v + 4, f"n={int(n)}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(b.bucket)
    ax.set_xlabel("VIX au close d'entrée"); ax.set_ylabel("Rendement moyen par trade (bps)")
    ax.set_title("Axe 3 — l'edge par trade croît avec le régime de volatilité")
    fig.tight_layout(); fig.savefig(FIG / "fig11_vix.png"); plt.close(fig)


if __name__ == "__main__":
    for f in [fig01_anatomie, fig02_repro, fig03_full, fig04_annuel, fig05_grid,
              fig06_couts, fig07_dist, fig08_rolling, fig09_cfd, fig10_improvements,
              fig11_vix]:
        f()
        print("ok", f.__name__)
