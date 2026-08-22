# Rapport stratégie 93/109 — Volume Filters Part 2 — *court (volume non reproductible)*

**Statut :** ❌ **DISCARD (= #92)** — *variante de filtre volume ; non reproductible FTMO + base = breakout beta.* · **Source :** https://oxfordstrat.com/trading-strategies/volume-filters-2/ (Edwards/Magee, rating **C**). · **Registre :** #93. · 2026-06-07.

## Note
Part 2 = variante de définition du filtre volume sur le même breakout de prix Donchian. **Même double obstacle que #92** : (i) le **volume n'est pas disponible** sur l'univers FTMO (CFD sans volume centralisé), donc le filtre n'est pas reproductible ; (ii) la **base price-breakout = trend/beta long** (cf #92, #20-22 DISCARD). La série Volume Filters de la source conclut uniformément que le volume **n'améliore pas** les breakouts de prix. Pas de re-test (base identique à #92). 93ᵉ traitée, **93ᵉ DISCARD**.

## Repro
Voir `code/strat_s092_volume_filters.py` (base price-breakout identique ; le filtre volume n'est pas reproductible FTMO). `ftmo_lab.py` inchangé.
