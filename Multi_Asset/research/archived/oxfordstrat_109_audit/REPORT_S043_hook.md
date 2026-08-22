# Rapport stratégie 43/109 — Hook Pattern (Exits)

**Statut :** ❌ **DISCARD (1/4)** — *Hook + ORB-stop Crabel ; two-sided+ & OOS+ mais le fill porte l'edge et ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-hook/ (Toby Crabel, rating **D**). · **Registre :** #43. · 2026-06-07.

## Spec & archétype
**Hook** (Crabel) : long = ouvre au-dessus du plus-haut veille, clôture sous la clôture veille, range qui se resserre (gap-up avorté). Entrée **ORB-stop Crabel** (Open ± Stretch) le lendemain. Réutilise `s027.simulate_engulf` (Crabel-ORB directionnel) + `crabel_stretch`. Two-sided (long+short hooks). Sorties Target/Time/ATR. Point Target=3, Time=10.

## Résultats + chiffres décisifs (réf. Target=3, Time=10)
**1 083 trades · win 30,0 % · expR +0,0915 · PF 1,126 · Sharpe 0,33 · MaxDD −38,0 %.**

> **DÉLAI+1 :** natif +0,33 → réel **+0,03** (expR +0,092 → +0,010) — l'ORB-stop porte l'essentiel (quasi-artefact).
> **TWO-SIDED :** long **+0,105** / short **+0,074** → ✅ bilatéral.  **BETA-MATCHED :** rec +0,57 vs BH +1,01 → ne bat pas le beta.

## Gates — `results/s043_gates.csv` (1/4 FAIL)
Délai+1 ✅(faible) + Two-sided ✅ + OOS ✅ (+0,118→+0,055) ; **DSR FAIL** (0,56<1,52). edge_pos=True → **DISCARD.** Le Hook a un edge bilatéral réel mais (a) presque tout vient du fill ORB (délai+1 +0,33→+0,03), (b) ne bat pas le beta, (c) DSR insuffisante. 43ᵉ traitée, **43ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s043_hook.py` (dépend de s027 + beta_bench). `ftmo_lab.py` inchangé.
