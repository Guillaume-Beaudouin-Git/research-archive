# Rapport stratégie 23/109 — Dow Theory – Multiple Time Frames (Entry)

**Statut :** ❌ **DISCARD (2/4)** — *nouvel archétype (pivots/swing-structure MTF) mais même bassin : beta long déguisé (Gate 2) + DSR. Gate 1 & OOS PASS.* · **Source :** https://oxfordstrat.com/trading-strategies/dow-theory-trend-2/ (Charles Dow, rating **C**). · **Registre :** #23. · 2026-06-06.

> Mécanisme **différent** (pas de canal/MA — des **pivots DeMark** + filtre de tendance primaire multi-échelle), mais il meurt exactement comme les breakouts : c'est du **suivi de tendance = beta long** sur cet univers.

## LES 2 CHIFFRES DÉCISIFS (en tête)

> **DÉLAI+1 (Gate 1) :** natif Sharpe **+0,61** (expR +0,0311) → fill réaliste open[i+1] **+0,46** (expR +0,0232). **→ PASS : vrai breakout de structure (swing-high), survit au fill.**
> **TWO-SIDED (Gate 2) :** long **+0,0678** (n=1751) / short **−0,0199** (n=1260). **→ FAIL : long porte tout, short perd = beta long.**

## Spec & archétype
Suivi de tendance **Dow Theory multi-échelle** sur **pivots DeMark** (fractals). *Supply pivot* = haut entouré de `Pivot_Size` plus-bas-hauts de chaque côté ; *demand pivot* = bas entouré de plus-hauts-bas. **Filtre = tendance primaire** (gros pivots, `Primary_Size = Pivot_Size × Pivot_Index`) : long seulement si primaire haussière (pHH & pHL). **Entrée** = en primaire haussière, buy stop au-dessus du dernier swing-high *secondaire* (reprise de tendance après pullback). **Sortie** = trailing sell stop sous le dernier swing-low secondaire + stop ATR×6. Sweep `Pivot_Size × Pivot_Index`.

Implémentation fidèle `simulate_dow` : fractals vectorisés avec **lag de confirmation causal** (`shift(window)`), état de tendance primaire via les 2 derniers pivots HH/HL, entrée sur cross frais, sortie trailing vectorisée. Point représentatif **Pivot_Size=2 / Pivot_Index=3** (primaire = 6). `ftmo_lab` v2-gates inchangé.

## Résultats (réf. Pivot_Size=2, Pivot_Index=3)
**3 011 trades · win 38,0 % · expR +0,0311 · PF 1,193 · Sharpe 0,61 · MaxDD −38,0 %.** Grille `PS × PI` **100 % positive** (expR croît avec Pivot_Size — pivots plus gros = tendances plus marquées).

## Gates — `results/s023_gates.csv` (2/4 FAIL)

| # | Gate | Résultat | Verdict |
|---|---|---|---|
| 1 | Délai+1 | +0,61 → **+0,46** | ✅ PASS — vrai breakout de structure |
| 2 | Two-sided | long +0,068 / short **−0,020** | ❌ **FAIL — beta long déguisé** |
| 3 | DSR (N=9) | best Sharpe 0,850 < 1,519 | ❌ FAIL — grille = bruit |
| 4 | OOS | train +0,021 → test **+0,040** | ✅ PASS — positif OOS |

## Verdict
❌ **DISCARD (2/4).** Le pivot/Dow-theory MTF est un **vrai signal de structure** (survit délai+1 + OOS) avec un **MaxDD nettement meilleur (−38 %)** que les breakouts de canal (−60 à −88 %) grâce à la sortie trailing sur swing-low — *la sortie est la meilleure du lot trend à ce jour.* Mais le **cœur reste identique** : acheter la force dans une tendance primaire haussière = **capter le beta long** (long +0,068 / short −0,020). Pas un edge symétrique ; DSR insuffisante. **DISCARD.** 23ᵉ traitée, **23ᵉ DISCARD**.

**Méta-constat (taxonomie trend) :** 6ᵉ mécanisme de *continuation de tendance* indépendant à mourir au Gate 2 (après KAMA, ADX/Donchian, Aroon, Bollinger-breakout, DI-cross, channel-breakouts). **Tout « acheter la force » sur cet univers = beta long.** L'archétype change, le verdict non.

## Suite
**#24 (Dow Theory – Trend, Entry & Exit)** = le *cas de base* (mono-échelle) que la #23 « benchmarke » → héritage attendu (même pivot/trend). Puis #25/#26 (Dual Momentum).

## Repro
`cd oxfordstrat_109/code && python strat_s023_dow_mtf.py` (Python 3.10.12 ; numpy 2.2.6 ; pandas 2.3.3). Moteur `ftmo_lab.py` partagé/inchangé. Code faisant foi : `code/strat_s023_dow_mtf.py`.
