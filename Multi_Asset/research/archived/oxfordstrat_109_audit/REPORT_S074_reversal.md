# Rapport stratégie 74/109 — Reversal Patterns Part 1 (Wyckoff/Crabel pivots)

**Statut :** ❌ **DISCARD (2/4)** — *reversal sur pivots offre/demande ; beta long déguisé + grille = bruit.* · **Source :** https://oxfordstrat.com/trading-strategies/reversal-patterns-1/ (Wyckoff/Crabel, rating **C**). · **Registre :** #74. · 2026-06-07.

## Spec & archétype
**Pivot reversal** (archétype neuf, deux côtés) : *Demand pivot* = plus-bas fractal (min sur ±5 barres) ; *Bottom Reversal* (long) = le prix casse sous un demand pivot puis se retourne (clôture > 2 clôtures précédentes, > pivot, > open & mid-range, range > veille, dans les 5 barres du breakdown). Entrée open lendemain ; sorties : quick-stop (plus-bas vrai du setup), cible RR×risque, stop ATR×6, sortie temporelle. Top Reversal (short) = miroir. Balayage Reward_Ratio × Trade_Duration. Réf. RR=4, TD=20.

## Résultats (réf. RR=4, TD=20)
**5 007 trades · win 29,1 % · expR +0,0113 · PF 1,086 · Sharpe 0,42 · MaxDD −29,2 %.**
> **DÉLAI+1 :** open[+1] +0,42 → open[+2] +0,69 (pas d'artefact de fill ; entrée @open).  **TWO-SIDED :** long **+0,042** / short **−0,011** → asymétrie = **beta long déguisé**.  **DSR :** 0,42 < 1,52 → grille = bruit.  **BETA-MATCHED :** rec 0,52 < BH 1,01 → ne bat pas le beta.
> Grille : seuls les **grands RR (4-8)** sont positifs (RR=2 quasi nul) — conforme à la fiche (« reversal patterns très sensibles aux coûts ; grandes cibles préférées »).

## Gates — `results/s074_gates.csv` (2/4 FAIL)
Le pattern de réversion sur pivots survit au délai+1 mais (i) tout le PnL vient du **long** (le short perd) = beta long, et (ii) la grille RR×TD n'est **pas significative** (DSR). Le win rate très bas (29 %) compensé par de gros RR le rend fragile aux coûts. 74ᵉ traitée, **74ᵉ DISCARD**.

## Repro
`cd oxfordstrat_109/code && python strat_s074_reversal.py` (dépend de `ftmo_lab` + `beta_bench`). `ftmo_lab.py` inchangé.
