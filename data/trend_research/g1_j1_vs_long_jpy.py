"""
G1 — J1 carry-aligned : EDGE ORTHOGONAL OU BETA LONG-JPY DÉGUISÉ ?

Hypothèse à tester (L25-like) : comme carry US-JP > 0 sur ~100% de la période
(US toujours > BoJ), le filtre "carry-aligned" est cosmétique. J1 serait donc
en pratique un long-only TSMOM sur USDJPY (= long USDJPY quand TSMOM le dit),
soit une simple exposition au beta carry-trade JPY classique (USD funds via
yen, monte structurellement quand le différentiel se maintient).

Tests :
1. Comptage du nombre de jours signal > 0, == 0, < 0
2. Comparaison vs buy & hold USDJPY vol-targeté (passif long-only)
3. Comparaison vs TSMOM 12-1 USDJPY non filtré (qui peut shorter)
4. Survie en retirant 2008 (Lehman, JPY rally), 2020 (COVID stress)
5. Stat OLS : J1_ret = α + β × USDJPY_ret + ε  → β proche de 1 ?

Sortie : un tableau qui répond "filtre cosmétique ?" (oui/non) et "edge net du
beta long-JPY ?" (oui/non).
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


def backtest(px, pos, spread_bp, swap_daily=None):
    r = px.pct_change()
    turn = pos.diff().abs().fillna(0.0)
    cost = turn * (spread_bp / 1e4)
    out = pos * r - cost
    if swap_daily is not None:
        out = out + swap_daily.reindex(out.index).fillna(0.0)
    return out.dropna()


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
    print("G1 — J1 carry-aligned : edge ou beta long-JPY ?\n")
    jpy = declitch(yahoo_close("JPY=X"), 0.05)
    irx = yahoo_close("%5EIRX")

    us = irx.reindex(jpy.index).ffill()
    jp = pd.Series(0.0, index=jpy.index)
    jp[jpy.index >= "2024-03-01"] = 0.25
    jp[jpy.index >= "2024-07-01"] = 0.50
    carry = (us - jp).shift(2)

    momJ = tsmom(jpy)
    sigJ_aligned = pd.Series(np.where(np.sign(carry).fillna(0) == momJ, momJ, 0.0), index=jpy.index)
    sigJ_unfiltered = momJ  # TSMOM brut, peut shorter
    sigJ_long_only = momJ.clip(lower=0.0)  # long-only TSMOM (jamais short)
    sigJ_perma_long = pd.Series(1.0, index=jpy.index)  # buy & hold

    # --- Counts ---------------------------------------------
    print("=== 1. Comptage des jours de signal (carry-aligned) ===")
    cnt = sigJ_aligned.value_counts(dropna=False).sort_index()
    n_short_carry = int((sigJ_aligned < 0).sum())
    n_neutral_carry = int((sigJ_aligned == 0).sum())
    n_long_carry = int((sigJ_aligned > 0).sum())
    total = len(sigJ_aligned.dropna())
    print(f"  total points : {total}")
    print(f"  long  (+1) : {n_long_carry} ({100*n_long_carry/total:.1f}%)")
    print(f"  flat   (0) : {n_neutral_carry} ({100*n_neutral_carry/total:.1f}%)")
    print(f"  short (-1) : {n_short_carry} ({100*n_short_carry/total:.1f}%)")

    # Fraction du temps où le filtre carry RÉELLEMENT filtre quelque chose
    # = fraction où signe(carry) != signe(mom) ET mom != 0
    mom_nz = momJ != 0
    signe_carry = np.sign(carry).fillna(0)
    mismatch = (signe_carry != momJ) & mom_nz
    print(f"  jours où carry filter agit (signe_carry != signe_mom): "
          f"{int(mismatch.sum())} ({100*int(mismatch.sum())/total:.1f}%)")

    print("\n  carry < 0 (US < JP, ie filtre 'short JPY' possible) : "
          f"{int((carry < 0).sum())} jours ({100*int((carry<0).sum())/len(carry.dropna()):.1f}%)")
    print(f"  carry > 0 (US > JP, ie long JPY trade favorisé)      : "
          f"{int((carry > 0).sum())} jours ({100*int((carry>0).sum())/len(carry.dropna()):.1f}%)")

    # --- Sleeves ---------------------------------------------
    # J1 carry-aligned
    pos_a = vol_target_pos(jpy, sigJ_aligned)
    swap_a = pos_a * carry / 100.0 / 252.0
    pnl_a = backtest(jpy, pos_a, 0.6, swap_a)
    # J1 unfiltered TSMOM (peut shorter)
    pos_u = vol_target_pos(jpy, sigJ_unfiltered)
    swap_u = pos_u * carry / 100.0 / 252.0  # même swap
    pnl_u = backtest(jpy, pos_u, 0.6, swap_u)
    # J1 long-only TSMOM (jamais short, mais filtre TSMOM)
    pos_lo = vol_target_pos(jpy, sigJ_long_only)
    swap_lo = pos_lo * carry / 100.0 / 252.0
    pnl_lo = backtest(jpy, pos_lo, 0.6, swap_lo)
    # Perma long vol-targeté (buy & hold sans filtre)
    pos_pl = vol_target_pos(jpy, sigJ_perma_long)
    swap_pl = pos_pl * carry / 100.0 / 252.0
    pnl_pl = backtest(jpy, pos_pl, 0.6, swap_pl)
    # Perma long SANS swap (pure carry-trade beta sans crédit)
    pnl_pl_nocarry = backtest(jpy, pos_pl, 0.6, None)

    print("\n=== 2. Sleeves comparés ===")
    rows = [
        ("J1 carry-aligned (rapport)", pnl_a),
        ("TSMOM brut unfilt (peut short)", pnl_u),
        ("TSMOM long-only (jamais short)", pnl_lo),
        ("Buy & hold USDJPY vol-targeté + swap", pnl_pl),
        ("Buy & hold USDJPY vol-targeté SANS swap", pnl_pl_nocarry),
    ]
    print(f"  {'sleeve':<45} {'SR':>7} {'skew':>6} {'MDD':>7}")
    for name, x in rows:
        print(f"  {name:<45} {sharpe(x):+7.3f} {x.skew():+6.2f} {100*max_dd_normalized(x):+6.1f}%")

    # --- OLS J1 = α + β × buy_hold ---------------------------------
    df = pd.concat([pnl_a.rename("J1"), pnl_pl.rename("BH"),
                    pnl_pl_nocarry.rename("BH_noswap")], axis=1).dropna()
    # OLS simple sans statsmodels (évite import lourd) — beta via cov/var
    var_bh = df["BH"].var()
    cov_j_bh = df["J1"].cov(df["BH"])
    beta = cov_j_bh / var_bh
    alpha_daily = df["J1"].mean() - beta * df["BH"].mean()
    resid = df["J1"] - (alpha_daily + beta * df["BH"])
    se_resid = resid.std() / np.sqrt(len(df))
    t_alpha = alpha_daily / se_resid
    print(f"\n=== 3. OLS J1 ~ buy & hold USDJPY (vol-targeté + swap) ===")
    print(f"  beta J1 sur buy&hold : {beta:+.3f}")
    print(f"  alpha daily : {alpha_daily*1e4:+.3f} bps/jour  → annualisé {alpha_daily*252*100:+.2f}%/yr")
    print(f"  t-stat alpha (naïve, non HAC) : {t_alpha:+.2f}")
    print(f"  R² (J1, BH) : {df['J1'].corr(df['BH'])**2:.3f}")
    print(f"  corr J1 vs BH : {df['J1'].corr(df['BH']):+.3f}")
    print(f"  corr J1 vs BH_noswap : {df['J1'].corr(df['BH_noswap']):+.3f}")

    # --- Survie en retirant 2008 et 2020 ----------------------
    print("\n=== 4. Robustesse aux carry-unwinds (2008, 2020) ===")
    masks = {
        "full sample": pd.Series(True, index=pnl_a.index),
        "ex-2008": ~((pnl_a.index.year == 2008)),
        "ex-2020": ~((pnl_a.index.year == 2020)),
        "ex-2008&2020": ~pnl_a.index.year.isin([2008, 2020]),
        "ex-2008&2020&2022": ~pnl_a.index.year.isin([2008, 2020, 2022]),  # 2022 = BoJ stress
    }
    print(f"  {'fenêtre':<25} {'SR J1':>8} {'SR BH':>8} {'corr':>8}")
    for k, m in masks.items():
        j_ = pnl_a[m]
        bh_ = pnl_pl[m]
        print(f"  {k:<25} {sharpe(j_):+8.3f} {sharpe(bh_):+8.3f} {j_.corr(bh_):+8.3f}")

    # --- Per year breakdown ---------------------------------
    print("\n=== 5. Sharpe annuel J1 vs BH (sanity) ===")
    yr_j = pnl_a.groupby(pnl_a.index.year).apply(sharpe)
    yr_b = pnl_pl.groupby(pnl_pl.index.year).apply(sharpe)
    out = pd.concat([yr_j.rename("J1"), yr_b.rename("BH")], axis=1)
    print(out.round(2).to_string())

    # Sauvegarde pour gates suivants
    pd.DataFrame({"J1": pnl_a, "BH": pnl_pl, "BH_noswap": pnl_pl_nocarry,
                  "TSMOM_unfilt": pnl_u, "TSMOM_long_only": pnl_lo}).to_csv(
        "<HOME>/Desktop/Algo_claude/data/trend_research/g1_sleeves.csv")
    print("\nSAVED → g1_sleeves.csv")


if __name__ == "__main__":
    main()
