# Rapport stratégie 69/109 — Price Momentum Model (Benchmark) — *court (héritage trend)*

**Statut :** ❌ **DISCARD (2/4)** — *benchmark momentum dual = beta long déguisé.* · **Source :** https://oxfordstrat.com/trading-strategies/price-momentum-model/ (Perry Kaufman, rating **C**). · **Registre :** #69. · 2026-06-07.

## Spec & archétype
Trend dual-momentum pur : M1 (rapide) = Close − Close[−M1_LB+1], M2 (lent) = Close − Close[−M2_LB+1]. **Long si M1>0 ET M2>0** ; short si les deux <0. Entrée @open, sortie sur retournement de M1 @open + stop ATR. Défaut M2_LB > 80 (on prend 100), M1 = 0,5·M2 = 50. Archétype = momentum/tendance = beta. Réutilise `trend_lab` (machine à états @open).

## Résultats + chiffres décisifs (réf. M2=100, M1=50)
**6 481 trades · expR +0,016 · Sharpe 0,36 · MaxDD…**
> **DÉLAI+1 :** +0,36 → **+0,36** (PASS — entrée @open, pas d'artefact).  **TWO-SIDED :** long **+0,070** / short **−0,044** → asymétrie = **beta long**.  **DSR :** 0,64 < 1,65 → grille = bruit.  **OOS :** +0,022 → +0,010 PASS.  **BETA-MATCHED :** rec **0,30 < BH 1,01** → ne bat pas le beta.

## Gates — `results/s069_gates.csv` (2/4 FAIL)
Survit au délai+1 (entrée @open) et à l'OOS, mais échoue two-sided (le short perd, le long porte tout) et DSR (grille non significative) ; surtout il **ne bat pas le buy&hold** (0,30 vs 1,01). C'est la définition d'un **proxy de tendance long** — un beta, pas un alpha. Cohérent avec tout le cluster momentum/trend du projet (#4-10, #23-26, #46-54, #64). 69ᵉ traitée, **69ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s069_price_momentum.py` (dépend de `trend_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
