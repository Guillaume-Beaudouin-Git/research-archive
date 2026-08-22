"""
G3 — Profil queue gauche du book J1+G1 (skew négatif L7).

Suspect L7 : skew −0.36 du book est le VRAI tueur de p(pass) sur barrière
symétrique. Un SR 0.70 skew+ donnerait plus de p(pass) qu'un SR 0.70 skew−,
parce que la barrière daily DD coupe le côté gauche de la distribution.

Tests :
1. Statistiques tail honest : worst day, worst week, worst month, p1/p5 daily,
   p1/p5 monthly, CVaR 5%/1% daily, CVaR 5%/1% monthly.
2. Skew/kurtosis fenêtre roulante (le skew est-il stable ou concentré ?).
3. Top-5 plus mauvaises journées : datent-elles de 2008/2020/2022 ? = carry-crash
   structurel (skew non-réparable par trailing-stop intraday parce que le crash
   est gap-overnight).
4. Comparaison skew daily vs skew monthly : si skew daily ~ skew monthly →
   queue persistante, pas du noise quotidien.

Documente pourquoi un trailing-stop intraday ne répare PAS un carry-crash.
"""
from __future__ import annotations
import json
import urllib.request

import numpy as np
import pandas as pd

ANN = np.sqrt(252)


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


def tsmom(px):
    return np.sign(px.shift(22) / px.shift(252) - 1.0)


def vol_target_pos(px, sig, tgt=0.10, w=20, cap=3.0):
    r = px.pct_change()
    rv = r.rolling(w).std().shift(1) * ANN
    return (tgt / rv).clip(upper=cap) * sig


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN) if x.std() > 0 else float("nan")


def cvar(x, alpha):
    x = pd.Series(x).dropna()
    q = x.quantile(alpha)
    return float(x[x <= q].mean())


