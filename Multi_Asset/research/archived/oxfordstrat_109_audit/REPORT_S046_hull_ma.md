# Rapport stratégie 46/109 — Hull Moving Average Filter (Entry & Exit) — *court (héritage trend)*

**Statut :** ❌ **DISCARD (2/4)** — *dual-HMA slope = beta long ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/hull-moving-average/ (Alan Hull, rating **C**). · **Registre :** #46. · 2026-06-07.

## Spec & archétype (1 ligne)
Long quand Slow_HMA **et** Fast_HMA montent (pente>0) ; entrée @open ; sortie quand une HMA retourne / ATR×6. HMA = MA à lag réduit (WMA(2·WMA(n/2)−WMA(n), √n)). Réutilise `trend_lab` ; `ftmo_lab`+`beta_bench` inchangés. Point Slow=250, Fast_Index=1.

## Résultats + chiffres décisifs (réf. Slow=250, Fast_Index=1)
**1 970 trades · win 28,7 % · expR +0,0458 · PF 1,131 · Sharpe 0,26 · MaxDD −40,9 %.**

> **DÉLAI+1 :** +0,26 → +0,26 (PASS, entrée@open robuste).  **TWO-SIDED :** long **+0,251** / short **−0,166** → beta long.  **BETA-MATCHED :** rec 0,27 < BH 1,01.

## Gates — `results/s046_gates.csv` (2/4)
Délai+1 ✅ + OOS ✅ ; FAIL Gate2 (beta long) + DSR (0,60). Encore une MA-trend = beta long, plus lent ≠ meilleur. 46ᵉ traitée, **46ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s046_hull_ma.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
