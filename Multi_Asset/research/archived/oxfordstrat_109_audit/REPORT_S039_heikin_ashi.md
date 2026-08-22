# Rapport stratégie 39/109 — Heikin-Ashi Technique (Setup & Exit) — *court (nouvel indicateur, trend)*

**Statut :** ❌ **DISCARD net (3/4, edge_pos=False)** — *suivi de tendance sur bougies lissées ; ~nul, beta long.* · **Source :** https://oxfordstrat.com/trading-strategies/heikin-ashi-1/ (rating **C**). · **Registre :** #39. · 2026-06-07.

## Spec & archétype (1 ligne)
**Trend-following sur bougies Heikin-Ashi** (OHLC lissé puis HA). Setup long = HA verte (HaClose>HaOpen) ; entrée @open ; sortie Time + ATR×6. Sweep `Look_Back × Time`. `ftmo_lab`+`beta_bench` inchangés. Point Look_Back=1 (HA standard), Time=10.

## Résultats + chiffres décisifs (réf. Look_Back=1, Time=10)
**11 518 trades · win 49,5 % · expR −0,0010 · PF 0,994 · Sharpe −0,05 · MaxDD −33,1 %.** Grille 44 % positive (≈ nul).

> **TWO-SIDED :** long **+0,0288** / short **−0,0361** → beta long (le HA-vert = être long la tendance).  **BETA-MATCHED :** rec +0,05 vs BH +1,01 → ne bat pas le beta.

## Gates — `results/s039_gates.csv` (edge_pos=False → DISCARD net)
Délai+1 PASS ; FAIL Two-sided (beta) + DSR + OOS (flip). expR ≈ 0 → pas d'edge. La bougie HA, malgré le lissage, ne fait que suivre la tendance = beta long, sans alpha. 39ᵉ traitée, **39ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s039_heikin_ashi.py` (dépend de beta_bench). `ftmo_lab.py` inchangé.
