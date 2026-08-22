# Rapport stratégie 104/109 — TD Setup-Trend (DeMark) — *momentum = beta*

**Statut :** ❌ **DISCARD (3/4)** — *9-setup utilisé en continuation de tendance ; ~zéro edge, beta long.* · **Source :** https://oxfordstrat.com/indicators/td-setup-trend/ (DeMark, **Ind**, rating N/A). · **Registre :** #104. · 2026-06-07.

## Spec & archétype
Inverse du TD reversal : on trade **dans le sens** d'un setup complété (9 clôtures consécutives Close>Close[−4] → long ; miroir short). Entrée à la clôture de complétion, sortie temporelle + stop ATR. Momentum/continuation. Réf. Setup=9, Time=10.

## Résultats (réf. Setup=9, Time=10)
**3 635 trades · win 50,3 % · expR +0,0015 · PF 1,009 · Sharpe 0,04 · MaxDD −17,0 %.** (~plat)
> **DÉLAI+1 :** +0,04 → +0,15.  **TWO-SIDED :** long +0,021 / short −0,027 → beta long.  **BETA :** rec −0,09 < BH 1,01.

## Gates — `results/s104_gates.csv` (3/4 FAIL)
Espérance ~nulle, long-dominé, grille bruit, OOS flip. Le 9-setup en momentum ne crée pas d'edge net. 104ᵉ traitée, **104ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s104_td_setup_trend.py`. `ftmo_lab.py` inchangé.
