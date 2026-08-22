# Rapport stratégie 97/109 — Wilder Volatility Breakout — *trend = beta*

**Statut :** ❌ **DISCARD (2/4)** — *système volatilité stop-and-reverse = trend long déguisé.* · **Source :** https://oxfordstrat.com/trading-strategies/welles-wilder-1/ (J. Welles Wilder, rating **C**). · **Registre :** #97. · 2026-06-07.

## Spec & archétype
Volatility System de Wilder (2-phase stop-and-reverse) : SIC = meilleur close en position ; SAR = SIC ∓ ATR×Constant ; on retourne long quand close > SAR (depuis short), short quand close < SAR. Toujours en position. Entrée @open + stop ATR. Trend-following. Réutilise `trend_lab` (régime persistant). Réf. Constant=3, LookBack=14.

## Résultats (réf. K=3, LB=14)
**4 942 trades · win 36,2 % · expR +0,014 · PF 1,062 · Sharpe 0,26 · MaxDD −39,4 %.**
> **DÉLAI+1 :** +0,26 → +0,28 (entrée @open).  **TWO-SIDED :** long **+0,099** / short **−0,071** → beta long (le short perd).  **DSR :** bruit.  **BETA :** rec 0,37 < BH 1,01.

## Gates — `results/s097_gates.csv` (2/4 FAIL)
Trend-follower par stop de volatilité = beta long déguisé, ne bat pas le buy&hold (cohérent avec le cluster trend #69/#80/#87/#91/#95). 97ᵉ traitée, **97ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s097_wilder_vol.py`. `ftmo_lab.py` inchangé.
