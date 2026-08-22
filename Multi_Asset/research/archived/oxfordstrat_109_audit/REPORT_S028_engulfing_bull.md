# Rapport stratégie 28/109 — Bullish Engulfing Candlestick (Exits) — *court (héritage)*

**Statut :** ❌ **DISCARD net (edge_pos=False)** — *jambe long de l'archétype Engulfing (#27) ; ~nul, l'entrée ORB nuit.* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-bullish-engulfing/ (rating **D**). · **Registre :** #28. · 2026-06-06.

## Spec & archétype (1 ligne)
Bullish engulfing (O[y]>C[y] & O[t]<C[y] & C[t]>O[y]) + **entrée ORB-up** (buy stop Open+Stretch), sorties Stretch/Target/Time/ATR. Réutilise `s027.simulate_engulf` (long). Point Target=3, Time=10.

## Résultats + chiffres décisifs (réf. Target=3, Time=10)
**2 083 trades · win 29,1 % · expR −0,0031 · PF 0,996 · Sharpe −0,02 · MaxDD −49,5 %** (quasi nul, légèrement négatif).

> **DÉLAI+1 :** natif −0,02 (expR −0,0031) → fill réaliste open[i+1] **+0,49** (expR +0,097). **→ l'entrée ORB-up de la spec NUIT : entrer à l'open suivant (sans courir après le breakout) serait meilleur.**
> **PURE-PATTERN 10 j (sans ORB) : +0,37 %** — ≈ beta de marché, pas un alpha de reversal.

## Gates — `results/s028_gates.csv`
`edge_pos=False` (expR −0,003 < 0) → **DISCARD net (3/4 FAIL).** Le bullish engulfing + ORB-up est **breakeven-négatif** : le pattern n'apporte pas de bounce exploitable, et l'entrée momentum (ORB-up) achète le haut. 28ᵉ traitée, **28ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s028_engulfing_bull.py` (dépend de s027). `ftmo_lab.py` inchangé. Code : `code/strat_s028_engulfing_bull.py`.
