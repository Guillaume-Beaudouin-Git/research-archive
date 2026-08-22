# Rapport stratégie 98/109 — Richard Wyckoff Mean Reversion (Entry)

**Statut :** ❌ **DISCARD (4/4)** — *fade bull/bear-trap ; net perdant, ne bat pas le beta.* · **Source :** https://oxfordstrat.com/trading-strategies/richard-wyckoff-mean-reversion-1/ (Richard Wyckoff, rating **C**). · **Registre :** #98. · 2026-06-07.

## Spec & archétype
**Fade de false-breakout** (Bull/Bear Trap) : Bear-trap (long) = nouveau plus-bas sur Pattern_Size=10 barres (B) puis réaction (C) ; buy stop à Entry = B + (C−B)·Entry_Index quand le prix récupère ; annulé si nouveau plus-bas < B−(C−B)·Cancel_Index. Sorties : stop risque (Entry−range·Risk_Index), limite reward (Entry+range·Reward_Index, RR=2), stop ATR. Short = miroir. La fiche le classe explicitement « based on false breakouts » (Related = False Breakout #31/#32). Moteur `wyckoff.simulate_wyckoff`. Réf. Entry=0,5, Cancel=1.

## Résultats (réf. Entry=0,5, Cancel=1)
**11 995 trades · win 31,4 % · expR −0,0134 · PF 0,905 · Sharpe −0,89 · MaxDD −56,6 %.** (nettement perdant)
> **DÉLAI+1 :** −0,89 → −0,17.  **TWO-SIDED :** long +0,015 / short −0,036.  **BETA :** rec **−1,05** < BH 1,01. Grille `results/s098_sensitivity_expectancy.csv` négative partout.

## Gates — `results/s098_gates.csv` (4/4 FAIL, `edge_positive=False`)
Le fade de false-breakout Wyckoff **perd nettement** sur l'univers FTMO — cohérent avec **toute la famille fade** déjà écartée : False Breakout (#31/#32), Turtle Soup (#89/#90), Reversal Patterns (#74/#75). 98ᵉ traitée, **98ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s098_wyckoff.py` (dépend de `wyckoff` + `beta_bench`). `ftmo_lab.py` inchangé.
