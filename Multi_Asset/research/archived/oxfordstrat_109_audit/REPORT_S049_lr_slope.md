# Rapport stratégie 49/109 — Linear Regression Slope (Filter & Entry) — *court (héritage trend)*

**Statut :** ❌ **DISCARD (2/4)** — *double-pente de régression = beta long ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/linear-regression/ (Kaufman, rating **C**). · **Registre :** #49. · 2026-06-07.

## Spec & archétype (1 ligne)
Long quand LRS_1 (pente sur Look_Back) **et** LRS_2 (pente sur Look_Back×Index) > 0 ; entrée@open ; sortie quand condition off / ATR×6. Réutilise `trend_lab` (pente vectorisée). Point Look_Back=100, Index=0,5.

## Résultats + chiffres décisifs (réf. LB=100, Index=0,5)
**2 037 trades · win 36,2 % · expR +0,0528 · PF 1,176 · Sharpe 0,38 · MaxDD −47,5 %.**

> **DÉLAI+1 :** +0,38 → +0,37 (PASS).  **TWO-SIDED :** long **+0,207** / short **−0,129** → beta long.  **BETA-MATCHED :** rec 0,31 < BH 1,01.

## Gates — `results/s049_gates.csv` (2/4)
Délai+1 ✅ + OOS ✅ ; FAIL Gate2 (beta long) + DSR (0,60). Pente de régression positive = être long la tendance = beta. 49ᵉ traitée, **49ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s049_lr_slope.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
