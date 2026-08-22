# Rapport stratégie 65/109 — ORBP with Price Channel Filter (Filter & Exit) — *court (héritage ORB)*

**Statut :** ❌ **DISCARD (3/4)** — *ORB filtré par cassure Donchian ; artefact de fill + beta long + grille = bruit.* · **Source :** https://oxfordstrat.com/trading-strategies/orbp-with-price-channel-filter/ (Crabel + Donchian, rating **C**). · **Registre :** #65. · 2026-06-07.

## Spec & archétype
Entrée **ORB-stop** restreinte au côté confirmé par une **cassure de canal Donchian** : `High[t] > UpperChannel[t−1]` (plus-haut sur Look_Back) → **long only** ; `Low[t] < LowerChannel[t−1]` → **short only** ; sinon stand-aside. Stretch = SMA(min(H−O,O−L),10)×1. Sortie : Time_Index + stop ATR×6. Côté sur t, trade t+1 (no look-ahead). `orb_filtered.simulate_orb_filtered`. Réf. Look_Back=20, Time=10.

## Résultats + chiffres décisifs (réf. Look_Back=20, Time=10)
**6 532 trades · win 51,4 % · expR +0,0121 · PF 1,073 · Sharpe 0,42 · MaxDD −40,1 %.**

> **DÉLAI+1 :** +0,42 → **−0,04** (inversion = **artefact de fill**).  **TWO-SIDED :** long +0,036 / short −0,021 → **beta long déguisé**.  **DSR :** 1,07 < 1,78 → **grille = bruit**.  **BETA-MATCHED :** rec 0,61 < BH 1,01 → ne bat pas le beta.

## Gates — `results/s065_gates.csv` (3/4 FAIL)
Contrairement au filtre momentum (#64), le filtre **canal Donchian** ne déclenche que les jours de cassure de canal — précisément ceux où le **fill intrabar est le plus optimiste** → l'artefact de fill **revient** (délai+1 inverse), et la sélectivité accrue rend la grille non significative. Pire que #64 sur tous les plans sauf le MaxDD. 65ᵉ traitée, **65ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s065_orbp_channel.py` (dépend de `orb_filtered` + `beta_bench`). `ftmo_lab.py` inchangé.
