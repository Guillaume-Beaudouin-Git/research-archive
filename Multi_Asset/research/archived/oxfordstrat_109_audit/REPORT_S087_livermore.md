# Rapport stratégie 87/109 — The Livermore System Part 1 (Filters) — *momentum = beta*

**Statut :** ❌ **DISCARD (2/4)** — *« average momentum model » (dixit la source) = beta long déguisé.* · **Source :** https://oxfordstrat.com/trading-strategies/livermore-system-1/ (Jesse Livermore / Kaufman, rating **C**). · **Registre :** #87. · 2026-06-07.

## Spec & archétype
Système de swing Livermore : pivots offre/demande (hauts/bas locaux suivis d'un swing ≥ Swing_Filter ATR) ; entrée à l'open après **pénétration des 2 derniers Supply Pivots + Noise** (= cassure de swing haussière) ; sortie sur pénétration du Demand Pivot + stop ATR. La fiche conclut : *« an average momentum model »*. **Proxy** : régime de cassure Donchian persistant (long après nouveau plus-haut N-barres, short après nouveau plus-bas), entrée @open, sortie sur flip + ATR. `trend_lab`. Réf. N=40.

## Résultats (réf. N=40)
**1 855 trades · win 32,1 % · expR +0,018 · PF 1,043 · Sharpe 0,08 · MaxDD −26,8 %.**
> **DÉLAI+1 :** +0,08 → +0,08 (entrée @open, pas d'artefact).  **TWO-SIDED :** long **+0,245** / short **−0,215** → le short perd = **beta long**.  **DSR :** grille = bruit.  **BETA :** rec 0,13 < BH 1,01.

## Gates — `results/s087_gates.csv` (2/4 FAIL)
Comme tout le cluster trend/momentum (#69 Price Momentum, #80 SMA) : tout le PnL vient du long, le short perd, et il **ne bat pas le buy&hold**. Confirme le verdict de la source (« average momentum model »). 87ᵉ traitée, **87ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s087_livermore.py` (proxy Donchian-régime ; dépend de `trend_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
