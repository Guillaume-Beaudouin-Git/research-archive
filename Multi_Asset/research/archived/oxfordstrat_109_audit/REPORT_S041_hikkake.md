# Rapport stratégie 41/109 — Hikkake Pattern (Filter & Exit)

**Statut :** ❌ **DISCARD (3/4)** — *trap inside-bar fakeout ; net ≈ nul, beta-tilt, décayé OOS ; ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/hikkake-pattern/ (Dan Chesler, rating **C**). · **Registre :** #41. · 2026-06-07.

## Spec & archétype
**Inside-bar « false breakout »** (deux barres) : barre intérieure puis fausse cassure ; entrée **buy stop au-dessus du haut de la barre intérieure** (bull) quand le prix reprend, dans les 3 barres. Two-sided (fade le fakeout). Filtre tendance (redondant selon la fiche), sortie Time + Pattern + ATR×6. Sweep `Trend_Index × Time`. `ftmo_lab`+`beta_bench` inchangés. Point Trend=0, Time=20.

## Résultats + chiffres décisifs (réf. Trend=0, Time=20)
**3 525 trades · win 27,1 % · expR +0,0025 · PF 1,017 · Sharpe 0,07 · MaxDD −15,0 %.** (≈ nul)

> **DÉLAI+1 :** +0,07 → +0,07 (PASS — l'entrée-stop n'est pas un artefact ici).  **TWO-SIDED :** long **+0,037** / short **−0,031** → beta.
> **BETA-MATCHED :** rec **−0,40** vs BH +1,01 → ne bat pas le beta.

## Gates — `results/s041_gates.csv` (3/4 FAIL)
Délai+1 ✅ ; FAIL Two-sided (beta long), DSR (0,32), OOS (flip +0,022→−0,014). expR ≈ 0. **DISCARD.** Le fakeout inside-bar ne produit pas d'edge net. 41ᵉ traitée, **41ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s041_hikkake.py` (dépend de beta_bench). `ftmo_lab.py` inchangé.
