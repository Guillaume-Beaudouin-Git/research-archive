"""
G0 (bis) — Variante miroir des choix d'implémentation du script trend_replication.py
pour isoler la source de l'écart (~25%) entre ma réplication indépendante et leur
chiffrage (J1 0.58 / G1 0.66 / book 0.70).

Hypothèses isolées :
- vol-target via rolling std des SIMPLE returns (vs log returns de g0_replication.py)
- carry laggé t-2 (vs t-1)
- pas de shift additionnel sur mom (le script utilise pour tsmom shift(22)/shift(252)
  qui est déjà laggé d'office ; on ne re-shifte pas)
- swap modélisé sur position long uniquement pour G1, comme l'orig

Si CETTE version donne ~0.58/0.66/0.70 → l'écart de G0 vient des choix d'impl
(simple vs log returns, lag carry), PAS d'un artefact de pipeline.
Si CETTE version ne donne pas non plus 0.58/0.66/0.70 → vrai artefact, à signaler.
"""
from __future__ import annotations
import json
import urllib.request

import numpy as np
import pandas as pd

ANN = np.sqrt(252)
SEED = 7


def yahoo_close(ticker):
    p1, p2 = 946684800, 1780272000
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    j = json.load(urllib.request.urlopen(req, timeout=20))["chart"]["result"][0]
    s = pd.Series(j["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(j["timestamp"], unit="s").normalize())
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")]
    return s.sort_index()


def declitch(s, thresh=0.05):
    r = s.pct_change()
    bad = (r.abs() > thresh) & ((r + r.shift(-1)).abs() < thresh / 2)
    out = s.copy()
    out[bad] = np.nan
    return np.exp(np.log(out).interpolate())


def tsmom_orig(px):
    """Formulation EXACTE de trend_replication.py:43 — sign(P[t-22]/P[t-252] - 1)."""
    return np.sign(px.shift(22) / px.shift(252) - 1.0)


def backtest_orig(px, sig, carry, spread_bp, swap_sign):
    """Reproduction littérale de trend_replication.py:48-63."""
    r = px.pct_change()
    rv = (r.rolling(20).std().shift(1) * ANN)
    pos = (0.10 / rv).clip(upper=3.0) * sig
    turn = pos.diff().abs().fillna(0.0)
    swap = 0.0
    if swap_sign > 0 and carry is not None:
        swap = pos * (carry / 100.0 / 252.0)
    elif swap_sign < 0 and carry is not None:
        swap = -(carry.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos.abs()
    return (pos * r - turn * spread_bp / 1e4 + swap).dropna()


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN)


def max_dd_normalized(x):
    """MaxDD sur série rescalée à vol annuelle 10% (sinon l'unit-vol explose en cumprod)."""
    x = pd.Series(x).dropna()
    if x.std() == 0:
        return float("nan")
    x = x / x.std() * (0.10 / ANN)  # vol annuelle 10%
    eq = (1.0 + x).cumprod()
    return float((eq / eq.cummax() - 1).min())


def block_boot_ci(x, n=2000, block=10, seed=1):
    rng = np.random.default_rng(seed)
    a = pd.Series(x).dropna().values
    m = len(a)
    out = []
    for _ in range(n):
        idx = rng.integers(0, m - block, m // block)
        bl = np.concatenate([a[i:i + block] for i in idx])
        out.append(bl.mean() / bl.std() * ANN)
    return round(float(np.percentile(out, 2.5)), 2), round(float(np.percentile(out, 97.5)), 2)


def main():
    print("Twin-check : reproduction littérale de trend_replication.py")
    jpy = declitch(yahoo_close("JPY=X"), 0.05)
    gold = declitch(yahoo_close("GC=F"), 0.08)
    irx = yahoo_close("%5EIRX")

    # carry orig : us - jp, shift(2)
    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry = (us - jp).shift(2)

    # J1
    momJ = tsmom_orig(jpy)
    sigJ = pd.Series(np.where(np.sign(carry).fillna(0) == momJ, momJ, 0.0), index=jpy.index)
    J = backtest_orig(jpy, sigJ, carry, spread_bp=0.6, swap_sign=+1)

    # G1
    carryG = irx.reindex(gold.index).ffill().shift(2)
    G = backtest_orig(gold, tsmom_orig(gold), carryG, spread_bp=1.5, swap_sign=-1)

    print(f"\nTwin J1 : Sharpe {sharpe(J):+.3f}  skew {J.skew():+.2f}  MDD(norm 10%) {100*max_dd_normalized(J):.1f}%  CI95 {block_boot_ci(J)}")
    print(f"Twin G1 : Sharpe {sharpe(G):+.3f}  skew {G.skew():+.2f}  MDD(norm 10%) {100*max_dd_normalized(G):.1f}%  CI95 {block_boot_ci(G)}")

    df = pd.concat([J.rename("J"), G.rename("G")], axis=1).dropna()
    book = df["J"] / df["J"].std() + df["G"] / df["G"].std()
    print(f"Twin BOOK : Sharpe {sharpe(book):+.3f}  skew {book.skew():+.2f}  corr {df['J'].corr(df['G']):+.3f}")

    # Sauvegarde pour gates suivants
    pd.DataFrame({"J_twin": J, "G_twin": G, "book_twin": book}).to_csv(
        "<HOME>/Desktop/Algo_claude/data/trend_research/g0_twin_pnl.csv")
    print("\nSAVED → g0_twin_pnl.csv")


if __name__ == "__main__":
    main()
