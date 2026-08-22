"""
G2 — SWAP RÉEL vs MODÉLISÉ : grille de sensibilité ±50% sur les hypothèses.

Suspects (L30/L33) :
1. Le rapport MODÉLISE les swaps mais ne les MESURE pas (broker démo manquant).
2. Incohérence interne entre script et inline : G1 swap script ne crédite pas
   les shorts (gold), inline le crédite. Différence ~+0.10 SR sur G1.
3. Pour J1 : proxy carry = ^IRX (13w T-bill) - taux directeur JP estimé. Le vrai
   serait un swap differential 2y US-JP réel.
4. Brokers réels : multiplicateurs swap (souvent 1.5-3× le mid), avec marge.

Tests :
A. Grille ±50% sur swap_multiplier  ∈ {0.5, 0.75, 1.0, 1.25, 1.5, 2.0} pour :
   - J1 : swap_J = mul × pos × carry/100/252
   - G1 : swap_G = mul × −(US_rate × 0.9) × pos.clip(lower=0)
B. Variante G1 swap symétrique (crédite shorts) : impact sur G1 SR
C. Variante J1 SANS swap (worst-case = J1 = pur TSMOM long-only sans carry)
D. Best/worst-case combinés sur le BOOK : SR Book ∈ ?

Gate : si SR book < 0.5 sous hypothèse pessimiste plausible (e.g. mul=1.5 +
G1 swap symétrique) → fragile, flag.
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


def backtest_simple(px, pos, spread_bp):
    r = px.pct_change()
    turn = pos.diff().abs().fillna(0.0)
    cost = turn * (spread_bp / 1e4)
    return (pos * r - cost)


def sharpe(x):
    x = pd.Series(x).dropna()
    return float(x.mean() / x.std() * ANN) if x.std() > 0 else float("nan")


def main():
    print("G2 — Sensibilité swap : grille ±50%\n")
    jpy = declitch(yahoo_close("JPY=X"), 0.05)
    gold = declitch(yahoo_close("GC=F"), 0.08)
    irx = yahoo_close("%5EIRX")

    # carry US-JP
    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry_jp = (us - jp).shift(2)
    us_g = irx.reindex(gold.index).ffill().shift(2)

    # J1 — TSMOM long-only équivalent au filter carry (cf G1)
    mom_j = tsmom(jpy)
    sig_j = pd.Series(np.where(np.sign(carry_jp).fillna(0) == mom_j, mom_j, 0.0),
                      index=jpy.index)
    pos_j = vol_target_pos(jpy, sig_j)
    base_j = backtest_simple(jpy, pos_j, 0.6)

    # G1 — TSMOM
    mom_g = tsmom(gold)
    pos_g = vol_target_pos(gold, mom_g)
    base_g = backtest_simple(gold, pos_g, 1.5)

    multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    print("=== A. Sensibilité J1 (swap mul × carry_J × pos) ===")
    print(f"  {'mul':>5} {'SR J1':>8}")
    j1_grid = {}
    for mul in multipliers:
        swap_j = mul * pos_j * carry_jp / 100.0 / 252.0
        pnl_j = (base_j + swap_j).dropna()
        sr = sharpe(pnl_j)
        j1_grid[mul] = pnl_j
        print(f"  {mul:>5.2f} {sr:+8.3f}")
    # J1 sans swap (carry = 0)
    print(f"  {'NO-S':>5} {sharpe(base_j):+8.3f}  (sans swap du tout)")

    print("\n=== B. Sensibilité G1 (script orig : long pay, short rien) ===")
    print(f"  {'mul':>5} {'SR G1_orig':>10} {'SR G1_credit_shorts':>20}")
    g1_orig_grid = {}
    g1_credit_grid = {}
    for mul in multipliers:
        # orig : long paie, short rien
        swap_g_orig = -mul * (us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(lower=0)
        pnl_g_orig = (base_g + swap_g_orig).dropna()
        # credit symétrique : long paie, short reçoit (mêmes 0.9× ; broker symétrique idéal)
        swap_g_credit = -mul * (us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g  # signe direct
        pnl_g_credit = (base_g + swap_g_credit).dropna()
        g1_orig_grid[mul] = pnl_g_orig
        g1_credit_grid[mul] = pnl_g_credit
        print(f"  {mul:>5.2f} {sharpe(pnl_g_orig):+10.3f} {sharpe(pnl_g_credit):+20.3f}")
    print(f"  {'NO-S':>5} {sharpe(base_g):+10.3f} {sharpe(base_g):+20.3f}  (sans swap)")

    print("\n=== C. BOOK J1+G1 (equal-risk) sous différentes hypothèses jointes ===")
    print(f"  {'hypothèse swap (J1, G1)':<55} {'SR book':>9}")
    scenarios = [
        ("baseline (mul=1, G1 orig)",        1.0, "orig"),
        ("baseline (mul=1, G1 credit shorts)", 1.0, "credit"),
        ("OPTIMISTE J1 ×1.5 + G1 ×0.5 credit", (1.5, 0.5), "credit"),
        ("PESSIMISTE J1 ×0.5 + G1 ×1.5 orig",  (0.5, 1.5), "orig"),
        ("CONSERVATEUR mul=1.25 G1 orig",      1.25, "orig"),
        ("NO-SWAP du tout",                    0.0, "no"),
    ]
    book_summary = {}
    for label, mul, gtype in scenarios:
        # cas simples : tuple sinon mul commun
        if isinstance(mul, tuple):
            mj, mg = mul
        else:
            mj = mg = mul

        if mj > 0:
            swap_j = mj * pos_j * carry_jp / 100.0 / 252.0
        else:
            swap_j = pd.Series(0.0, index=pos_j.index)
        pnl_j = (base_j + swap_j).dropna()

        if gtype == "orig":
            swap_g = -mg * (us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(lower=0)
        elif gtype == "credit":
            swap_g = -mg * (us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g
        else:
            swap_g = pd.Series(0.0, index=pos_g.index)
        pnl_g = (base_g + swap_g).dropna()

        df = pd.concat([pnl_j.rename("J"), pnl_g.rename("G")], axis=1).dropna()
        book = df["J"] / df["J"].std() + df["G"] / df["G"].std()
        book_summary[label] = (sharpe(pnl_j), sharpe(pnl_g), sharpe(book))
        print(f"  {label:<55} J={sharpe(pnl_j):+.2f} G={sharpe(pnl_g):+.2f} BOOK={sharpe(book):+.2f}")

    # --- Décomposition apport swap au SR ----------------------
    print("\n=== D. Décomposition du SR : combien vient du swap ? ===")
    sr_j_no_swap = sharpe(base_j)
    sr_j_with_swap = sharpe((base_j + pos_j * carry_jp / 100.0 / 252.0).dropna())
    print(f"  J1 sans swap : {sr_j_no_swap:+.3f}")
    print(f"  J1 avec swap : {sr_j_with_swap:+.3f}")
    print(f"  Δ swap J1    : {sr_j_with_swap - sr_j_no_swap:+.3f} SR")

    swap_g_orig = -(us_g.clip(lower=0) * 0.9 / 100.0 / 252.0) * pos_g.clip(lower=0)
    sr_g_with_swap_orig = sharpe((base_g + swap_g_orig).dropna())
    print(f"  G1 sans swap : {sharpe(base_g):+.3f}")
    print(f"  G1 avec swap (orig) : {sr_g_with_swap_orig:+.3f}")
    print(f"  Δ swap G1 : {sr_g_with_swap_orig - sharpe(base_g):+.3f} SR")

    # Sauvegarde grille pour pessimist book et G3
    out = pd.DataFrame({
        "J1_baseline_mul1": j1_grid[1.0],
        "J1_pessim_mul0p5": j1_grid[0.5],
        "G1_baseline_orig": g1_orig_grid[1.0],
        "G1_pessim_orig_mul1p5": g1_orig_grid[1.5],
        "G1_credit_shorts_mul1": g1_credit_grid[1.0],
    })
    out.to_csv("<HOME>/Desktop/Algo_claude/data/trend_research/g2_swap_grid.csv")
    print("\nSAVED → g2_swap_grid.csv")


if __name__ == "__main__":
    main()
