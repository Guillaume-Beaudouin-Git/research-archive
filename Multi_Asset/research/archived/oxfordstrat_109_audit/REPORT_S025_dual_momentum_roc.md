# Rapport stratégie 25/109 — Dual Momentum & Rate of Change (Entry)

**Statut :** ❌ **DISCARD (2/4)** — *nouvel archétype (dual momentum absolu / CTA) ; beta long déguisé (Gate 2) + DSR. Gate 1 & OOS PASS.* · **Source :** https://oxfordstrat.com/trading-strategies/dual-momentum-rate-of-change/ (rating **C**). · **Registre :** #25. · 2026-06-06.

> Momentum absolu **double confirmation** (lent = filtre, rapide = setup). Reproduit fidèlement le profil CTA de la fiche (Sharpe ~0,6–0,9, MaxDD ~50 %) — et meurt comme tout le reste : **beta long**.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif Sharpe **+0,59** (expR +0,0830) → fill réaliste **+0,52** (expR +0,0719). **→ PASS : robuste au fill (entrée breakout d'extrême, pas un artefact).**
> **TWO-SIDED (Gate 2) :** long **+0,2116** (n=1060) / short **−0,1137** (n=693). **→ FAIL : long porte tout, short perd = beta long.**

## Spec & archétype
**Dual momentum** sur *Rate of Change*. `ROC1` (lent, Look_Back_#1) et `ROC2` (rapide, LB2=round(LB1×0,5)). **Filtre** : long si ROC1>0 / short si ROC1<0. **Setup** : long si ROC2>0 / short si ROC2<0. **Entrée (Extreme Point Rule)** : quand les deux momentums sont alignés, achat au-delà de l'extrême récent (opérationnalisé en breakout du plus-haut de la fenêtre rapide). **Sortie** : Time Exit (Time_Index) + ATR×6. Sweep `Look_Back_#1 × Time_Index`. Simulateur partagé `simulate_dual_mom` (réutilisé par #26) ; `ftmo_lab` v2-gates inchangé. Point LB1=100/LB2=50, Time=51 (la fiche recommande Time>50).

## Résultats (réf. LB1=100/LB2=50, Time=51)
**1 753 trades · win 50,0 % · expR +0,0830 · PF 1,230 · Sharpe 0,59 · MaxDD −53,4 %.** Grille `LB1 × Time` **100 % positive** (expR croît avec LB1 et Time — exactement ce que dit la fiche : *« longer holding preferred »*). Cohérent avec les Sharpe 0,55–0,90 publiés.

## Gates — `results/s025_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,59 → **+0,52** | ✅ PASS — robuste au fill |
| 2 | Two-sided | long +0,212 / short **−0,114** | ❌ **FAIL — beta long** |
| 3 | DSR (N=9) | best Sharpe 0,805 < 1,519 | ❌ FAIL — bruit |
| 4 | OOS | train +0,106 → test **+0,063** | ✅ PASS — positif OOS |

## Verdict
❌ **DISCARD (2/4).** Le momentum absolu à double confirmation est un **vrai trend-follower** (survit délai+1 + OOS, profil CTA conforme à la fiche). Mais c'est du **beta long** : tout le profit vient des longs (+0,21), les shorts perdent (−0,11). Sur cet univers à dérive haussière, « acheter la force confirmée » = capter le beta. DSR insuffisante (Sharpe 0,8 < seuil). MaxDD −53 %. **DISCARD.** 25ᵉ traitée, **25ᵉ DISCARD**. *(8ᵉ mécanisme trend indépendant à mourir au Gate 2.)*

## Suite
**#26 (Dual Momentum & Vortex)** = même structure dual-momentum, indicateur Vortex au lieu du ROC → héritage attendu (la fiche dit elle-même que ROC et Vortex ont des perfs similaires).

## Repro
`cd oxfordstrat_109/code && python strat_s025_dual_momentum_roc.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code : `code/strat_s025_dual_momentum_roc.py`.
