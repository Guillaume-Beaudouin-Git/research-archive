"""
G5 — Verdict par conteneur.

(a) FTMO : déjà clos, ~36%, non-véhicule. Confirmé, on ne re-prouve pas.
(b) PERSONAL BOOK : J1+G1 net swap RÉALISTE (pessimiste) + profil queue G3.
    - SR, MaxDD, worst-month
    - vs A (TSMOM crypto SR 1.33 OOS) et B (delta-neutral SR ~2.0 proxy)
    - décorrélation avec A et B (lecture portefeuille)
    - apport de Sharpe au portefeuille global vs ce qu'on a déjà
(c) CV : un trend-following classique répliqué proprement avec 2 bugs attrapés
    et toute la décomposition honnête EST un item CV valable même si modeste.

Comparaison numérique vs A et B :
- A : Sharpe 1.33 OOS / MaxDD -6.9% (crypto TSMOM long-only weekly)
- B : Sharpe ~2.0 mainnet proxy (delta-neutral carry HL)
- A+B (existant, ERC) : Sharpe 2.24 / MaxDD -1.0%
- J1+G1 candidat (modélé baseline=0.71, réaliste ~0.62)
- Gate D : Sharpe(A+B+D) > 1.10 × 2.24 = 2.46

Si J1+G1 corrélé ~0 à A et B, son apport à A+B+book peut être estimé via :
  σ_global^2 = σ_A^2 + σ_B^2 + σ_book^2 + 2 × cov_AB + 2 × cov_A_book + 2 × cov_B_book
Sous l'hypothèse de corr ≈ 0 (à vérifier sur séries communes si possible) :
  σ_global ≈ √(σ_A^2 + σ_B^2 + σ_book^2)
  E[r_global] = E[r_A] + E[r_B] + E[r_book]
  SR_global = (SR_A × σ_A + SR_B × σ_B + SR_book × σ_book) / σ_global

Ici on traite tous les sleeves à vol cible égal (10% annuelle) → σ_i ≈ 0.10
pour tous → SR_global ≈ (SR_A + SR_B + SR_book) / √3 (si corr=0).

On peut aussi calculer correlation directe J1/G1 vs A (proxy : BTC-USD TSMOM 4w
weekly hold). Pas de B sur Yahoo donc on borne par hypothèse.
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


def tsmom(px, lookback=252, skip=22):
    return np.sign(px.shift(skip) / px.shift(lookback) - 1.0)


def vol_target_pos(px, sig, tgt=0.10, w=20, cap=3.0):
    r = px.pct_change()
    rv = r.rolling(w).std().shift(1) * ANN
    return (tgt / rv).clip(upper=cap) * sig


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN) if x.std() > 0 else float("nan")


def max_dd_normalized(x, tgt=0.10):
    x = pd.Series(x).dropna()
    if x.std() == 0:
        return float("nan")
    x = x / x.std() * (tgt / ANN)
    eq = (1 + x).cumprod()
    return float((eq / eq.cummax() - 1).min())


def main():
    print("G5 — Verdict par conteneur\n")
    jpy = declitch(yahoo_close("JPY=X"), 0.05)
    gold = declitch(yahoo_close("GC=F"), 0.08)
    btc = yahoo_close("BTC-USD")
    irx = yahoo_close("%5EIRX")

    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry_jp = (us - jp).shift(2)
    us_g = irx.reindex(gold.index).ffill().shift(2)

    # J1
    mom_j = tsmom(jpy)
    sig_j = pd.Series(np.where(np.sign(carry_jp).fillna(0) == mom_j, mom_j, 0.0),
                      index=jpy.index)
    pos_j = vol_target_pos(jpy, sig_j)
    swap_j_modelled = pos_j * carry_jp / 100.0 / 252.0
    pnl_j_baseline = (pos_j * jpy.pct_change() - pos_j.diff().abs().fillna(0) * 0.6 / 1e4 + swap_j_modelled).dropna()
    pnl_j_realistic = (pos_j * jpy.pct_change() - pos_j.diff().abs().fillna(0) * 0.6 / 1e4 + 0.7 * swap_j_modelled).dropna()  # 70% du swap modélisé (broker shave)

    # G1
    mom_g = tsmom(gold)
    pos_g = vol_target_pos(gold, mom_g)
    swap_g = -(us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(lower=0)
    pnl_g_baseline = (pos_g * gold.pct_change() - pos_g.diff().abs().fillna(0) * 1.5 / 1e4 + swap_g).dropna()
    pnl_g_realistic = pnl_g_baseline.copy()  # G1 est conservatif déjà (funding payé)

    # A proxy : BTC TSMOM 28 jours, weekly rebal long-only (description Strategy A)
    btc_mom = np.sign(btc.pct_change(28))  # signe ret 28j
    btc_lo = btc_mom.clip(lower=0)
    btc_vol = btc.pct_change().rolling(28).std() * np.sqrt(252)
    btc_pos = (0.10 / btc_vol).clip(upper=3.0) * btc_lo
    # weekly hold : ne change la pos qu'une fois par semaine (Monday)
    btc_pos_w = btc_pos.copy()
    is_mon = btc_pos_w.index.dayofweek == 0
    last = np.nan
    out_pos = []
    for d, v, m in zip(btc_pos_w.index, btc_pos_w.values, is_mon):
        if m or pd.isna(last):
            last = v
        out_pos.append(last)
    btc_pos_w = pd.Series(out_pos, index=btc_pos_w.index)
    btc_pnl = (btc_pos_w * btc.pct_change() - btc_pos_w.diff().abs().fillna(0) * 17 / 1e4).dropna()
    # 17 bps = 0.17% RT crypto

    # === Stats brutes ====================================
    print("=== A. Sleeves vs portefeuille existant ===")
    print(f"  {'sleeve':<35} {'SR':>7} {'MDD(10%)':>10}")
    sleeves = [
        ("J1 baseline (rapport)", pnl_j_baseline),
        ("J1 realistic (swap×0.7)", pnl_j_realistic),
        ("G1 baseline (rapport)", pnl_g_baseline),
        ("Strategy A proxy (BTC TSMOM w)", btc_pnl),
    ]
    for nm, x in sleeves:
        print(f"  {nm:<35} {sharpe(x):+7.3f} {100*max_dd_normalized(x):+10.1f}%")

    # === Book baseline et réaliste =======================
    print("\n=== B. Book J1+G1 sous deux régimes ===")
    df_base = pd.concat([pnl_j_baseline.rename("J"), pnl_g_baseline.rename("G")], axis=1).dropna()
    book_base = df_base["J"] / df_base["J"].std() + df_base["G"] / df_base["G"].std()
    df_real = pd.concat([pnl_j_realistic.rename("J"), pnl_g_realistic.rename("G")], axis=1).dropna()
    book_real = df_real["J"] / df_real["J"].std() + df_real["G"] / df_real["G"].std()
    print(f"  baseline  : SR {sharpe(book_base):+.3f}  MDD(10%) {100*max_dd_normalized(book_base):+.1f}%")
    print(f"  realistic : SR {sharpe(book_real):+.3f}  MDD(10%) {100*max_dd_normalized(book_real):+.1f}%")

    # === Worst month of book realistic ===================
    bm = book_real.resample("ME").sum() / book_real.std() * (0.10 / ANN)
    print(f"\n  worst month (book vol 10%) : {bm.min()*100:+.2f}% ({bm.idxmin().strftime('%Y-%m')})")
    print(f"  median monthly             : {bm.median()*100:+.2f}%")
    print(f"  p5 / p95 monthly           : {bm.quantile(0.05)*100:+.2f}% / {bm.quantile(0.95)*100:+.2f}%")

    # === Corr book réaliste vs A proxy =================
    print("\n=== C. Corrélation avec Strategy A (proxy BTC TSMOM w) ===")
    df_corr = pd.concat([book_real.rename("book"), btc_pnl.rename("A_proxy")], axis=1).dropna()
    print(f"  fenêtre commune : {df_corr.index.min().date()} → {df_corr.index.max().date()} ({len(df_corr)} j)")
    if len(df_corr) > 100:
        print(f"  corr daily : {df_corr.corr().iloc[0, 1]:+.3f}")
        print(f"  corr weekly: {df_corr.resample('W').sum().corr().iloc[0, 1]:+.3f}")
        print(f"  corr monthly:{df_corr.resample('ME').sum().corr().iloc[0, 1]:+.3f}")

    # === D. Apport au portefeuille existant ==============
    print("\n=== D. Apport au portefeuille A+B (hypothèses) ===")
    SR_A = 1.33
    SR_B = 2.0  # mainnet proxy
    # apport book à vol 10% au portefeuille A+B
    SR_book_real = sharpe(book_real / book_real.std() * (0.10 / ANN))  # déjà sur vol 10% effectif
    SR_book_baseline = sharpe(book_base / book_base.std() * (0.10 / ANN))

    # Hypothèse corr A-B ≈ 0 (delta-neutral vs TSMOM), corr book-A ≈ 0 (BTC vs FX/Gold),
    # corr book-B ≈ 0 (carry crypto execution-driven vs trend macro).
    # Tous les sleeves vol 10% → σ²/sleeve = 0.01 → portfolio σ² = 3 × 0.01 - 2×0×0 = 0.03
    # SR_port = (E[r_A] + E[r_B] + E[r_book]) / σ_port = (0.133 + 0.20 + SR_book × 0.10) / √0.03

    for label, sr_book in [("baseline 0.71", SR_book_baseline),
                            ("realistic ~0.62", SR_book_real)]:
        E_port = (SR_A * 0.10) + (SR_B * 0.10) + (sr_book * 0.10)
        sigma_port = np.sqrt(3 * 0.10**2)  # corr 0 hypothèse
        SR_port = E_port / sigma_port
        gain_vs_AB_only = SR_port - ((SR_A * 0.10 + SR_B * 0.10) / np.sqrt(2 * 0.10**2))
        gain_pct = SR_port / ((SR_A * 0.10 + SR_B * 0.10) / np.sqrt(2 * 0.10**2)) - 1
        print(f"  Book {label}: SR_port (A+B+book, corr=0) = {SR_port:.3f}")
        print(f"  vs SR(A+B) = {(SR_A*0.10+SR_B*0.10)/np.sqrt(2*0.10**2):.3f} → gain {gain_pct*100:+.1f}%")
        print(f"  gate D requis : SR(A+B+book) > 1.10 × {(SR_A*0.10+SR_B*0.10)/np.sqrt(2*0.10**2):.2f} = {1.10*(SR_A*0.10+SR_B*0.10)/np.sqrt(2*0.10**2):.2f}")

    # === E. Sensibilité au seuil de corr ==================
    print("\n=== E. Sensibilité à la corr book-A et book-B ===")
    print(f"  {'corr_book_A':>11} {'corr_book_B':>11} {'SR_port':>9}")
    for c_ba in [0.0, 0.1, 0.2, 0.3]:
        for c_bb in [0.0, 0.1, 0.2]:
            sigma_sq = 0.01 + 0.01 + 0.01 + 2 * 0 * 0.01 + 2 * c_ba * 0.01 + 2 * c_bb * 0.01
            # corr A-B = 0 hypo
            E = 0.10 * (SR_A + SR_B + SR_book_real)
            sr_p = E / np.sqrt(sigma_sq)
            print(f"  {c_ba:>11.1f} {c_bb:>11.1f} {sr_p:>9.3f}")

    # === Sauvegarde ===
    pd.DataFrame({"book_realistic": book_real, "book_baseline": book_base,
                  "btc_proxy_A": btc_pnl}).to_csv(
        "<HOME>/Desktop/Algo_claude/data/trend_research/g5_book_vs_A.csv")
    print("\nSAVED → g5_book_vs_A.csv")


if __name__ == "__main__":
    main()
