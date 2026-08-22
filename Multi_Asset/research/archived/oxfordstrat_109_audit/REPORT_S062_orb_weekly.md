# Rapport stratégie 62/109 — Opening Range Breakout, Weekly Bars (Entry) — *court (héritage ORB)*

**Statut :** ❌ **DISCARD (2/4)** — *ORB sur barres hebdo ; beta long déguisé + grille = bruit.* · **Source :** https://oxfordstrat.com/trading-strategies/opening-range-breakout-weekly/ (Crabel, rating **D**). · **Registre :** #62. · 2026-06-07.

## Spec & archétype
ORB identique mais sur **barres hebdomadaires** (resample W-FRI : open=first, high=max, low=min, close=last) : buy/sell stop à [WeekOpen ± Stretch], 1er touché = position. Stretch = SMA(min(H−O,O−L), L) × M sur le bruit hebdo. Sortie : **stop ATR×6 uniquement** (ni time, ni target → tenu jusqu'au stop). Variables balayées : Stretch_Length × Stretch_Multiple. `simulate_bracket` inchangé (target=999 jamais touché, time=52 plafond 1 an). Réf. L=10, M=2.

## Résultats + chiffres décisifs (réf. L=10, M=2)
**669 trades · win 42,5 % · expR +0,1013 · PF 1,384 · Sharpe 0,52 · MaxDD −29,3 %.**

> **DÉLAI+1 :** +0,52 → **+0,11** (survit faiblement : sur barre hebdo le fill open-suivant reste proche).  **TWO-SIDED :** long **+0,379** / short **−0,165** → asymétrie totale = **beta long déguisé**.  **DSR :** 0,52 < 1,78 → **grille = bruit**.  **BETA-MATCHED :** rec 0,79 < BH 1,01 → **ne bat pas le beta**.

## Gates — `results/s062_gates.csv` (2/4 FAIL)
FAIL two-sided (le short perd, le long porte tout) + DSR (la grille Len×Mult est du bruit). Le délai+1 et l'OOS passent, mais sans edge symétrique ni significativité, et **sans battre le buy&hold**, il ne reste rien. **La fiche le dit elle-même** : *« depuis 1990, la stratégie cesse de fonctionner une fois le coût réaliste appliqué ; sans coût elle tient »* — exactement ce qu'on observe (beta long + coûts). 62ᵉ traitée, **62ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s062_orb_weekly.py` (dépend de `orb_filtered` + `beta_bench`). `ftmo_lab.py` inchangé.
