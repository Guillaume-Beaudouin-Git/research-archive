# Candidat — Long-vol VXX (tail-hedge overlay)

> **Statut** : Phase-2 complète, **NON-RENTABLE en overlay naïf** sur le merge testé. Conservé comme référence convexité, à reconsidérer SI un timing VIX/VIX3M backwardé est ajouté (qui dépasse le signal naïf L10).
> **Source canonique** : `data/skew_research/session_cowork/exploration_2026-06.md` (phase 3) + `data/skew_research/MERGE_portfolio_2026-06.md` (§5).

## Mécanisme

Long-vol structurel via VXX (front-month VIX futures ETN) en overlay d'un sleeve de portefeuille (typiquement trend / TSMOM). L'idée : couvrir le tail correlated-crash-day qui menace la barrière daily-DD propfirm. Pay-off attendu = pic VIX sur jour de stress equity.

## Métriques mesurées

| Champ | Valeur (fenêtre 2018-01-26 → 2026-05-27, n=2094) |
|---|---|
| Skew daily | **+1,86** (le plus élevé du merge) |
| Mean daily | **−9,99 bps** (theta bleed) |
| Sharpe standalone | **−0,34** |
| MaxDD standalone | **−99 %** (naive always-long) |
| corr vs LONG_US500 | **−0,748** (le hedge equity marche) |
| corr vs TSMOM_PROXY | −0,197 |
| corr vs Donchian / XS-mom / autres sleeves | −0,06 … −0,10 |

### Décomposition crash days (test décisif §5 MERGE)

- VXX mean sur jours krach (LONG_US500 ≤ p5 = −1,79 %/j) : **+10,67 %/jour**
- VXX mean sur jours normaux : **−0,67 %/jour** (theta bleed)
- Naïf naïf 10 % overlay sur TSMOM, 8,3 ans :
  - ann return : +2,72 % → **−0,07 %** (Δ = **−2,79 %/an drag**)
  - MaxDD : −33,6 % → −34,7 % (**aggravé +1,1 pp**)
  - worst day : −6,29 % → −5,28 % (atténué +1 pp)

## Verdict

> **NON RENTABLE en overlay naïf 10 %.** Le drag theta (−2,8 %/an) dépasse le bénéfice DD (1 pp réduit / parfois aggravé). L'arbitrage est défavorable : **DD évité (1pp) × p(krach) (5%) < portage certain (2,8 %/an)**.

L'overlay VXX est de **l'assurance trop chère** sur la fenêtre 2018-2026 (qui inclut pourtant COVID-2020 et bear 2022 — les meilleurs scenarii pour VXX). Sur sample plus calme, le drag serait pire encore.

Cohérent avec verdict session_cowork : *« long-vol = portfolio insurance, not profit edge »* — confirmé chiffré dans le MERGE.

## Gate-0 FTMO

- ❌ **VXX est un ETN — pas tradeable FTMO** (« no access to ETFs, bonds, options, or spot markets »).
- ❌ Pas de VIX futures sur FTMO (univers Forex/Indices/Commodities/Stocks CFD/Crypto).
- ❌ Pas de proxy fidèle : un long-VIX synthétique via options/straddles n'est pas accessible non plus.

→ Hors-FTMO de toute façon. Réservé compte courtier classique (ETN ou VIX futures CME).

## Conditions de promotion (improbables court terme)

1. **Timing tactique VIX/VIX3M backwardé** : long-vol seulement quand le term-structure inverse. Dépasse le signal naïf L10 (interdit comme tel pour la première itération du book). Nécessiterait une étude dédiée.
2. **Réduire l'allocation** : 1-2 % VXX au lieu de 10 % → drag réduit mais bénéfice quasi-nul aussi.
3. **Pivot instrument** : VIX futures CME directement (commission inférieure, pas de drag ETN), mais théta toujours présent. Marginal.

## Corrélations utiles connues

| Vs sleeve | Corr (commune 2018-2026) |
|---|---:|
| LONG_US500 | **−0,748** |
| VIXTERM (timé) | **−0,357** |
| TSMOM_PROXY | −0,197 |
| MR_REVERSAL | −0,123 |
| PREFOMC | −0,134 |

→ Anti-corrélé partout, surtout equity. Profil convexe pur, mais coût certain.

## Réconciliation archive

- Cohérent avec [[orb-structure-diagnostic-2026-06]] : « overlay anti-cluster détruit l'edge » — même classe d'artefact (overlay intuitivement séduisant, drag mesuré).
- Distinct du VRP short-vol archivé (skew −1,70 natif, cost-killed) — c'est le côté inverse, **structurellement skew+ mais carry−**.
- Lesson candidate : *« convexity sleeve ≠ edge »* — long-vol a EV standalone négatif mais est le sleeve de portefeuille le plus anti-corrélé à l'equity. Sélection sur skew+décorrélation ne suffit pas : le carry doit être supportable.
