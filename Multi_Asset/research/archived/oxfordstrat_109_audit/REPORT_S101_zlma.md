# Rapport stratégie 101/109 — Zero Lag Moving Average Filter (Ehlers) — *trend = beta*

**Statut :** ❌ **DISCARD (2/4)** — *crossover ZLMA/EMA = trend long déguisé.* · **Source :** https://oxfordstrat.com/trading-strategies/zero-lag-moving-average/ (Ehlers/Way, rating **C**). · **Registre :** #101. · 2026-06-07.

## Spec & archétype
Système 2-phases : ZLMA (EMA dé-laggée, ZLEMA = EMA(2·Close − Close[lag])) croise au-dessus/dessous de l'EMA → long/short. Entrée @open + stop ATR. Trend-following. Réutilise `trend_lab`. Réf. Look_Back=250.

## Résultats (réf. LB=250)
**606 trades · win 37,5 % · expR +0,626 · PF 2,308 · Sharpe 0,79 · MaxDD −83,1 %.**
> **DÉLAI+1 :** +0,79 → +0,80.  **TWO-SIDED :** long **+1,38** / short **−0,15** → beta long massif (le short perd).  **DSR :** bruit.  **BETA :** rec 0,94 < BH 1,01.

## Gates — `results/s101_gates.csv` (2/4 FAIL)
MA lente dé-laggée = trend-follower long classique, ne bat pas le buy&hold (la source dit elle-même « pas mieux que la Hull MA »). Cf cluster trend #80/#46/#91/#97. 101ᵉ traitée, **101ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s101_zlma.py`. `ftmo_lab.py` inchangé.
