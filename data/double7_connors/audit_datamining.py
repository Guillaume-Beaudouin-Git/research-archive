"""Audit 3/4 — Risque de surapprentissage / data-mining.

1) Deflated Sharpe Ratio (Bailey & López de Prado, 2014) : le Sharpe observé
   reste-t-il significatif APRÈS correction pour (a) le nombre d'essais (108
   configs), (b) la non-normalité (skew, kurtosis), (c) la longueur d'échantillon ?

2) Probability of Backtest Overfitting (PBO) via CSCV (combinatorially
   symmetric cross-validation) : sur la matrice T×108 des rendements,
   la config gagnante IS reste-t-elle au-dessus de la médiane OOS ?

3) Test de permutation par entrées aléatoires : à exposition égale (même
   nombre de trades, mêmes durées, uniquement quand close>SMA200), le timing
   "plus bas 7 jours" bat-il un timing aléatoire ?
"""

from __future__ import annotations

import json
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

import data

TD = 252
SLIP = 5e-4
GRID = [(e, x, m) for m in (100, 150, 200) for e in range(5, 11) for x in range(5, 11)]
RNG = np.random.default_rng(11)


def sleeve_daily_returns(c: np.ndarray, ent: np.ndarray, exi: np.ndarray, sleeve0=1.0):
    cash, shares, epx = sleeve0, 0.0, np.nan
    eq = np.empty(len(c))
    for i in range(len(c)):
        px = c[i]
        if shares > 0 and exi[i]:
            cash, shares = shares * px * (1 - SLIP), 0.0
        elif shares == 0 and ent[i]:
            epx = px * (1 + SLIP); shares, cash = cash / epx, 0.0
        eq[i] = cash + shares * px
    return eq


def config_port_returns(closes: pd.DataFrame, cfg, start, end):
    e, x, m = cfg
    idx = closes.loc[start:end].index
    eqs = []
    for sym in closes.columns:
        c = closes[sym].dropna()
        sma = c.rolling(m, min_periods=m).mean()
        ent = ((c <= c.rolling(e).min()) & (c > sma)).values
        exi = (c >= c.rolling(x).max()).values
        eq = sleeve_daily_returns(c.values, ent, exi)
        eqs.append(pd.Series(eq, index=c.index).reindex(idx).ffill())
    port = pd.concat(eqs, axis=1).bfill().mean(axis=1)  # équipondéré
    return port.pct_change().fillna(0.0)


def deflated_sharpe(daily_ret: np.ndarray, sr_trials_daily: np.ndarray, n_trials: int):
    """DSR : proba que le vrai Sharpe > 0 compte tenu du multiple testing."""
    sr = daily_ret.mean() / daily_ret.std(ddof=1)            # Sharpe par jour (observé)
    g3 = stats.skew(daily_ret)
    g4 = stats.kurtosis(daily_ret, fisher=False)             # kurtosis non-excès
    n = len(daily_ret)
    var_sr = np.var(sr_trials_daily, ddof=1)
    emc = 0.5772156649
    z = stats.norm.ppf
    # Sharpe attendu du MEILLEUR parmi N essais sous H0 (vrai SR=0)
    sr0 = np.sqrt(var_sr) * ((1 - emc) * z(1 - 1.0 / n_trials)
                             + emc * z(1 - 1.0 / (n_trials * np.e)))
    num = (sr - sr0) * np.sqrt(n - 1)
    den = np.sqrt(1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2)
    dsr = stats.norm.cdf(num / den)
    # PSR vs 0 (sans correction multiple testing) pour comparaison
    psr = stats.norm.cdf(sr * np.sqrt(n - 1) / den)
    return dict(sharpe_daily=float(sr), sharpe_ann=float(sr * np.sqrt(TD)),
                skew=float(g3), kurtosis=float(g4),
                sr0_daily=float(sr0), sr0_ann=float(sr0 * np.sqrt(TD)),
                deflated_sharpe_prob=float(dsr), psr_vs0=float(psr),
                n_trials=n_trials, n_obs=n, var_sr_trials_daily=float(var_sr))


