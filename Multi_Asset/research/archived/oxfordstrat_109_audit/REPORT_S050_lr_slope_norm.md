# Rapport stratégie 50/109 — Normalized Linear Regression Slope (Entry) — *court (héritage trend)*

**Statut :** ❌ **DISCARD (2/4)** — *= #49 normalisé par l'ATR ; meilleur Sharpe du lot mais toujours beta long, ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/normalized-linear-regression/ (Kaufman, rating **C**). · **Registre :** #50. · 2026-06-07.

## Spec & archétype (1 ligne)
**NLRS = LRS(Look_Back) / ATR(20)** ; long quand NLRS>Growth_Index, sortie quand NLRS<0 (+ ATR×6). Entrée@open. Réutilise `trend_lab`. Point Look_Back=100, Growth=0,025.

## Résultats + chiffres décisifs (réf. LB=100, Growth=0,025)
**1 313 trades · win 36,6 % · expR +0,1384 · PF 1,344 · Sharpe 0,57 · MaxDD −63,7 %.**

> **DÉLAI+1 :** +0,57 → +0,55 (PASS).  **TWO-SIDED :** long **+0,430** / short **−0,172** → beta long.  **BETA-MATCHED :** full 0,57 < 0,74 ; **rec 0,49 < BH 1,01**.

## Gates — `results/s050_gates.csv` (2/4)
Délai+1 ✅ + OOS ✅ (+0,176→+0,108) ; FAIL Gate2 (beta long) + DSR (0,68). La normalisation par vol améliore le Sharpe (0,57, le meilleur du lot) mais **ne change pas la nature beta long** ni ne bat le buy&hold ; MaxDD −64 %. **Cluster LR-slope {#49,#50} : 2/2 DISCARD.** 50ᵉ traitée, **50ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s050_lr_slope_norm.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
