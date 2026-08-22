# Rapport stratégie 52/109 — MACD Part 1 (Entry) — *court (héritage trend)*

**Statut :** ❌ **DISCARD (2/4)** — *MACD zero-cross = beta long ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/macd-part-1/ (Gerald Appel, rating **C**). · **Registre :** #52. · 2026-06-07.

## Spec & archétype (1 ligne)
MACD = EMA(rapide) − EMA(lente) ; long si MACD>0, short si <0 ; entrée@open, sortie zero-cross / ATR×6. Réutilise `trend_lab`. Point EMA1=40, EMA2=80 (la fiche déconseille le défaut 12/26).

## Résultats + chiffres décisifs (réf. EMA1=40/EMA2=80)
**1 553 trades · win 29,7 % · expR +0,1215 · PF 1,324 · Sharpe 0,53 · MaxDD −60,8 %.**

> **DÉLAI+1 :** +0,53 → +0,53 (PASS).  **TWO-SIDED :** long **+0,391** / short **−0,155** → beta long.  **BETA-MATCHED :** rec 0,63 < BH 1,01.

## Gates — `results/s052_gates.csv` (2/4)
Délai+1 ✅ + OOS ✅ ; FAIL Gate2 (beta long) + DSR (0,58). MACD>0 = être long une tendance = beta. 52ᵉ traitée, **52ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s052_macd.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
