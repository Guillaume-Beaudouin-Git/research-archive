# Rapport stratégie 53/109 — MACD Part 2 (Entry) — *court (héritage trend)*

**Statut :** ❌ **DISCARD (2/4)** — *= #52 + ligne signal ; pire que Part 1 (comme l'annonce la fiche) ; beta long.* · **Source :** https://oxfordstrat.com/trading-strategies/macd-part-2/ (Gerald Appel, rating **D**). · **Registre :** #53. · 2026-06-07.

## Spec & archétype (1 ligne)
Long si MACD>0 **et** MACD>Signal(EMA9 du MACD) ; sortie quand MACD<Signal ; entrée@open + ATR×6. Réutilise `trend_lab`. Point EMA1=40/EMA2=80/Signal=9.

## Résultats + chiffres décisifs (réf. EMA1=40/EMA2=80)
**3 433 trades · win 33,5 % · expR +0,0251 · PF 1,123 · Sharpe 0,37 · MaxDD −38,5 %.** (Sharpe 0,37 < 0,53 du #52, conforme à la fiche)

> **DÉLAI+1 :** +0,37 → +0,26 (PASS).  **TWO-SIDED :** long **+0,089** / short **−0,061** → beta long.  **BETA-MATCHED :** rec 0,60 < BH 1,01.

## Gates — `results/s053_gates.csv` (2/4)
FAIL Gate2 (beta long) + DSR (0,46). La ligne signal sur-trade et n'ajoute rien (pire que #52). **Cluster MACD {#52,#53} : 2/2 DISCARD.** 53ᵉ traitée, **53ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s053_macd2.py` (dépend de trend_lab + beta_bench). `ftmo_lab.py` inchangé.
