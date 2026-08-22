# Rapport stratégie 83/109 — Smash Day Pattern Type B (Filter & Exit) — *rating B non confirmé*

**Statut :** ❌ **DISCARD (3/4)** — *le « smash » de Williams ; rating B à la source mais beta long + grille bruit + OOS décayé sur l'univers FTMO.* · **Source :** https://oxfordstrat.com/trading-strategies/smash-day-pattern-b1/ (Larry Williams, rating **B**). · **Registre :** #83. · 2026-06-07.

## Spec & archétype
**Smash Day Type B** : setup long = un jour qui **clôture sous le plus-bas de la veille** (Close[t] < Low[t−1]) — le « smash » baissier ; filtre Close[t]>Close[t−Trend_Index]. Entrée : **buy stop au-dessus du plus-haut du jour smash** (pari sur l'échec du smash = reversal). Short = miroir (Close[t]>High[t−1]). Sorties quick/ATR/temps. `setup_typeB`. Réf. Trend=20, Time=10.

## Résultats (réf. Trend=20, Time=10)
**6 712 trades · win 25,1 % · expR +0,000 · PF 1,000 · Sharpe 0,00 · MaxDD −31,5 %.**
> **DÉLAI+1 :** natif **0,00** → open[i+1] **+1,15** — ⚠️ le fill optimiste est *pire* que le réaliste : drapeau de fragilité (l'« edge » dépend du timing de fill, pas d'un signal robuste).  **TWO-SIDED :** long +0,011 / short −0,013 → **beta long déguisé**.  **DSR :** 0,13 ≪ 1,78 (bruit).  **OOS :** +0,002 → −0,002 (flip).  **BETA :** rec 0,01 < BH 1,01.

## Gates — `results/s083_gates.csv` (3/4 FAIL)
**Le rating B de la source ne se traduit pas** sur l'univers FTMO (la source teste 42 futures incl. taux, 1980-2011). Ici : long-dominé, grille non significative, OOS décayé, ne bat pas le beta. Le +1,15 en délai+1 (vs 0,00 natif) n'est pas un edge robuste — c'est l'artefact inverse (le stop intrabar achète le plus-haut d'un jour volatil de reversal = pire prix). 83ᵉ traitée, **83ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s083_smashday_b.py`. `ftmo_lab.py` inchangé.
