# Rapport stratégie 33/109 — Fractal Adaptive Moving Average (Setup) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *trend/beta (héritage cluster MA/KAMA) ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/ (J. Ehlers, rating **C**). · **Registre :** #33. · 2026-06-07.

## Spec & archétype (1 ligne)
Breakout de bande sur **MA adaptative fractale** (FRAMA, α = exp(−4,6·(D−1))) : long si Close franchit FRAMA + ATR_Band·ATR ; entrée **@open** ; sortie bande interne (0,5×) / ATR×6. Sweep `FRAMA_Length × ATR_Band`. La fiche conclut elle-même : « pas mieux que les alternatives ». `ftmo_lab`+`beta_bench` inchangés. Point Length=80, Band=3.

## Résultats + chiffres décisifs (réf. Length=80, Band=3)
**1 478 trades · win 35,9 % · expR +0,0187 · PF 1,051 · Sharpe 0,13 · MaxDD −21,0 %.**

> **DÉLAI+1 :** +0,13 → +0,08 (PASS faible).
> **TWO-SIDED :** long **+0,198** / short **−0,159** → ❌ beta long classique.
> **BETA-MATCHED :** rec **+0,27** vs buy&hold **+1,01** → ne bat pas le beta.

## Gates — `results/s033_gates.csv` (2/4)
Gate1 PASS (faible) + OOS PASS ; FAIL Gate2 (beta long) + DSR (0,32 ≪ 1,52). **DISCARD.** Encore une MA-trend = beta long. 33ᵉ traitée, **33ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s033_frama.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé.
