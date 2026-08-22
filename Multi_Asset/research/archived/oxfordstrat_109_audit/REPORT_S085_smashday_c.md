# Rapport stratégie 85/109 — Smash Day Type C (Exits) — *court (variante sans filtre, rating D)*

**Statut :** ❌ **DISCARD (3/4)** — *Type B sans filtre tendance ; net perdant, ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/smash-day-pattern-c/ (Williams, rating **D**). · **Registre :** #85. · 2026-06-07.

## Spec & résultats
= setup Type B (Close<Low[t−1] / Close>High[t−1]) **sans filtre de tendance** (la source ajoute une cible % en sortie — non implémentée ici, mineur). Réf. Time=10 : **11 983 trades · win 25,0 % · expR −0,0054 · Sharpe −0,36 · MaxDD −53,0 %.**
> **DÉLAI+1 :** −0,36 → +1,57 (artefact inverse : le stop intrabar achète le plus-haut d'un jour de reversal volatil = très mauvais prix ; sans filtre, le pattern est encore plus bruité).  **TWO-SIDED :** long +0,011 / short −0,019.  **BETA :** rec **−1,02** < BH 1,01.

## Gates — `results/s085_gates.csv` (3/4 FAIL, `edge_positive=False`)
Retirer le filtre dégrade encore (net −0,36, rec −1,02). 85ᵉ traitée, **85ᵉ DISCARD**. **Cluster Smash Day {#81-85} = 5/5 DISCARD** : le reversal de Williams (entrée stop au-delà de l'extrême d'un jour de smash) achète systématiquement de mauvais prix sur l'univers FTMO et ne bat jamais le beta.

## Repro
`cd oxfordstrat_109/code && python strat_s085_smashday_c.py`. `ftmo_lab.py` inchangé.
