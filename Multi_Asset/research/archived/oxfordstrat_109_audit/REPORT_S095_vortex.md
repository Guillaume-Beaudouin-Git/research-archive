# Rapport stratégie 95/109 — Vortex Indicator (Entry) — *trend = beta*

**Statut :** ❌ **DISCARD (2/4)** — *crossover VI+/VI− = momentum/trend long déguisé.* · **Source :** https://oxfordstrat.com/trading-strategies/vortex-indicator-1/ (rating **C**). · **Registre :** #95. · 2026-06-07.

## Spec & archétype
Vortex : VI+ = Σ|High−Low_veille| / Σ TR ; VI− = Σ|Low−High_veille| / Σ TR (sur N). Long quand VI+>VI−, short quand VI−>VI+. Entrée @open, sortie sur flip + stop ATR. Trend/momentum bidirectionnel. Réutilise `trend_lab`. Réf. N=14.

## Résultats (réf. N=14)
**10 384 trades · win 37,1 % · expR +0,0035 · PF 1,025 · Sharpe 0,15 · MaxDD −23,4 %.**
> **DÉLAI+1 :** +0,15 → +0,04 (entrée @open ; léger).  **TWO-SIDED :** long **+0,038** / short **−0,032** → beta long (le short perd).  **DSR :** grille = bruit.  **BETA :** rec 0,67 < BH 1,01.

## Gates — `results/s095_gates.csv` (2/4 FAIL)
Le Vortex est un indicateur de tendance : tout le PnL vient du long, le short perd, et il ne bat pas le buy&hold (cohérent avec le cluster trend/momentum : #69, #80, #87, et #26 Vortex+Dual-Momentum). 95ᵉ traitée, **95ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s095_vortex.py` (dépend de `trend_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
