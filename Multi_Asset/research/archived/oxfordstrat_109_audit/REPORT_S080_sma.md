# Rapport stratégie 80/109 — Simple Moving Average Filter (Entry & Exit) — *contrôle propre : trend = beta*

**Statut :** ❌ **DISCARD (2/4)** — *SMA dual classique = beta long déguisé ; le short perd. Sert de CONTRÔLE pour le Ross Hook.* · **Source :** https://oxfordstrat.com/trading-strategies/simple-moving-average/ (Kaufman, rating **C**). · **Registre :** #80. · 2026-06-07.

## Spec & archétype
Trend dual-SMA, toujours-en-position (2 phases) : `Fast_SMA > Slow_SMA` → long ; `<` → short. Entrée @open, sortie sur flip + stop ATR×6. Fast = Fast_Index × Slow. Réf. Slow=250, Fast=62. `trend_lab` (machine à états @open).

## Résultats (réf. Slow=250, Fast=62)
**840 trades · win 36,7 % · expR +0,352 · PF 1,790 · Sharpe 0,70 · MaxDD −76,6 %.**
> **DÉLAI+1 :** +0,70 → +0,69 (entrée @open, pas d'artefact).  **TWO-SIDED :** long **+0,893** / short **−0,184** → le **short perd** = beta long.  **DSR :** grille = bruit.  **BETA-MATCHED :** rec 0,79 < BH 1,01 → **ne bat pas le beta**.

## Gates — `results/s080_gates.csv` (2/4 FAIL)
Le SMA dual est un **trend-follower générique** : tout le PnL vient du **long** (le short perd), et il **ne bat pas le buy&hold** (0,79 < 1,01). C'est du beta long classique. 80ᵉ traitée, **80ᵉ DISCARD**.

> 🔍 **Rôle de contrôle (important pour #76).** Le SMA dual ÉCHOUE là où le Ross Hook PASSE, sur le **même univers** et le même moteur de coûts. Cela montre que l'edge du Ross Hook **n'est pas** « la tendance marche ici » (sinon le SMA passerait aussi) mais vient de la **sélectivité de l'entrée hook** (achat de la reprise après la 1ʳᵉ correction). C'est le contraste qui crédibilise #76.

## Repro
`cd oxfordstrat_109/code && python strat_s080_sma.py` (dépend de `trend_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
