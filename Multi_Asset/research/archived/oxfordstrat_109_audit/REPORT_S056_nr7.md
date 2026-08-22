# Rapport stratégie 56/109 — NR7 Pattern (Setup & Exit) — *court (héritage ORB-stop)*

**Statut :** ❌ **DISCARD (3/4)** — *NR7 Crabel + ORB-stop = artefact de fill.* · **Source :** https://oxfordstrat.com/trading-strategies/nr7/ (Toby Crabel, rating **C**). · **Registre :** #56. · 2026-06-07.

## Spec & archétype (1 ligne)
NR7 (range du jour < chacun des NR_Length=6 jours précédents) + **entrée ORB-stop Crabel** (Open ± Stretch) ; sorties Time(N)+Stretch+ATR. Réutilise `simulate_bracket` + Crabel stretch. Point NR_Length=6, N=10.

## Résultats + chiffres décisifs (réf. NR_Length=6, N=10)
**7 504 trades · win 43,9 % · expR +0,0060 · PF 1,043 · Sharpe 0,26 · MaxDD −26,1 %.**

> **DÉLAI+1 :** natif +0,26 → réel **−0,98** → ❌ artefact de fill intrabar.  **BETA-MATCHED :** rec −0,11 < BH 1,01.

## Gates — `results/s056_gates.csv` (3/4 FAIL)
Two-sided ~PASS (long +0,044/short +0,003, mais minuscule) ; FAIL délai+1 (artefact) + DSR + OOS flip. La fiche elle-même : *« non tradeable une fois les coûts appliqués »*. **Cluster ORB-stop/NR {#1,#2,#37,#55,#56} : 5/5 DISCARD.** 56ᵉ traitée, **56ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s056_nr7.py` (dépend de s027 + beta_bench). `ftmo_lab.py` inchangé.
