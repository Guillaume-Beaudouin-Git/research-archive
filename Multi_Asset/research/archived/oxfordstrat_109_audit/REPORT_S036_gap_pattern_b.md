# Rapport stratégie 36/109 — Gap Pattern Type B (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (1/4)** — *héritage gap-momentum (#35) ; gap plus lâche, décayé sous le beta récent + DSR.* · **Source :** https://oxfordstrat.com/trading-strategies/gap-pattern-2/ (Hill/Pruitt, rating **C**). · **Registre :** #36. · 2026-06-07.

## Spec & archétype (1 ligne)
**= #35 (Type A)** mais gap plus lâche : `Low[i] > Close[i−1]` (au lieu de `> High[i−1]`), pattern-exit au prior close. Entrée@open, filtre tendance, Time/Pattern/ATR. `ftmo_lab`+`beta_bench` inchangés. Point Filter_LB=20, Time=10.

## Résultats + chiffres décisifs (réf. Filter_LB=20, Time=10)
**5 119 trades · win 36,4 % · expR +0,0264 · PF 1,238 · Sharpe 1,02 · MaxDD −48,7 %.** Grille 100 % positive.

> **DÉLAI+1 :** +1,02 → **+1,14** ✅ (vrai, entrée@open).  **TWO-SIDED :** long **+0,040** / short **+0,007** ✅ (bilatéral).
> **BETA-MATCHED :** full +1,02 vs BH +0,74 ✓ ; **rec +0,49 vs BH +1,01 → ne bat plus le beta**.

## Gates — `results/s036_gates.csv` (1/4 FAIL)
Délai+1 ✅, Two-sided ✅, OOS ✅ (train +0,039 → test +0,013) ; **DSR FAIL** (1,02 < 1,52). edge_pos=True → **DISCARD**.

## Verdict
❌ **DISCARD (1/4).** Même histoire que le #35 (gap-momentum bilatéral réel) mais **moins efficace** (gap plus lâche → bruit), comme l'annonce la fiche, et **décayé** (rec 0,49 < beta 1,01). **Cluster gap {#35,#36} : 2/2 DISCARD** — vrai momentum bilatéral mais en fin de vie / DSR insuffisante. 36ᵉ traitée, **36ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s036_gap_pattern_b.py` (dépend de `beta_bench`). `ftmo_lab.py` inchangé.
