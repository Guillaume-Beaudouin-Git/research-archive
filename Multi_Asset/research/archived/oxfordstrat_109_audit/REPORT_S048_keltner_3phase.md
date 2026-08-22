# Rapport stratégie 48/109 — Keltner Channels 3-Phase Model (Setup) — *court (héritage)*

**Statut :** ❌ **DISCARD net (4/4)** — *= #47 avec phase neutre ; toujours net perdant.* · **Source :** https://oxfordstrat.com/trading-strategies/keltner-channels-2/ (Chester Keltner, rating **C**). · **Registre :** #48. · 2026-06-07.

## Spec & archétype (1 ligne)
**= #47** mais **3-phase (long/flat/short)** : sortie vers neutre quand Close repasse sous la MA médiane (au lieu du reversal direct). Entrée@open + ATR×6. Réutilise `trend_lab` (régime 3-états). Point LB=10, RM=1.

## Résultats + chiffres décisifs (réf. LB=10, RM=1)
**11 442 trades · win 35,6 % · expR −0,0069 · PF 0,949 · Sharpe −0,35 · MaxDD −48,8 %.** (net perdant)

> **DÉLAI+1 :** −0,35 → −0,46 (artefact).  **TWO-SIDED :** long +0,022 / short −0,037.  **BETA-MATCHED :** rec −0,09 < BH 1,01.

## Gates — `results/s048_gates.csv` (4/4 FAIL, edge_pos=False)
La phase neutre n'aide pas — net perdant, encore plus de trades. **Cluster Keltner {#47,#48} : 2/2 DISCARD net.** 48ᵉ traitée, **48ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s048_keltner_3phase.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
