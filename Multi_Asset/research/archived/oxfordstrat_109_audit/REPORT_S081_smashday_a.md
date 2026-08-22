# Rapport stratégie 81/109 — Smash Day Pattern Type A (Filter & Exit)

**Statut :** ❌ **DISCARD (3/4)** — *reversal « jour avorté » ; pas d'edge positif après coûts.* · **Source :** https://oxfordstrat.com/trading-strategies/smash-day-pattern-a1/ (Larry Williams, rating **C**). · **Registre :** #81. · 2026-06-07.

## Spec & archétype
**Smash Day Type A (reversal de pattern avorté)** : setup long = jour qui clôture **en hausse** (Close[t]>Close[t-1]) mais **dans le quartile bas** de sa barre (Close[t] ≤ Low[t]+0,25·range) — clôture faible ; filtre tendance Close[t]>Close[t−Trend_Index]. Entrée : **buy stop au-dessus du plus-haut du jour de setup**. Short = miroir. Sorties : quick-stop (sous min(Low setup, Low entrée)), stop ATR×6, temps. Moteur `smashday.simulate_smash` + `setup_typeA`. Réf. Trend=20, Time=10.

## Résultats (réf. Trend=20, Time=10)
**1 058 trades · win 22,2 % · expR −0,0089 · PF 0,920 · Sharpe −0,18 · MaxDD −10,4 %.** (net perdant)
> **DÉLAI+1 :** natif −0,18 → open[i+1] +0,35 (*le fill optimiste « stop » est PIRE que le réaliste* : acheter au plus-haut d'un jour de reversal = mauvais prix).  **TWO-SIDED :** long +0,007 / short −0,029.  **DSR :** 0,13 ≪ 1,78 (bruit).  **OOS :** −0,003 → −0,014 (flip).  **BETA :** rec −0,15 < BH 1,01.

## Gates — `results/s081_gates.csv` (3/4 FAIL, `edge_positive=False`)
Aucun edge positif après coûts : pattern long-dominé, grille = bruit, OOS décayé. 81ᵉ traitée, **81ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s081_smashday_a.py` (dépend de `smashday` + `beta_bench`). `ftmo_lab.py` inchangé.
