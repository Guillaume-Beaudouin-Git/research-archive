# Rapport stratégie 70/109 — Profit-Taking: Perry Kaufman (Test Period 1)

**Statut :** ❌ **DISCARD (4/4)** — *système EMA-turn net perdant ; et l'étude confirme que les cibles de profit DÉGRADENT le résultat.* · **Source :** https://oxfordstrat.com/trading-strategies/profit-taking-1/ (Perry Kaufman, rating **N/A** — étude de sortie). · **Registre :** #70. · 2026-06-07.

## Spec & archétype
Système de base : EMA(EMA_Length) se retourne à la hausse (EMA[i]>EMA[i−1] & EMA[i−1]<EMA[i−2]) → achat @close ; retournement baissier → vente @close. Sortie : **cible % de profit** (Close ≥ Entrée×(1+T/100)) + stop ATR×6. L'**étude** : une cible de profit aide-t-elle ? Réutilise un sim dédié (entrée @close sur retournement EMA) + `beta_bench`.

## Résultats + chiffres décisifs (réf. EMA=40, Target=20 %)
**expR −0,115 · Sharpe −0,71** (le système de base est **net perdant**).
> **DÉLAI+1 :** −0,71 → −0,80.  **TWO-SIDED :** long +0,118 / short −0,249.  **DSR :** −0,29 < 1,65.  **OOS :** −0,149 → −0,084.  **BETA :** ne bat pas. **Gates 4/4 FAIL** (`edge_positive=False`).

**Étude prise-de-profit (expR par niveau de cible) :**

| Target % | 10 | 20 | 50 | **Aucune** |
|---|---|---|---|---|
| expR | −0,091 | −0,115 | −0,112 | **−0,092** |

→ La version **sans cible (−0,092)** fait **mieux** que les cibles serrées (−0,115 à 20 %). **Les cibles de profit dégradent le résultat.**

## Verdict
❌ **DISCARD 4/4.** Double conclusion : (i) le système d'entrée EMA-turn est un **trend-MA net perdant** sur l'univers FTMO (Sharpe −0,71) — cohérent avec tout le cluster MA/trend ; (ii) on **reproduit le résultat de la fiche** qui *contredit* Kaufman (1995) : sur un large échantillon, *« les cibles de profit simples réduisent les rendements absolus ET ajustés du risque »*. Kaufman avait conclu l'inverse sur 3 marchés / 1988-1993 (sur-ajustement de petit échantillon). Leçon de méthode utile : une règle de sortie « intuitive » testée sur petit échantillon ne survit pas hors échantillon. 70ᵉ traitée, **70ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s070_profit_taking.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé.
