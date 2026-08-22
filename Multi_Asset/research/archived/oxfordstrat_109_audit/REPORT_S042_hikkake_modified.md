# Rapport stratégie 42/109 — Modified Hikkake Pattern (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (3/4)** — *= #41 (fakeout plus lâche) ; à peine mieux, toujours beta/décayé.* · **Source :** https://oxfordstrat.com/trading-strategies/modified-hikkake-pattern/ (Dan Chesler, rating **C**). · **Registre :** #42. · 2026-06-07.

## Spec & archétype (1 ligne)
**= #41** mais fakeout plus lâche : barre[i] avec simple **close plus bas** que la barre intérieure (bull) ; entrée buy stop au-dessus du **plus-haut des 2 barres**. Sweep `Trend × Time`. `ftmo_lab`+`beta_bench` inchangés. Point Trend=0, Time=20.

## Résultats + chiffres décisifs (réf. Trend=0, Time=20)
**4 082 trades · win 27,5 % · expR +0,0064 · PF 1,043 · Sharpe 0,18 · MaxDD −24,7 %.**

> **DÉLAI+1 :** +0,18 → +0,22 (PASS).  **TWO-SIDED :** long +0,037 / short −0,026 → beta.  **BETA-MATCHED :** rec −0,06 vs BH +1,01 → ne bat pas le beta.

## Gates — `results/s042_gates.csv` (3/4 FAIL)
Délai+1 ✅ ; FAIL Two-sided (beta) + DSR (0,39) + OOS (flip). À peine mieux que #41 (Sharpe 0,18 vs 0,07), conforme à la fiche (« modifications n'ajoutent pas de valeur »). **Cluster Hikkake {#41,#42} : 2/2 DISCARD.** 42ᵉ traitée, **42ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s042_hikkake_modified.py`. `ftmo_lab.py` inchangé.
