# Rapport stratégie 86/109 — TD Sequential (DeMark)

**Statut :** ❌ **DISCARD (4/4)** — *exhaustion MR célèbre ; pas d'edge positif après coûts sur l'univers FTMO.* · **Source :** https://oxfordstrat.com/trading-strategies/td-sequential-1/ (Thomas DeMark, rating **N/A**). · **Registre :** #86. · 2026-06-07.

## Spec & archétype
**TD Sequential** (réversion par épuisement) : **Setup** = 9 clôtures consécutives < clôture 4 jours avant (achat) ; **Intersection** (condition d'ordre, assumée) ; **Countdown** = compter les barres où Close < Low[i−2] jusqu'à 13 (annulé si Close > plus-haut du setup) ; **Entrée méthode 2** (testée) = à la clôture de la 1ʳᵉ barre où Close > Close[i−4] après le countdown. Sortie : stop DeMark (pattern_low − risque) + stop ATR×6 + temps. Short = miroir. Moteur `td_seq.simulate_tdseq`. *Simplifications documentées : intersection assumée, règle d'annulation (a) omise, méthode 2 seule.*

## Résultats (réf. Setup=9, Countdown=13)
**1 392 trades · win 33,7 % · expR −0,0080 · PF 0,968 · Sharpe −0,09 · MaxDD −16,5 %.** (net perdant)
> **DÉLAI+1 :** −0,09 → −0,06 (pas d'edge dans les deux cas).  **TWO-SIDED :** long **+0,095** (n535) / short **−0,072** (n857).  **BETA :** rec 0,43 < BH 1,01.

## Gates — `results/s086_gates.csv` (4/4 FAIL, `edge_positive=False`)
**Asymétrie instructive** : la jambe **long** (acheter l'épuisement baissier après un 9-setup + 13-countdown) a un expR **positif +0,095** — il y a une vraie réversion d'épuisement à l'achat. Mais la jambe **short** (vendre l'épuisement haussier) **perd −0,072** (vendre la force dans des marchés qui dérivent à la hausse), et l'ensemble est **net négatif après coûts**. Le célèbre indicateur DeMark ne passe pas le filtre coûts/beta sur l'univers FTMO. 86ᵉ traitée, **86ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s086_td_sequential.py` (dépend de `td_seq` + `beta_bench`). `ftmo_lab.py` inchangé.
