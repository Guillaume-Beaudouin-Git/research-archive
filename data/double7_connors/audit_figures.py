"""Figures de l'audit (matplotlib)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

FIG = Path(__file__).resolve().parent / "figures"
FIG.mkdir(exist_ok=True)

C_STRAT = "#1f4e79"; C_BENCH = "#9aa5b1"; C_ALT = "#c0504d"
C_ALT2 = "#4e8542"; C_ALT3 = "#8064a2"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
})


def fig_a1_mc_dd():
    mdd = np.load("mc_daily_maxdd.npy")
    mdd_tr = np.load("mc_trades_maxdd.npy")
    obs = json.load(open("audit_montecarlo.json"))["observed"]["maxdd"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.4))
    ax.hist(mdd * 100, bins=60, color=C_STRAT, alpha=0.85)
    ax.axvline(obs * 100, color=C_ALT, lw=1.6, label=f"Observé {obs:.1%}")
    ax.axvline(np.percentile(mdd, 5) * 100, color="black", lw=1, ls="--",
               label=f"p5 {np.percentile(mdd,5):.1%}")
    ax.axvline(np.percentile(mdd, 1) * 100, color=C_ALT2, lw=1, ls=":",
               label=f"p1 {np.percentile(mdd,1):.1%}")
    ax.set_xlabel("Max drawdown simulé (%)"); ax.set_ylabel("Fréquence")
    ax.set_title("MC-A — bootstrap des rendements quotidiens\n(portefeuille 3 sleeves, 5000 chemins)")
    ax.legend(fontsize=7)
    ax2.hist(mdd_tr * 100, bins=60, color=C_ALT3, alpha=0.85)
    ax2.axvline(np.percentile(mdd_tr, 50) * 100, color=C_ALT, lw=1.4,
                label=f"médiane {np.percentile(mdd_tr,50):.1%}")
    ax2.set_xlabel("Max drawdown simulé (%)")
    ax2.set_title("MC-B — réordonnancement des trades\n(compte unique, borne conservatrice)")
    ax2.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig_a1_mc_drawdown.png"); plt.close(fig)


def fig_a2_mc_dist():
    cagr = np.load("mc_daily_cagr.npy"); sh = np.load("mc_daily_sharpe.npy")
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.2, 3.3))
    ax.hist(cagr * 100, bins=60, color=C_STRAT, alpha=0.85)
    ax.axvline(0, color=C_ALT, lw=1.4, label="seuil 0 %")
    ax.axvline(np.percentile(cagr, 5) * 100, color="black", ls="--", lw=1,
               label=f"p5 {np.percentile(cagr,5):+.1%}")
    ax.set_xlabel("CAGR simulé (%)"); ax.set_ylabel("Fréquence")
    ax.set_title(f"Distribution du CAGR — P(CAGR<0) = {np.mean(cagr<0):.1%}")
    ax.legend(fontsize=7)
    ax2.hist(sh, bins=60, color=C_ALT2, alpha=0.85)
    ax2.axvline(0, color=C_ALT, lw=1.4)
    ax2.axvline(np.percentile(sh, 5), color="black", ls="--", lw=1,
                label=f"p5 {np.percentile(sh,5):.2f}")
    ax2.set_xlabel("Sharpe simulé"); ax2.set_title(f"Distribution du Sharpe — P(<0) = {np.mean(sh<0):.1%}")
    ax2.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(FIG / "fig_a2_mc_distrib.png"); plt.close(fig)


def fig_a3_walkforward():
    wf = json.load(open("audit_walkforward.json"))
    segs = pd.DataFrame(wf["rolling_3is_1oos"]["segments"])
    eq = pd.read_csv("wf_equity_rolling_3is_1oos.csv", index_col=0, parse_dates=True).iloc[:, 0]
    base = pd.read_csv("eq_full_sleeves.csv", index_col=0, parse_dates=True).iloc[:, 0]
    base = base.loc[eq.index[0]:]
    base = base / base.iloc[0]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(9.4, 3.5), gridspec_kw={"width_ratios": [1, 1.3]})
    ax.scatter(segs.is_sharpe, segs.oos_sharpe, color=C_STRAT, s=40, zorder=3)
    lim = [-1.6, 3.1]
    ax.plot(lim, lim, color=C_BENCH, lw=0.8, ls="--")
    ax.axhline(0, color=C_ALT, lw=0.8)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Sharpe In-Sample (config sélectionnée)")
    ax.set_ylabel("Sharpe Out-of-Sample")
    ax.set_title(f"WF glissant 3a/1a — {int((segs.oos_sharpe>0).mean()*100)}% des OOS positifs")
    ax2.plot(eq.index, eq.values, color=C_STRAT, lw=1.3, label="Walk-forward OOS (params ré-optimisés)")
    ax2.plot(base.index, base.values, color=C_BENCH, lw=1.1, ls="--", label="7/7/200 figé")
    ax2.set_ylabel("Équité OOS (base 1)"); ax2.legend(fontsize=7.5)
    ax2.set_title("Équité walk-forward concaténée")
    fig.tight_layout(); fig.savefig(FIG / "fig_a3_walkforward.png"); plt.close(fig)


def fig_a4_underwater():
    uw = pd.read_csv("underwater.csv", index_col=0, parse_dates=True).iloc[:, 0]
    fig, ax = plt.subplots(figsize=(8.4, 3.2))
    ax.fill_between(uw.index, uw.values * 100, 0, color=C_STRAT, alpha=0.6)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Courbe underwater 2005-2026 — DD modérés mais épisode 2021-2024 long (924 j sous l'eau)")
    ann = json.load(open("audit_stress.json"))["top_drawdowns"][:3]
    for d in ann:
        t = pd.Timestamp(d["trough"])
        ax.annotate(f"{d['depth']:.1%}", (t, d["depth"] * 100),
                    textcoords="offset points", xytext=(0, -12), fontsize=7,
                    ha="center", color=C_ALT)
    fig.tight_layout(); fig.savefig(FIG / "fig_a4_underwater.png"); plt.close(fig)


def fig_a5_crisis():
    cw = pd.DataFrame(json.load(open("audit_stress.json"))["crisis"])
    x = np.arange(len(cw))
    fig, ax = plt.subplots(figsize=(8.8, 3.6))
    ax.bar(x - 0.2, cw.strat_ret * 100, 0.4, color=C_STRAT, label="Double 7")
    ax.bar(x + 0.2, cw.bh_ret * 100, 0.4, color=C_BENCH, label="Buy & hold 1/3")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels(cw.crise, rotation=35, ha="right", fontsize=7)
    ax.set_ylabel("Rendement sur la fenêtre (%)"); ax.legend(fontsize=8)
    ax.set_title("Stress tests — la stratégie amortit les krachs (filtre SMA200), protection +10 à +20 pts")
    fig.tight_layout(); fig.savefig(FIG / "fig_a5_crisis.png"); plt.close(fig)


def fig_a6_random():
    rnd = np.load("dm_random_sharpes.npy")
    dm = json.load(open("audit_datamining.json"))
    obs = dm["random_entry"]["obs_sharpe"]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.hist(rnd, bins=45, color=C_BENCH, alpha=0.9, label="Entrées aléatoires (même exposition)")
    ax.axvline(obs, color=C_ALT, lw=1.8, label=f"Double 7 observé ({obs:.2f})")
    ax.axvline(np.percentile(rnd, 95), color="black", ls="--", lw=1,
               label=f"p95 aléatoire ({np.percentile(rnd,95):.2f})")
    ax.set_xlabel("Sharpe annualisé"); ax.set_ylabel("Fréquence")
    ax.set_title(f"Test de permutation — le timing '7-day low' bat l'aléatoire (p = {dm['random_entry']['pvalue']:.3f})")
    ax.legend(fontsize=7.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_a6_random_entry.png"); plt.close(fig)


def fig_a7_deflated():
    dm = json.load(open("audit_datamining.json"))
    R = pd.read_csv("dm_config_returns.csv", index_col=0, parse_dates=True)
    sr = (R.mean() / R.std(ddof=1)) * np.sqrt(252)
    d = dm["deflated_sharpe"]
    fig, ax = plt.subplots(figsize=(7.6, 3.3))
    ax.hist(sr.values, bins=22, color=C_STRAT, alpha=0.85, label="Sharpe des 108 configs")
    ax.axvline(d["sr0_ann"], color=C_ALT, lw=1.8,
               label=f"SR0 — max attendu sous H0 ({d['sr0_ann']:.2f})")
    ax.axvline(d["sharpe_ann"], color=C_ALT2, lw=1.8,
               label=f"Config 7/7/200 ({d['sharpe_ann']:.2f})")
    ax.set_xlabel("Sharpe annualisé"); ax.set_ylabel("Nb de configs")
    ax.set_title(f"Deflated Sharpe — P(edge réel) = {d['deflated_sharpe_prob']:.1%} malgré 108 essais")
    ax.legend(fontsize=7.5)
    fig.tight_layout(); fig.savefig(FIG / "fig_a7_deflated.png"); plt.close(fig)


if __name__ == "__main__":
    for f in [fig_a1_mc_dd, fig_a2_mc_dist, fig_a3_walkforward, fig_a4_underwater,
              fig_a5_crisis, fig_a6_random, fig_a7_deflated]:
        f(); print("ok", f.__name__)
