# Rapport stratégie 67/109 — Price Breakout with NR7 (Setup & Exit)

**Statut :** ❌ **DISCARD (1/4)** — *NR7 + cassure de canal Donchian-1 ; artefact de fill spectaculaire.* · **Source :** https://oxfordstrat.com/trading-strategies/price-breakout-nr7/ (Crabel + Connors/Raschke, rating **C**). · **Registre :** #67. · 2026-06-07.

## Spec & archétype
Setup **NR7** (range du jour < chacun des 6 ranges précédents) → lendemain : buy stop au **plus-haut de la veille** (UpperChannel, Channel_Length=1), sell stop au plus-bas de la veille ; 1er touché = position. Sortie : Time N au close + stop ATR×6. Balayage NR_Length × N. Variante de l'entrée du NR7-ORB (#56, Open±Stretch) : ici l'entrée est une **cassure de canal Donchian-1**.

## Résultats + chiffres décisifs (réf. NR_Length=6, N=10)
**8 283 trades · win 41,4 % · expR +0,0045 · PF 1,034 · Sharpe 0,21 · MaxDD −27,5 %.**

> **DÉLAI+1 :** natif (stop intrabar) +0,21 → fill open[i+1] **−1,39** (expR +0,0045 → **−0,0285**). **→ INVERSION VIOLENTE = artefact de fill pur.**  **TWO-SIDED :** long +0,049 / short +0,007 (fill optimiste).  **DSR :** 2,01 > 1,78 (fill optimiste).  **BETA :** rec 0,18 < BH 1,01.

## Gates — `results/s067_gates.csv` (1/4 FAIL, décisif)

| # | Gate | Résultat | Verdict |
|---|------|----------|---------|
| 1 | Délai+1 | +0,21 → **−1,39** | ❌ **FAIL — artefact de fill intrabar** |
| 2 | Two-sided | long +0,049 / short +0,007 | ✅ PASS (fill optimiste) |
| 3 | DSR | 2,01 > 1,78 | ✅ PASS (fill optimiste) |
| 4 | OOS | +0,007 → +0,002 | ✅ PASS |

## Verdict
❌ **DISCARD.** Confirme la conclusion de la fiche (*« non tradeable une fois les coûts appliqués ; performance similaire au NR7-ORB »*, qui était DISCARD 3/4). Changer la méthode d'entrée — cassure de canal Donchian-1 au lieu de l'ORB Open±Stretch — **ne change rien** : c'est la même entrée par **stop intrabar**, donc le même artefact. Et l'inversion délai+1 est ici la plus violente du projet (+0,21 → **−1,39**), parce que sur un jour NR7 le breakout du plus-haut de la veille se remplit au pire prix intrabar. 67ᵉ traitée, **67ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s067_pricebreak_nr7.py` (dépend de `pricebreak` + `beta_bench`). `ftmo_lab.py` inchangé.
