# Rapport stratégie 102/109 — Zero Lag MA (Entry & Filter) — *court (variante #101)*

**Statut :** ❌ **DISCARD (= #101)** — *même ZLMA/EMA + filtre seuil ; trend long = beta.* · **Source :** https://oxfordstrat.com/trading-strategies/zero-lag-moving-average-2/ (Ehlers/Way, rating **C**). · **Registre :** #102. · 2026-06-07.

## Note
Part 2 = même crossover ZLMA/EMA que #101 + une étude de filtre (seuil sur l'erreur normalisée). Le filtre restreint les trades sans changer la nature : **trend long déguisé** (cf #101, long +1,38/short −0,15, ne bat pas le BH). La source conclut « pas significativement mieux que la Hull MA ». Pas de re-test (base = #101). 102ᵉ traitée, **102ᵉ DISCARD**.

## Repro
Voir `code/strat_s101_zlma.py` (même base ZLMA/EMA). `ftmo_lab.py` inchangé.
