# Rapport stratégie 90/109 — Turtle Soup (Setup & Exit 2) — *court (variante #89)*

**Statut :** ❌ **DISCARD (3/4)** — *2ᵉ étude de sortie (canal rapide) ; même verdict que #89.* · **Source :** https://oxfordstrat.com/trading-strategies/turtle-soup-plus-2/ (Connors/Raschke, rating **D**). · **Registre :** #90. · 2026-06-07.

## Spec & résultats
= #89 avec sortie canal plus rapide (Channel_#2=5). **1 899 trades · win 14,8 % · expR −0,0063 · Sharpe −0,17 · MaxDD −15,6 %.** DÉLAI+1 −0,17→+0,76 (artefact inverse de fill). TWO-SIDED long +0,004 / short −0,014. BETA rec 0,01 < BH 1,01. **Gates 3/4 FAIL (`edge_positive=False`).** Accélérer la sortie ne sauve pas le fade. Cluster Turtle Soup {#89,#90} = 2/2 DISCARD ; avec False Breakout {#31,#32}, le fade de cassure 20j est **4/4 DISCARD** sur l'univers FTMO. 90ᵉ traitée, **90ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s090_turtle_soup2.py`. `ftmo_lab.py` inchangé.
