# Rapport stratégie 59/109 — Oops Pattern Bearish (Exits) — *court (héritage)*

**Statut :** ❌ **DISCARD net (4/4)** — *jambe short du gap-fade ; perdante.* · **Source :** https://oxfordstrat.com/trading-strategies/bear-oops-pattern/ (L. Williams, rating **D**). · **Registre :** #59. · 2026-06-07.

## Spec & archétype (1 ligne)
Jambe **short** du Oops : gap up (Open>High veille) → sell stop à High[veille]. Réutilise `s058` (side='short'). Point ATR_Index=3, Time=10.

## Résultats + chiffres décisifs (réf. ATR_Index=3, Time=10)
**4 219 trades · win 44,4 % · expR −0,0156 · PF 0,911 · Sharpe −0,47 · MaxDD −31,5 %.** (perdant)

> **DÉLAI+1 :** −0,47 → −0,59 (artefact + perdant).  OOS flip.

## Gates — `results/s059_gates.csv` (4/4 FAIL, edge_pos=False)
Le gap-up-fade short **ne marche pas** (fade une force haussière dans un marché qui dérive à la hausse = perdant). DISCARD net. Confirme l'asymétrie : seul le **long** (gap-down-fade, #60) a un edge. 59ᵉ traitée, **59ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s059_oops_bear.py` (dépend de s058). `ftmo_lab.py` inchangé.
