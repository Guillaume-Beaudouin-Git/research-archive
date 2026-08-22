# Rapport stratégie 47/109 — Keltner Channels 2-Phase Model (Setup) — *court (héritage trend)*

**Statut :** ❌ **DISCARD net (4/4)** — *breakout de canal Keltner (always-in) ; net perdant, beta.* · **Source :** https://oxfordstrat.com/trading-strategies/keltner-channels/ (Chester Keltner, rating **C**). · **Registre :** #47. · 2026-06-07.

## Spec & archétype (1 ligne)
Trend breakout : long quand Close franchit `Buy_Line = MA(TypPrice) + MA(Range)×Mult` ; always-in 2-phase (reversal long/short) ; entrée@open + ATR×6. Réutilise `trend_lab` (régime persistant). Point Look_Back=10, Range_Mult=1.

## Résultats + chiffres décisifs (réf. LB=10, RM=1)
**8 448 trades · win 35,2 % · expR −0,0069 · PF 0,961 · Sharpe −0,23 · MaxDD −40,8 %.** (net perdant)

> **TWO-SIDED :** long +0,038 / short −0,052 → beta.  **DÉLAI+1 :** −0,23 → −0,15 (négatif).  **BETA-MATCHED :** rec −0,06 < BH 1,01.

## Gates — `results/s047_gates.csv` (4/4 FAIL, edge_pos=False)
Net négatif → DISCARD net. Le breakout de canal Keltner sur-trade (8 448 trades, LB=10 court) et perd net. 47ᵉ traitée, **47ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s047_keltner_2phase.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