def main():
    print("G3 — Profil queue gauche du book J1+G1\n")
    jpy = declitch(yahoo_close("JPY=X"), 0.05)
    gold = declitch(yahoo_close("GC=F"), 0.08)
    irx = yahoo_close("%5EIRX")

    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry_jp = (us - jp).shift(2)
    us_g = irx.reindex(gold.index).ffill().shift(2)

    # J1 carry-aligned
    mom_j = tsmom(jpy)
    sig_j = pd.Series(np.where(np.sign(carry_jp).fillna(0) == mom_j, mom_j, 0.0),
                      index=jpy.index)
    pos_j = vol_target_pos(jpy, sig_j)
    swap_j = pos_j * carry_jp / 100.0 / 252.0
    pnl_j = (pos_j * jpy.pct_change() - pos_j.diff().abs().fillna(0.0) * 0.6 / 1e4 + swap_j).dropna()
    # G1
    pos_g = vol_target_pos(gold, tsmom(gold))
    swap_g = -(us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(lower=0)
    pnl_g = (pos_g * gold.pct_change() - pos_g.diff().abs().fillna(0.0) * 1.5 / 1e4 + swap_g).dropna()

    df = pd.concat([pnl_j.rename("J"), pnl_g.rename("G")], axis=1).dropna()
    # Book unit-vol re-normalisé à 10% annuel (sinon stats à des échelles bizarres)
    j_u = df["J"] / df["J"].std() * (0.10 / ANN)
    g_u = df["G"] / df["G"].std() * (0.10 / ANN)
    book = j_u + g_u

    # === Stats tail daily ============================
    print("=== A. Stats tail daily ===")
    for name, x in [("J1 (vol 10%)", j_u), ("G1 (vol 10%)", g_u), ("BOOK (J+G unit-vol)", book)]:
        sd = float(x.std())
        sk = float(x.skew())
        ku = float(x.kurt())
        worst = float(x.min())
        p1 = float(x.quantile(0.01))
        p5 = float(x.quantile(0.05))
        cvar5 = cvar(x, 0.05)
        cvar1 = cvar(x, 0.01)
        worst_date = x.idxmin()
        print(f"  {name:<25}  std={sd*100:.2f}%  skew={sk:+.2f}  kurt={ku:+.2f}")
        print(f"    worst day {worst*100:+.2f}% ({worst_date.date()}) | p1 {p1*100:+.2f}% | p5 {p5*100:+.2f}%")
        print(f"    CVaR1 {cvar1*100:+.2f}% | CVaR5 {cvar5*100:+.2f}%")

    # === Stats tail monthly ==========================
    print("\n=== B. Stats tail mensuel ===")
    for name, x in [("J1 (vol 10%)", j_u), ("G1 (vol 10%)", g_u), ("BOOK", book)]:
        m = x.resample("ME").sum()
        sk = float(m.skew())
        worst = float(m.min())
        p1 = float(m.quantile(0.01))
        p5 = float(m.quantile(0.05))
        worst_date = m.idxmin()
        print(f"  {name:<22}  skew_M={sk:+.2f}  worst_month {worst*100:+.2f}% "
              f"({worst_date.strftime('%Y-%m')})  p1_M {p1*100:+.2f}%  p5_M {p5*100:+.2f}%")

    # === Top-5 worst days ===========================
    print("\n=== C. Top-10 worst days du BOOK ===")
    bw = book.sort_values().head(10)
    print(f"  {'date':<12} {'return %':>9}")
    for d, v in bw.items():
        print(f"  {str(d.date()):<12} {v*100:+9.2f}")

    # === D. Concentration sur 2008/2020/2022 ============
    print("\n=== D. Concentration crash years (carry-unwind suspects) ===")
    years_susp = [2008, 2020, 2022]
    bw_susp = bw[bw.index.year.isin(years_susp)]
    print(f"  Top-10 worst days dont en {years_susp} : {len(bw_susp)}/10")
    if len(bw_susp) > 0:
        print(f"  Détail : {[str(d.date()) for d in bw_susp.index]}")

    # === E. Rolling skew (stabilité du skew) ==========
    print("\n=== E. Stabilité du skew (rolling 252j) ===")
    sk_roll = book.rolling(252).skew()
    sk_roll = sk_roll.dropna()
    print(f"  skew rolling 252j : min {sk_roll.min():+.2f} | max {sk_roll.max():+.2f} | "
          f"médiane {sk_roll.median():+.2f}")
    n_neg = int((sk_roll < 0).sum())
    n_tot = len(sk_roll)
    print(f"  fraction du temps skew rolling < 0 : {100*n_neg/n_tot:.0f}%")

    # === F. Pire mois identifié — drawdown spécifique ===
    print("\n=== F. Pire fenêtre 21j (drawdown intra-mois) ===")
    rolling_21 = book.rolling(21).sum()
    worst_21 = rolling_21.idxmin()
    print(f"  Pire perte 21j : {rolling_21.min()*100:+.2f}% en finissant le {worst_21.date()}")

    # === G. Impact d'un cap intraday simulé : si on coupait sur -3% ?
    print("\n=== G. Impact d'un kill switch quotidien -3% (gap-overnight = ininterceptable) ===")
    capped = book.clip(lower=-0.03)
    n_capped = int((book < -0.03).sum())
    sr_orig = sharpe(book)
    sr_capped = sharpe(capped)
    print(f"  Jours où le kill switch s'active : {n_capped} ({100*n_capped/len(book):.2f}%)")
    print(f"  SR book : {sr_orig:+.3f} → SR avec cap : {sr_capped:+.3f}")
    print(f"  Δ SR cap intraday : {sr_capped - sr_orig:+.3f}")
    print("  → Si Δ ≈ 0, le kill switch n'aide pas car les pertes sont essentiellement gap-overnight.")

    # === H. Lien skew→survival théorique sur barrière 5% daily DD ==
    print("\n=== H. Estimation p(survival) sur barrière 5% daily DD (block-bootstrap simple) ===")
    # Resamping unit-vol normalisé à 1%/jour pour pouvoir tester sizing 1.5%
    book_z = book / book.std()  # unit-vol journalier
    # Compter fréquence des jours < -5% post-rescaling à différents sizings
    for sz in [0.005, 0.01, 0.015, 0.02]:
        scaled = book_z * sz
        n_breach = int((scaled < -0.05).sum())
        print(f"  sizing {sz*100:.1f}% : jours où daily < -5% : {n_breach} (en {len(scaled)} = {100*n_breach/len(scaled):.3f}%)")

    pd.DataFrame({"book_10pct_vol": book, "J1_10pct_vol": j_u, "G1_10pct_vol": g_u}).to_csv(
        "<HOME>/Desktop/Algo_claude/data/trend_research/g3_book_book.csv")
    print("\nSAVED → g3_book_book.csv")


if __name__ == "__main__":
    main()
