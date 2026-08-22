# Rapport stratégie 29/109 — Bullish Engulfing Type A (Exits) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *pattern plus strict ; marginalement positif mais beta long + DSR bruit.* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-bullish-engulfing-a/ (rating **D**). · **Registre :** #29. · 2026-06-06.

## Spec & archétype (1 ligne)
Bullish engulfing **Type A** = base + `High[t]>High[t−1]` & `Low[t]<Low[t−1]` (englobe toute la **range**, pas que le corps). Entrée ORB-up, sorties Stretch/Target/Time/ATR. Réutilise `s027` (`eng_bull_A`, long). Point Target=3, Time=10.

## Résultats + chiffres décisifs (réf. Target=3, Time=10)
**710 trades · win 30,8 % · expR +0,0513 · PF 1,073 · Sharpe 0,16 · MaxDD −24,2 %.**

> **DÉLAI+1 :** natif +0,16 (expR +0,051) → réel **+0,32** (expR +0,109) → PASS (robuste, l'entrée ORB n'est pas un artefact ici).
> **PURE-PATTERN 10 j : +0,41 %** — ≈ beta de marché.

## Gates — `results/s029_gates.csv` (2/4 FAIL)
Gate1 PASS + OOS — mais **FAIL Gate2 (beta long : que des longs) + DSR (Sharpe 0,16 ≪ 1,52)**. Le pattern plus strict (range engulfing) améliore l'expR mais reste **du beta long faible et non significatif**. 29ᵉ traitée, **29ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s029_engulfing_bull_a.py` (dépend de s027). `ftmo_lab.py` inchangé. Code : `code/strat_s029_engulfing_bull_a.py`.
