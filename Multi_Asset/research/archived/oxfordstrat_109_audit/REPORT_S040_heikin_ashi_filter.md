# Rapport stratégie 40/109 — Heikin-Ashi Technique (Setup & Filter) — *court (héritage)*

**Statut :** ❌ **DISCARD net (4/4)** — *= #39 HA + filtres corps/tendance ; net perdant, clôt le cluster HA.* · **Source :** https://oxfordstrat.com/trading-strategies/heikin-ashi-2/ (rating **D**). · **Registre :** #40. · 2026-06-07.

## Spec & archétype (1 ligne)
**HA + filtre de corps** (faible ombre opposée : `HaOpen−HaLow ≤ (HaHigh−HaLow)×Body_Index`) **+ filtre de tendance** (`Close[i−1]>Close[i−1−Trend_Index]`). Entrée @open ; sortie **flip HA** @open + ATR×6. Sweep `Body_Index × Trend_Index`. `ftmo_lab`+`beta_bench` inchangés. Point Body=0,1, Trend=20.

## Résultats + chiffres décisifs (réf. Body=0,1, Trend=20)
**16 664 trades · win 37,9 % · expR −0,0019 · PF 0,980 · Sharpe −0,16 · MaxDD −27,9 %.** Grille **0 % positive**.

> **DÉLAI+1 :** −0,16 → −0,44 ❌.  **TWO-SIDED :** long +0,010 / short −0,016 (beta).  **BETA-MATCHED :** rec +0,08 vs BH +1,01 → ne bat pas le beta.

## Gates — `results/s040_gates.csv` (4/4 FAIL, edge_pos=False)
Les 4 gates échouent ; net perdant. Les filtres corps/tendance n'ajoutent rien à la HA. **Cluster Heikin-Ashi {#39, #40} : 2/2 DISCARD.** 40ᵉ traitée, **40ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s040_heikin_ashi_filter.py` (dépend de beta_bench). `ftmo_lab.py` inchangé.
