# Rapport stratégie 91/109 — Volatility Squeeze (Bollinger) — *trend = beta*

**Statut :** ❌ **DISCARD (2/4)** — *le filtre squeeze n'ajoute rien (dixit la source) ; la base Bollinger-trend = beta long.* · **Source :** https://oxfordstrat.com/trading-strategies/volatility-squeeze/ (John Bollinger, rating **C**). · **Registre :** #91. · 2026-06-07.

## Spec & archétype
Breakout de bande de Bollinger (MA=80, ±2σ) : long quand Close>UpperBand, sortie quand Close<MA (+ stop ATR×6) ; short miroir. Le **filtre squeeze** (ne trader que quand BandWidth est à son minimum sur Squeeze_LookBack) ne fait que restreindre les trades. La fiche conclut explicitement : *« le filtre squeeze n'améliore PAS le modèle trend de base »* (LookBack=0/Memory=1000 = toutes les entrées). Donc on teste la **base Bollinger-trend**. Réutilise `trend_lab` (régime de bande). Réf. MA=80, σ=2.

## Résultats (réf. MA=80, σ=2)
**1 466 trades · win 32,2 % · expR +0,045 · PF 1,134 · Sharpe 0,27 · MaxDD −32,7 %.**
> **DÉLAI+1 :** +0,27 → +0,27 (entrée @open).  **TWO-SIDED :** long **+0,217** / short **−0,146** → beta long (le short perd).  **DSR :** grille = bruit.  **BETA :** rec 0,14 < BH 1,01.

## Gates — `results/s091_gates.csv` (2/4 FAIL)
Trend-following Bollinger = beta long déguisé, ne bat pas le buy&hold (cohérent avec #14 Bollinger Momentum). Le squeeze n'y change rien. 91ᵉ traitée, **91ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s091_vol_squeeze.py` (dépend de `trend_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
