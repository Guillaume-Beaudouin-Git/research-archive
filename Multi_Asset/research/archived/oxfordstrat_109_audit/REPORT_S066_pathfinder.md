# Rapport stratégie 66/109 — Intermarket Analysis: The Pathfinder (Filter)

**Statut :** ❌ **DISCARD (4/4 + non reproductible FTMO)** — *système devises intermarché ; le filtre T-bonds n'existe pas dans l'univers FTMO et la source montre qu'il a décayé à zéro post-1995.* · **Source :** https://oxfordstrat.com/trading-strategies/intermarket-analysis-pathfinder/ (Nelson Freeburg, rating **C**). · **Registre :** #66. · 2026-06-07.

> 🆕 **Archétype neuf : analyse intermarché.** Un marché (T-bonds) pilote le signal sur un autre (devises). Premier du registre. Mais il bute sur deux écueils, l'un de données, l'autre d'edge.

## Spec & archétype
Système devises de Freeburg : **Setup** (devise) MA(9) > MA(18) ET MA(6) en hausse → long (inverse → short) ; **Filtre intermarché** : MA(3) des T-bonds > MA(25) confirme les longs. Entrée @open ; sortie sur croisement MA(9)/MA(18) @open suivant + stop ATR. Portefeuille = 4 devises (JY, EUR, CHF, GBP).

## Deux problèmes décisifs
**1. Non reproductible en FTMO.** La caractéristique *définissante* est le **filtre T-bonds**. L'univers FTMO (10 indices, 9 forex, 9 commodités, 2 crypto) **ne contient aucun instrument de taux** → le filtre intermarché ne peut pas être reproduit fidèlement. Aucun proxy honnête (or, indices) ne capture la relation taux→devises.

**2. La source elle-même montre que l'edge a décayé.** Benchmark Freeburg (Table 2 de la fiche) :

| | Base (sans T-bonds) 1980-95 | Pathfinder 1980-95 | Base 1996-2015 | Pathfinder 1996-2015 |
|---|---|---|---|---|
| Sharpe | 0,79 | **0,88** | 0,17 | **0,06** |
| Profit Factor | 1,55 | 1,81 | 1,08 | 1,03 |
| Net Profit | 1,06 M | 1,07 M | 109 k | **27 k** |

Le filtre intermarché **améliorait** la base en 1980-1995 mais l'a **dégradée** en 1996-2015 (Sharpe 0,06 < 0,17) : la relation bond→devise a disparu après 1995 (globalisation, convergence des taux).

## Test FTMO du cas de base (dual-MA devises, sans T-bonds)
**349 longs / 330 shorts · expR +0,000 · Sharpe −0,10 · MaxDD…** (4 devises FTMO).
> **DÉLAI+1 :** −0,10 → −0,22.  **TWO-SIDED :** long +0,006 / short −0,012.  **BETA :** rec −0,05 < BH +0,33.  **Gates : 4/4 FAIL** (`edge_positive=False`).

Même le cas de base FTMO-tradable **n'a aucun edge positif après coûts** : c'est un trend-MA devises classique (= beta, ici même pas positif sur 4 paires).

## Verdict
❌ **DISCARD 4/4.** Stratégie écartée pour **deux raisons indépendantes** : (i) son cœur — le filtre intermarché T-bonds — n'est **pas reproductible** dans l'univers FTMO ; (ii) la source démontre que cet edge **a décayé à néant après 1995**, et le cas de base FTMO-tradable n'a **aucun edge positif** (4/4). L'archétype intermarché est intéressant conceptuellement mais inexploitable ici. 66ᵉ traitée, **66ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s066_pathfinder.py` (dépend de `trend_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
