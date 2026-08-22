# Rapport stratégie 75/109 — Reversal Patterns Part 2 (pivots + divergence MACD) — *court (variante #74)*

**Statut :** ❌ **DISCARD (2/4)** — *#74 + filtre divergence MACD ; le filtre ne sauve pas l'edge.* · **Source :** https://oxfordstrat.com/trading-strategies/reversal-patterns-part-2/ (Wyckoff/Crabel/Appel, rating **C**). · **Registre :** #75. · 2026-06-07.

## Spec & archétype
Identique à #74 (pivot reversal deux côtés) **+ filtre divergence prix-momentum** : la cassure du pivot doit être **non confirmée par le MACD(12,26,9)** (plus-bas du prix sous le pivot mais MACD plus haut = divergence haussière ; miroir pour le short). Réutilise `s074.simulate_rev(macd_div=True)`. Réf. RR=4, TD=20.

## Résultats (réf. RR=4, TD=20)
**3 788 trades · win 28,9 % · expR +0,0113 · PF 1,085 · Sharpe 0,37 · MaxDD −23,6 %.**
> **DÉLAI+1 :** +0,37 → +0,71.  **TWO-SIDED :** long **+0,039** / short **−0,006** → **beta long déguisé**.  **DSR :** 0,37 < 1,52 → bruit.  **BETA-MATCHED :** rec 0,78 < BH 1,01.

## Gates — `results/s075_gates.csv` (2/4 FAIL)
Le filtre de divergence MACD réduit le nombre de trades (5 007 → 3 788) et baisse un peu le MaxDD (−29 % → −24 %), mais **ne change pas le verdict** : toujours long-dominé (beta) et grille non significative (DSR). La fiche dit que la divergence « ajoute de la valeur » vs Part 1 — vrai à la marge (UPI/Sharpe légèrement mieux à gros RR), mais **insuffisant** : ne bat pas le beta, edge non significatif. 75ᵉ traitée, **75ᵉ DISCARD**. Cluster Reversal Patterns {#74,#75} = 2/2 DISCARD.

## Repro
`cd oxfordstrat_109/code && python strat_s075_reversal2.py` (dépend de `strat_s074_reversal`). `ftmo_lab.py` inchangé.
