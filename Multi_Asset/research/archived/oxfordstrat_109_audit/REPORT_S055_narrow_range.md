# Rapport stratégie 55/109 — Narrow Range N-Day Pattern (Setup) — *court (héritage ORB-stop)*

**Statut :** ❌ **DISCARD net (4/4)** — *NR Crabel + ORB-stop = artefact de fill (S001 family).* · **Source :** https://oxfordstrat.com/trading-strategies/narrow-range/ (Toby Crabel, rating **C**). · **Registre :** #55. · 2026-06-07.

## Spec & archétype (1 ligne)
Setup NR-N (range N jours la + étroite des Look_Back derniers) + **entrée ORB-stop Crabel** (Open ± Stretch) ; sorties Time(10)+Stretch+ATR. Réutilise `ftmo_lab.simulate_bracket` + Crabel stretch. Point N=4, Look_Back=20.

## Résultats + chiffres décisifs (réf. N=4, Look_Back=20)
**4 242 trades · win 43,4 % · expR +0,0061 · PF 1,046 · Sharpe 0,21 · MaxDD −19,0 %.**

> **DÉLAI+1 (DÉCISIF) :** natif +0,21 → réel **−0,88** (expR +0,006 → −0,025). **→ artefact de fill intrabar.**  OOS flip ; rec −0,13 < BH 1,01.

## Gates — `results/s055_gates.csv` (4/4 FAIL)
L'entrée ORB-stop s'effondre au fill réaliste — même mode de mort que S001/S002/GSV. **Cluster ORB-stop {#1,#2,#37,#55} : 4/4 DISCARD (Gate 1).** 55ᵉ traitée, **55ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s055_narrow_range.py` (dépend de s027 + beta_bench). `ftmo_lab.py` inchangé.
