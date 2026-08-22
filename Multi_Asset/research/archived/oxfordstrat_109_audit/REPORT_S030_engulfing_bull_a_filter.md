# Rapport stratégie 30/109 — Bullish Engulfing Type A (Filter & Exit) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *variante la plus MR (dip-filter) ; expR brut le plus élevé du cluster MAIS fine, peu robuste (DSR), unidirectionnelle (beta long). Clôt le cluster Engulfing.* · **Source :** https://oxfordstrat.com/trading-strategies/pattern-bullish-engulfing-b/ (rating **D**). · **Registre :** #30. · 2026-06-06.

## Spec & archétype (1 ligne)
Type A bullish engulfing **+ filtre contre-tendance** : n'accepter le pattern que si `Close[setup] < MA(Close, MA_Length)` (« bearish mode » = achat sur repli). Entrée ORB-up, sorties Stretch/Time/ATR (pas de Target). Réutilise `s027` (`eng_bull_A` + filtre MA). Sweep `MA_Length × Time`. Point MA=50, Time=10.

## Résultats + chiffres décisifs (réf. MA=50, Time=10)
**255 trades · win 29,0 % · expR +0,5089 · PF 1,713 · Sharpe 0,25 · MaxDD −43,9 %.**

> **DÉLAI+1 :** natif +0,25 (expR +0,509) → réel **+0,31** (expR +0,897) → PASS.
> **PURE-PATTERN 10 j (dip-filtré) : +0,51 %** — légèrement > les variantes non filtrées, mais reste ≈ beta de repli.

## Gates — `results/s030_gates.csv` (2/4 FAIL)
Gate1 PASS + OOS PASS — mais **FAIL Gate2 (beta long unidirectionnel) + DSR (Sharpe 0,25 ≪ 1,52)**.

## Verdict — ne pas se laisser éblouir par l'expR
❌ **DISCARD (2/4).** Le filtre dip donne l'expR brut **le plus élevé du cluster (+0,51, PF 1,71)** — mais c'est un **mirage de robustesse** : seulement **255 trades**, **Sharpe 0,25**, DSR catastrophique, et **strictement long** (beta de repli, pas un edge bilatéral). Rien à voir avec un vrai alpha MR (cf. Bollinger %b #12 qui, lui, avait un alpha *bilatéral* à Sharpe élevé). Conformément à la discipline : **expR élevé ≠ KEEP**. 30ᵉ traitée, **30ᵉ DISCARD**.

**Cluster Engulfing {#27,#28,#29,#30} : 4/4 DISCARD.** *Bilan bougies : Doji (4/4) + Engulfing (4/4) = 8/8 DISCARD — les patterns de bougie ne portent pas d'edge exploitable sur cet univers.*

## Repro
`cd oxfordstrat_109/code && python strat_s030_engulfing_bull_a_filter.py` (dépend de s027). `ftmo_lab.py` inchangé. Code : `code/strat_s030_engulfing_bull_a_filter.py`.
