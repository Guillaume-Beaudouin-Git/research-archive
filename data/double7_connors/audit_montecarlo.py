"""Audit 2/4 — Monte Carlo.

Deux familles complémentaires :

A) Bootstrap stationnaire des rendements QUOTIDIENS du portefeuille
   (blocs géométriques, longueur moyenne 20 j) → distribution de Sharpe,
   CAGR, MaxDD, richesse terminale, sur des chemins de même longueur.
   Préserve l'autocorrélation et la non-normalité (kurtosis ~8).

B) Rééchantillonnage de la SÉQUENCE DE TRADES (avec remise) sur un compte
   unique → distribution de MaxDD et "risk of ruin" (proba de toucher des
   seuils de perte). Réordonner les trades brise la chance d'enchaînement
   et révèle le DD que la stratégie aurait PU produire.

C) Sensibilité du DD au démarrage (overlap windows) — déjà couvert par A.
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)
TD = 252


def stationary_bootstrap_idx(n, mean_block, rng):
    """Indices d'un chemin bootstrap stationnaire (Politis-Romano)."""
    p = 1.0 / mean_block
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(n)
    for t in range(1, n):
        if rng.random() < p:
            idx[t] = rng.integers(n)
        else:
            idx[t] = (idx[t - 1] + 1) % n
    return idx


def mc_daily(returns: pd.Series, n_paths=5000, mean_block=20):
    r = returns.values
    n = len(r)
    yrs = n / TD
    sh = np.empty(n_paths); cagr = np.empty(n_paths)
    mdd = np.empty(n_paths); term = np.empty(n_paths)
    for k in range(n_paths):
        idx = stationary_bootstrap_idx(n, mean_block, RNG)
        x = r[idx]
        eq = np.cumprod(1 + x)
        sd = x.std(ddof=1)
        sh[k] = np.sqrt(TD) * x.mean() / sd if sd > 0 else np.nan
        cagr[k] = eq[-1] ** (1 / yrs) - 1
        mdd[k] = (eq / np.maximum.accumulate(eq) - 1).min()
        term[k] = eq[-1]
    def q(a):
        return {p: float(np.nanpercentile(a, p)) for p in (1, 5, 25, 50, 75, 95, 99)}
    return dict(sharpe=q(sh), cagr=q(cagr), maxdd=q(mdd), terminal_mult=q(term),
                prob_sharpe_neg=float(np.mean(sh < 0)),
                prob_cagr_neg=float(np.mean(cagr < 0)),
                prob_mdd_worse_25=float(np.mean(mdd < -0.25)),
                prob_mdd_worse_30=float(np.mean(mdd < -0.30)),
                arrays=dict(maxdd=mdd.tolist(), cagr=cagr.tolist(), sharpe=sh.tolist()))


def mc_trades(trade_rets: np.ndarray, n_paths=10000):
    """Compte unique: on enchaîne n trades tirés avec remise, ~même nb/an.
    Donne une distribution de MaxDD sur la courbe de trades (proxy de risque
    de séquence) et la proba de ruine à divers seuils.
    """
    n = len(trade_rets)
    mdd = np.empty(n_paths); term = np.empty(n_paths)
    ruin20 = ruin35 = ruin50 = 0
    for k in range(n_paths):
        x = RNG.choice(trade_rets, size=n, replace=True)
        # courbe de capital trade-par-trade, fraction fixe (proxy 1 sleeve)
        eq = np.cumprod(1 + x)
        dd = eq / np.maximum.accumulate(eq) - 1
        m = dd.min()
        mdd[k] = m; term[k] = eq[-1]
        ruin20 += m < -0.20; ruin35 += m < -0.35; ruin50 += m < -0.50
    def q(a):
        return {p: float(np.percentile(a, p)) for p in (1, 5, 50, 95, 99)}
    return dict(maxdd=q(mdd), terminal=q(term),
                prob_dd_20=ruin20 / n_paths, prob_dd_35=ruin35 / n_paths,
                prob_dd_50=ruin50 / n_paths,
                arrays=dict(maxdd=mdd.tolist()))


def main():
    eq = pd.read_csv("eq_full_sleeves.csv", index_col=0, parse_dates=True).iloc[:, 0]
    rets = eq.pct_change().dropna()
    tr = pd.read_csv("trades_full_sleeves.csv").dropna(subset=["pnl"])
    trade_rets = tr["ret"].values

    print("MC-A: bootstrap stationnaire des rendements quotidiens (5000 chemins)...")
    A = mc_daily(rets, n_paths=5000)
    print("  Sharpe  p5/p50/p95 :", round(A["sharpe"][5], 2), round(A["sharpe"][50], 2), round(A["sharpe"][95], 2))
    print("  CAGR    p5/p50/p95 :", f"{A['cagr'][5]:+.1%}", f"{A['cagr'][50]:+.1%}", f"{A['cagr'][95]:+.1%}")
    print("  MaxDD   p5/p50/p95 :", f"{A['maxdd'][5]:.1%}", f"{A['maxdd'][50]:.1%}", f"{A['maxdd'][95]:.1%}")
    print("  MaxDD   p99 (pire) :", f"{A['maxdd'][1]:.1%}")
    print("  P(CAGR<0):", f"{A['prob_cagr_neg']:.1%}", "| P(MaxDD<-25%):", f"{A['prob_mdd_worse_25']:.1%}",
          "| P(MaxDD<-30%):", f"{A['prob_mdd_worse_30']:.1%}")

    print("\nMC-B: rééchantillonnage de la séquence de trades (10000 chemins)...")
    B = mc_trades(trade_rets, n_paths=10000)
    print("  MaxDD (trade-curve) p50/p95/p99 :", f"{B['maxdd'][50]:.1%}", f"{B['maxdd'][95]:.1%}", f"{B['maxdd'][99]:.1%}")
    print("  P(DD>20%):", f"{B['prob_dd_20']:.1%}", "| P(DD>35%):", f"{B['prob_dd_35']:.1%}",
          "| P(DD>50%):", f"{B['prob_dd_50']:.1%}")

    # observé pour comparaison
    obs_mdd = float((eq / eq.cummax() - 1).min())
    obs_sh = float(np.sqrt(TD) * rets.mean() / rets.std(ddof=1))
    pctile_mdd = float((np.array(A["maxdd"]["50"] if False else 0) > 0))  # placeholder
    mdd_arr = np.array(A["arrays"]["maxdd"])
    print(f"\nObservé: Sharpe={obs_sh:.2f}, MaxDD={obs_mdd:.1%} "
          f"(percentile dans MC-A: {float((mdd_arr < obs_mdd).mean()):.0%})")

    out = {"mc_daily": {k: v for k, v in A.items() if k != "arrays"},
           "mc_trades": {k: v for k, v in B.items() if k != "arrays"},
           "observed": {"sharpe": obs_sh, "maxdd": obs_mdd,
                        "maxdd_percentile_in_mc": float((mdd_arr < obs_mdd).mean())}}
    json.dump(out, open("audit_montecarlo.json", "w"), indent=1)
    np.save("mc_daily_maxdd.npy", np.array(A["arrays"]["maxdd"]))
    np.save("mc_daily_cagr.npy", np.array(A["arrays"]["cagr"]))
    np.save("mc_daily_sharpe.npy", np.array(A["arrays"]["sharpe"]))
    np.save("mc_trades_maxdd.npy", np.array(B["arrays"]["maxdd"]))
    print("saved audit_montecarlo.json (+ .npy)")


if __name__ == "__main__":
    main()
