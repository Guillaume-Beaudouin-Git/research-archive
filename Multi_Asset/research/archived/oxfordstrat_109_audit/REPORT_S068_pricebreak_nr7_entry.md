# Rapport stratégie 68/109 — Price Breakout with NR7 (Setup & Entry) — *court (héritage)*

**Statut :** ❌ **DISCARD (4/4)** — *jumeau de #67 ; élargir le canal d'entrée détruit le peu d'edge.* · **Source :** https://oxfordstrat.com/trading-strategies/price-breakout-nr7-entry/ (Crabel + Connors/Raschke, rating **C**). · **Registre :** #68. · 2026-06-07.

## Spec & archétype
Même setup NR7 + entrée cassure de canal que #67, mais l'étude **balaye Channel_Length** (buy stop au plus-haut sur CL jours, pas seulement la veille). N=10 fixe. Réf. Channel_Length=10 (la fiche dit « mieux quand CL ≥ 10 »). Réutilise le moteur `pricebreak` de #67.

## Résultats + chiffres décisifs (réf. Channel_Length=10, NR=6, N=10)
**expR −0,0028 · Sharpe −0,09** (net perdant).
> **DÉLAI+1 :** −0,09 → **−0,43** (artefact + perdant).  **TWO-SIDED :** long +0,018 / short −0,039.  **DSR :** 0,33 < 1,75 (bruit).  **OOS :** −0,006 → 0,000 (flip).  **BETA :** rec 0,43 < BH 1,01.

Grille expR : seule la colonne **CL1 (= #67)** est positive ; dès CL≥5 l'expR **passe négatif** (cf. `results/s068_sensitivity_expectancy.csv`). Élargir le canal = entrer plus tard dans un faux breakout → pire.

## Gates — `results/s068_gates.csv` (4/4 FAIL, `edge_positive=False`)
La « meilleure » zone que la fiche revendique (CL≥10) est en réalité **négative après coûts** sur l'univers FTMO. L'amélioration apparente de la fiche est un artefact de fill (sans coûts). 68ᵉ traitée, **68ᵉ DISCARD**. Cluster Price-Breakout-NR7 {#67,#68} = 2/2 DISCARD ; bilan famille NR/NR7/ORB-stop maintenu à 0 edge réel.

## Repro
`cd oxfordstrat_109/code && python strat_s068_pricebreak_nr7_entry.py` (dépend de `pricebreak` + `strat_s067`). `ftmo_lab.py` inchangé.
