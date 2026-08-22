# Rapport stratégie 92/109 — Volume Filters Part 1 — *base = breakout beta ; volume non reproductible*

**Statut :** ❌ **DISCARD (2/4) + filtre volume non reproductible FTMO** — *base price-breakout = beta long ; la source montre que le filtre volume n'aide pas.* · **Source :** https://oxfordstrat.com/trading-strategies/volume-filters-1/ (Edwards/Magee + Donchian, rating **C**). · **Registre :** #92. · 2026-06-07.

## Spec & archétype
Breakout de canal de prix (Donchian) **confirmé par un breakout de volume** (UpVolume > plus-haut volume canal). Sortie : canal opposé + stop ATR.

**Deux problèmes :**
1. **Volume non disponible** : les CFD FTMO n'ont pas de volume centralisé ; le store est OHLC+spread (le tick_volume M1 n'existe que pour ~6 instruments, pas l'univers). Le filtre volume n'est **pas reproductible** fidèlement.
2. **La source elle-même** (Table 2 vs 3) montre que le filtre volume **dégrade** le résultat : Sharpe 0,95 (volume OFF) → 0,81 (volume ON). *« Volume filters do not improve simple price breakouts. »*

## Test de la base FTMO-tradable (price breakout, volume OFF)
**981 trades · expR +0,197 · PF 1,405 · Sharpe 0,46 · MaxDD −64,1 %.**
> **DÉLAI+1 :** +0,46 → +0,45.  **TWO-SIDED :** long **+0,656** / short **−0,256** → **beta long** (le short perd).  **DSR :** bruit.  **BETA :** rec 0,38 < BH 1,01.

## Gates — `results/s092_gates.csv` (2/4 FAIL)
La base price-breakout Donchian = trend/beta long (cf #20-22, déjà DISCARD), et le filtre volume (a) n'est pas reproductible et (b) n'aide pas selon la source. 92ᵉ traitée, **92ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s092_volume_filters.py` (base volume-OFF ; dépend de `trend_lab`). `ftmo_lab.py` inchangé.