def pbo_cscv(R: np.ndarray, n_splits=14):
    """R: matrice (T, N) de rendements par config. Retourne PBO."""
    T, N = R.shape
    s = n_splits if n_splits % 2 == 0 else n_splits - 1
    rows = np.array_split(np.arange(T), s)
    blocks = [r for r in rows if len(r)]
    s = len(blocks)
    logits = []
    for comb in combinations(range(s), s // 2):
        is_idx = np.concatenate([blocks[i] for i in comb])
        oos_idx = np.concatenate([blocks[i] for i in range(s) if i not in comb])
        is_sr = R[is_idx].mean(0) / (R[is_idx].std(0, ddof=1) + 1e-12)
        oos_sr = R[oos_idx].mean(0) / (R[oos_idx].std(0, ddof=1) + 1e-12)
        n_star = int(np.argmax(is_sr))
        # rang relatif OOS de la config gagnante IS
        rank = stats.rankdata(oos_sr)[n_star] / (N + 1)
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(np.log(rank / (1 - rank)))
    logits = np.array(logits)
    pbo = float(np.mean(logits <= 0))
    return dict(pbo=pbo, n_combinations=len(logits), median_logit=float(np.median(logits)))


def random_entry_test(closes: pd.DataFrame, base_trades: pd.DataFrame, n_perm=1000,
                      start="2005-09-01", end="2026-05-27"):
    """Sharpe sous entrées aléatoires (close>SMA200), même nb de trades/durées."""
    idx = closes.loc[start:end].index
    # durées observées (jours de bourse) par symbole
    sharpes = np.empty(n_perm)
    sym_info = {}
    for sym in closes.columns:
        c = closes[sym].dropna()
        sma = c.rolling(200, min_periods=200).mean()
        elig = ((c > sma)).reindex(idx).fillna(False).values
        rc = c.reindex(idx).values
        g = base_trades[base_trades.symbol == sym]
        sym_info[sym] = (rc, elig, len(g), g.holding_days.dropna().astype(int).values)
    for k in range(n_perm):
        sleeves = []
        for sym, (rc, elig, ntr, holds) in sym_info.items():
            n = len(rc)
            eq = np.ones(n)
            cash, shares = 1.0, 0.0
            elig_days = np.where(elig)[0]
            if len(elig_days) < ntr or len(holds) == 0:
                sleeves.append(np.ones(n)); continue
            entries = np.sort(RNG.choice(elig_days, size=min(ntr, len(elig_days)), replace=False))
            ei = 0
            i = 0
            exit_at = -1
            while i < n:
                if shares == 0 and ei < len(entries) and i == entries[ei]:
                    epx = rc[i] * (1 + SLIP); shares, cash = cash / epx, 0.0
                    exit_at = i + int(RNG.choice(holds))
                    ei += 1
                elif shares > 0 and i >= exit_at:
                    cash, shares = shares * rc[i] * (1 - SLIP), 0.0
                eq[i] = cash + shares * rc[i]
                i += 1
            sleeves.append(eq)
        port = np.mean(sleeves, axis=0)
        r = np.diff(port) / port[:-1]
        sd = r.std(ddof=1)
        sharpes[k] = np.sqrt(TD) * r.mean() / sd if sd > 0 else 0.0
    return sharpes


def main():
    etf = data.load_etf_closes()
    START, END = "2005-09-01", "2026-05-27"

    # Matrice T×108 des rendements par config (pour DSR variance + PBO)
    print("Calcul des 108 séries de rendements par configuration...")
    cols = {}
    for cfg in GRID:
        cols[str(cfg)] = config_port_returns(etf, cfg, START, END)
    R = pd.DataFrame(cols).dropna()
    R.to_csv("dm_config_returns.csv")
    sr_trials_daily = (R.mean() / R.std(ddof=1)).values
    print(f"  matrice {R.shape}, Sharpe annualisés min/med/max:",
          f"{sr_trials_daily.min()*np.sqrt(TD):.2f}/{np.median(sr_trials_daily)*np.sqrt(TD):.2f}/{sr_trials_daily.max()*np.sqrt(TD):.2f}")

    base = R["(7, 7, 200)"].values
    dsr = deflated_sharpe(base, sr_trials_daily, n_trials=len(GRID))
    print("\n--- Deflated Sharpe Ratio ---")
    for k, v in dsr.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    print("\n--- PBO (CSCV) ---")
    pbo = pbo_cscv(R.values, n_splits=14)
    print(f"  PBO = {pbo['pbo']:.1%} sur {pbo['n_combinations']} combinaisons (médiane logit {pbo['median_logit']:.2f})")

    print("\n--- Test des entrées aléatoires (1000 permutations) ---")
    tr = pd.read_csv("trades_full_sleeves.csv").dropna(subset=["pnl"])
    rnd = random_entry_test(etf, tr, n_perm=1000)
    obs_sh = np.sqrt(TD) * base.mean() / base.std(ddof=1)
    pval = float(np.mean(rnd >= obs_sh))
    print(f"  Sharpe observé (équipondéré) = {obs_sh:.2f}")
    print(f"  Sharpe entrées aléatoires: moy={rnd.mean():.2f} p95={np.percentile(rnd,95):.2f} max={rnd.max():.2f}")
    print(f"  p-value (random >= observé) = {pval:.3f}")

    out = dict(deflated_sharpe=dsr, pbo=pbo,
               random_entry=dict(obs_sharpe=float(obs_sh), mean=float(rnd.mean()),
                                 p95=float(np.percentile(rnd, 95)), max=float(rnd.max()),
                                 pvalue=pval),
               grid_sharpe_ann=dict(min=float(sr_trials_daily.min()*np.sqrt(TD)),
                                    med=float(np.median(sr_trials_daily)*np.sqrt(TD)),
                                    max=float(sr_trials_daily.max()*np.sqrt(TD))))
    json.dump(out, open("audit_datamining.json", "w"), indent=1)
    np.save("dm_random_sharpes.npy", rnd)
    print("\nsaved audit_datamining.json")


if __name__ == "__main__":
    main()
