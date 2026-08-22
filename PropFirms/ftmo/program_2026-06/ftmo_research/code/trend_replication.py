"""
Réplication indépendante — Investigation Trend-Following FTMO (J1, G1, book, p(pass)).
Reproduit les chiffres clés du RAPPORT_replication_trend.md pour vérification.

Usage : python trend_replication.py
Dépendances : numpy, pandas (réseau pour Yahoo Finance).

Méthodo (charte) : signal à T-1, trade à T ; coût mesuré ; barrière FTMO comme objectif ;
seeds fixés. Tout backtest, 0 jour live. 1 SEUL essai (jamais de % multi-essais).
"""
from __future__ import annotations
import json
import urllib.request

import numpy as np
import pandas as pd

ANN = np.sqrt(252)


# ----------------------------- données -----------------------------
def fetch_yahoo(ticker: str, start: int = 946684800, end: int = 1780272000) -> pd.Series:
    """Close quotidien depuis Yahoo (urllib direct — yfinance hang sur ses retries)."""
    u = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
         f"?period1={start}&period2={end}&interval=1d")
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=15))["chart"]["result"][0]
    s = pd.Series(d["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(d["timestamp"], unit="s").normalize()).dropna()
    return s[~s.index.duplicated()].sort_index()


def clean_glitches(px: pd.Series, thresh: float) -> pd.Series:
    """Corrige les ticks aberrants : |ret|>thresh qui se renversent le lendemain."""
    r = px.pct_change()
    glitch = (r.abs() > thresh) & ((r + r.shift(-1)).abs() < thresh / 2)
    out = px.copy()
    out[glitch] = np.nan
    return np.exp(np.log(out).interpolate())


# ----------------------------- signaux -----------------------------
def tsmom(px: pd.Series) -> pd.Series:
    """TSMOM 12-1 (Moskowitz) : signe du rendement 12 mois hors dernier mois. Laggé d'office."""
    return np.sign(px.shift(22) / px.shift(252) - 1.0)


def backtest(px: pd.Series, sig: pd.Series, carry: pd.Series | None,
             spread_bp: float, swap_sign: int) -> pd.Series:
    """
    Sleeve trend vol-targeté. swap_sign : +1 (carry encaissé, ex USDJPY long),
    -1 (funding payé, ex or long), 0 (aucun). pos[t] n'utilise que des données <= t-1.
    """
    r = px.pct_change()
    rv = (r.rolling(20).std().shift(1) * ANN)
    pos = (0.10 / rv).clip(upper=3.0) * sig          # vol-target 10 %, cap 3x
    turn = pos.diff().abs().fillna(0.0)
    swap = 0.0
    if swap_sign > 0 and carry is not None:           # carry encaissé sur la position
        swap = pos * (carry / 100.0 / 252.0)
    elif swap_sign < 0 and carry is not None:          # funding payé sur le long
        swap = -(carry.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos.abs()
    return (pos * r - turn * spread_bp / 1e4 + swap).dropna()


# ----------------------------- métriques -----------------------------
def sharpe(x: pd.Series) -> float:
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN)


def max_dd(x: pd.Series) -> float:
    eq = (1 + pd.Series(x).dropna()).cumprod()
    return float((eq / eq.cummax() - 1).min())


def bootstrap_ci(x: pd.Series, n: int = 2000, block: int = 10, seed: int = 1) -> tuple:
    rng = np.random.default_rng(seed)
    a = pd.Series(x).dropna().values
    m = len(a)
    out = []
    for _ in range(n):
        idx = rng.integers(0, m - block, m // block)
        bl = np.concatenate([a[i:i + block] for i in idx])
        out.append(bl.mean() / bl.std() * ANN)
    return round(np.percentile(out, 2.5), 2), round(np.percentile(out, 97.5), 2)


# ----------------------------- barrière FTMO 2-step -----------------------------
def ppass_ftmo_2step(ret_unit_vol: np.ndarray, sizing: float,
                     cap: int = 126, nb: int = 9000, seed: int = 2) -> tuple:
    """p(pass) 1 essai. Block-bootstrap 21 j. Daily DD 5 %, total DD 10 % statique."""
    rng = np.random.default_rng(seed)
    n = len(ret_unit_vol)
    blk, cols = 21, cap // 21 + 2
    ix = rng.integers(0, n - blk, (nb, cols))
    M = np.concatenate([ret_unit_vol[ix[:, j][:, None] + np.arange(blk)]
                        for j in range(cols)], axis=1)[:, :cap] * sizing
    eq = np.ones(nb); st = np.zeros(nb, np.int8); td = np.zeros(nb, int)
    ph = np.ones(nb, np.int8); tg = np.full(nb, 0.10)
    for t in range(M.shape[1]):
        live = st == 0
        x = M[:, t]; eq = np.where(live, eq * (1 + x), eq); td = np.where(live, td + 1, td)
        bust = live & ((x < -0.05) | (eq < 0.90)); st = np.where(bust, 2, st); live = st == 0
        p1 = live & (eq >= 1.10) & (td >= 4) & (ph == 1)
        eq = np.where(p1, 1.0, eq); tg = np.where(p1, 0.05, tg); ph = np.where(p1, 2, ph); td = np.where(p1, 0, td)
        fu = (st == 0) & (ph == 2) & (eq >= 1.05) & (td >= 4); st = np.where(fu, 1, st)
    return float((st == 1).mean()), float((st == 2).mean())


# ----------------------------- main -----------------------------
def main() -> None:
    print("Fetch Yahoo (USDJPY, Gold, ^IRX)…")
    jpy = clean_glitches(fetch_yahoo("JPY=X"), 0.05)
    gold = clean_glitches(fetch_yahoo("GC=F"), 0.08)
    irx = fetch_yahoo("%5EIRX")

    # carry proxy : US 13-sem − JP(~0, +0.25/0.5 BoJ 2024+), laggé 2 j
    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry = (us - jp).shift(2)

    # J1 : USDJPY carry-aligned (long-only de facto)
    momJ = tsmom(jpy)
    sigJ = pd.Series(np.where(np.sign(carry).fillna(0) == momJ, momJ, 0.0), index=jpy.index)
    J = backtest(jpy, sigJ, carry, spread_bp=0.6, swap_sign=+1)

    # G1 : Gold TSMOM, funding négatif
    carryG = irx.reindex(gold.index).ffill().shift(2)
    G = backtest(gold, tsmom(gold), carryG, spread_bp=1.5, swap_sign=-1)

    print("\n=== SLEEVES (à comparer §5.1) ===")
    for nm, s in [("J1 USDJPY", J), ("G1 Gold", G)]:
        print(f"  {nm}: Sharpe {sharpe(s):+.2f} | skew {s.skew():+.2f} | MaxDD {100*max_dd(s):.0f}%")
    print(f"  J1 bootstrap CI95 Sharpe : {bootstrap_ci(J)}  (attendu ~[0.18, 0.96])")
    print(f"  J1 régime : 2000-12 {sharpe(J[J.index<'2013']):+.2f} / 2013-26 {sharpe(J[J.index>='2013']):+.2f}")

    # Book equal-risk
    df = pd.concat([J.rename("J"), G.rename("G")], axis=1).dropna()
    book = df["J"] / df["J"].std() + df["G"] / df["G"].std()
    print("\n=== BOOK J1+G1 (à comparer §5.2) ===")
    print(f"  corr J-G {df['J'].corr(df['G']):+.2f} | Sharpe {sharpe(book):+.2f} | skew {book.skew():+.2f}")

    # p(pass) FTMO 2-step, 1 essai
    bz = (book / book.std()).values
    print("\n=== p(pass) FTMO 2-step — 1 ESSAI (à comparer §5.3) ===")
    for s in (0.010, 0.015, 0.020):
        pa, bu = ppass_ftmo_2step(bz, s)
        print(f"  book sizing {100*s:.1f}% : p(pass) {100*pa:.0f}% (bust {100*bu:.0f}%)")
    print("\nVerdict : book ~0.72 Sharpe, p(pass) 1 essai ~33-36% → mur structurel. 0 jour live.")


if __name__ == "__main__":
    main()
