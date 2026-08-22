# Rapport stratégie 73/109 — RSI(2) Model, New Exits (Connors) — *court (jumeau de #72)*

**Statut :** ❌ **DISCARD (= #72, décayé)** — *même entrée RSI2, sortie RSI au lieu de MA ; performance et décroissance identiques.* · **Source :** https://oxfordstrat.com/trading-strategies/relative-strength-index-2/ (Connors, rating **C**). · **Registre :** #73. · 2026-06-07.

## Spec & archétype
Identique à #72 (Close>SMA200 & RSI2<Entry_Threshold, achat next open) **sauf la sortie** : RSI-exit (vente @open si `RSI(2)[i-1] > Exit_Threshold`, défaut 95) + stop ATR. Balayage Entry_Threshold × Exit_Threshold. Réf. entry=10, exit=75.

## Résultats (réf. entry=10, exit=75)
**1 613 trades · win 74,0 % · expR +0,057 · Sharpe(trade) 1,32 · MaxDD −34,7 %.**
> **DÉLAI+1 :** +1,32 → +1,34 (survit). **DSR :** 1,567 > 1,519 PASS. **OOS :** +0,060 → +0,053 PASS. **beta_line** : « BEATS beta » (rec 1,22 vs 0,93) — *mais c'est le même artefact trade-Sharpe vs daily-Sharpe que #60*.

## Test décisif (mark-to-market) — identique à #72
La fiche le dit : *« la sortie RSI n'est ni significativement meilleure ni pire que la sortie MA (#72) »*. Confirmé : **MTM Sharpe 0,69, alpha couvert-beta +1,18 %/an, t_NW +2,65, Sharpe couvert 0,52** — *exactement les mêmes chiffres que #72*. Donc **même décroissance** : significatif 2000-2009, **mort 2019-2026** (cf. table dans `REPORT_S072_rsi2.md`).

## Gates — `results/s073_gates.csv` (1/4)
FAIL two-sided seulement (long-only par construction). Mais comme #72, l'**edge récent est nul** → non déployable. Le changement de sortie (RSI vs MA) ne change rien. 73ᵉ traitée, **73ᵉ DISCARD**. Cluster RSI2 {#72,#73} = 2/2 DISCARD (MR authentique mais arbitrée).

## Repro
`cd oxfordstrat_109/code && python strat_s073_rsi2_exits.py`. `ftmo_lab.py` inchangé.
