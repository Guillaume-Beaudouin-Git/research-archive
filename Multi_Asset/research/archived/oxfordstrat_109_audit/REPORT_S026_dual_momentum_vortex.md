# Rapport stratégie 26/109 — Dual Momentum & Vortex Indicator (Entry) — *court (héritage)*

**Statut :** ❌ **DISCARD (2/4)** — *héritage dual-momentum (#25) : beta long déguisé (Gate 2) + DSR. Gate 1 & OOS PASS.* · **Source :** https://oxfordstrat.com/trading-strategies/dual-momentum-vortex-indicator/ (Botes & Siepman, rating **C**). · **Registre :** #26. · 2026-06-06.

> **Même structure que #25**, indicateur **Vortex** au lieu du ROC. La fiche dit elle-même que ROC et Vortex ont des perfs similaires — confirmé : résultats quasi identiques.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif Sharpe **+0,58** (expR +0,0767) → fill réaliste **+0,48** (expR +0,0621). **→ PASS.**
> **TWO-SIDED (Gate 2) :** long **+0,2071** (n=1004) / short **−0,1241** (n=652). **→ FAIL : beta long.**

## Spec & archétype (1 ligne)
Dual momentum sur **Vortex** : `+VI_lb = Σ|H−L₋₁| / ΣTR`, `−VI_lb = Σ|L−H₋₁| / ΣTR` (lent LB1 = filtre, rapide LB2 = setup). Long si +VI1>−VI1 ET +VI2>−VI2 ; entrée breakout d'extrême ; sortie Time+ATR×6. **Réutilise `s025.simulate_dual_mom` tel quel** (seul le régime change) ; `ftmo_lab` v2-gates inchangé. Point LB1=100/LB2=50, Time=51.

## Résultats (réf. LB1=100/LB2=50, Time=51)
**1 656 trades · win 49,8 % · expR +0,0767 · PF 1,216 · Sharpe 0,58 · MaxDD −51,0 %.** Grille `LB1 × Time` 100 % positive. Quasi identique au #25 (ROC).

## Gates — `results/s026_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,58 → **+0,48** | ✅ PASS |
| 2 | Two-sided | long +0,207 / short **−0,124** | ❌ FAIL — beta long |
| 3 | DSR (N=9) | best Sharpe 0,768 < 1,519 | ❌ FAIL — bruit |
| 4 | OOS | train +0,110 → test +0,048 | ✅ PASS |

## Verdict
❌ **DISCARD (2/4).** Identique au #25 : vrai trend-follower (Gate 1 + OOS OK) mais **beta long** (long +0,21 / short −0,12), DSR insuffisante. Le changement d'indicateur (Vortex vs ROC) ne change rien — comme annoncé par la fiche. 26ᵉ traitée, **26ᵉ DISCARD**.

**Cluster dual-momentum = {#25, #26} : 2/2 DISCARD au Gate 2.** *(9ᵉ mécanisme trend indépendant à mourir au Gate 2 — la taxonomie « acheter la force = beta long » est désormais écrasante.)*

## Suite
Fin du bloc tendance/momentum. Prochain : **cluster Engulfing (#27-#30)** — pattern bougie d'absorption (reversal), **3ᵉ archétype de bougie** distinct du Doji → potentiel mean-reversion, à tester à fond.

## Repro
`cd oxfordstrat_109/code && python strat_s026_dual_momentum_vortex.py` (dépend de s025). Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3. Moteur `ftmo_lab.py` partagé/inchangé. Code : `code/strat_s026_dual_momentum_vortex.py`.
