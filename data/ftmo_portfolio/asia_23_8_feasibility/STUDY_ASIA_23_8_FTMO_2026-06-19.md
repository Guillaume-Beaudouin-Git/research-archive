# ÉTUDE DE FAISABILITÉ — ASIA_23_8 (gold overnight-drift) comme sleeve FTMO candidate

**Date :** 2026-06-19 · **Branche :** `claude/asia-23-8-ftmo-feasibility` · **Statut :** RECHERCHE PURE — go/no-go
**Pré-registration :** `PREREGISTRATION.md` (committée AVANT tout résultat, commit `fdf40b4`)
**Auteur :** session Claude Code (author≠auditor — validation ultérieure en session fraîche)
**Cadre :** sandboxé. AUCUN déploiement, AUCUN toucher au book live (`ftmo_live/`, EA gelé, FLAT, compte armé).
Le book FTMO 4-sleeves (vm14) lancé lundi est INDÉPENDANT et n'est pas affecté.

---

## VERDICT — (c) NON-VIABLE pour FTMO

ASIA_23_8 **échoue les gates prop-firm FTMO** (Q2) : aucune configuration pré-enregistrée
n'atteint le seuil de viabilité. Le triplet headline est **négatif en EV**.

| | p(funded) | attempts | EV campagne | bust/tentative |
|---|--:|--:|--:|--:|
| **Book incumbent (4 sleeves, vm14)** | **87.0 %** | 3.24 | **+$943** | — |
| ASIA standalone — meilleur (V0, K=4) | 35.1 % [26.8, 43.3] | 1.91 | **−$150** | 46.4 % |
| ASIA standalone — bust-contrôlé (V0, K=3) | 19.5 % [12.5, 27.1] | 1.49 | **−$124** | 31.2 % |

Cause racine : l'edge est **réel mais trop LENT** pour le mur de 91 j à un sizing survivable, et la
**barrière daily −5 %** + le **floor statique −10 %** sont percés par les **excursions intraday** de la
stratégie (pire −7.76 % à K=1, jour à levier 3× dans une surprise de vol). Monter K pour atteindre la
cible +10 % fait exploser le bust (~46 % à K=4). C'est la signature « no-bust × temps-illimité » déjà
documentée sur l'ORB ([[orb_realconstraints_2026-06]]), pas un edge exploitable en challenge.

Le **swap-free est confirmé** sur l'infra FTMO (Q4, le seul positif net), mais c'est nécessaire-non-suffisant.
En book add-on (Q3), ASIA est **décorrélée en rendement** (ρ 0.08) mais **n'améliore pas** le p(funded) du
book (Δ dans le bruit) et **empile de la marge métal** sous levier Swing.

**Recommandation :** ne PAS lancer d'étude d'intégration. Réexamen envisageable seulement si (i) un
véhicule prop-firm SANS mur temporel court ET (ii) un cap de vol-target bien plus bas (hors budget de
mods pré-enregistré) — voir §Q5.

---

## Q1 — Reproduction : le RAPPORT reproduit au centième ; le docstring est optimiste

`strategy_overnight.backtest` sur le stack actuel (XAUUSD M1→H1 true-UTC, 2007–2026, 5 018 jours, swap=0) :

| spread RT | Sharpe (moi) | rapport | docstring | OOS (moi) | maxDD (moi) | DSR(90) | t_HAC |
|---|--:|--:|--:|--:|--:|--:|--:|
| 1.0 bp | 1.293 | — | 1.38 | 1.144 | −16.4 % | 1.00 | 5.66 |
| **1.5 bp** | **1.101** | **1.10** ✓ | 1.18 ✗ | **0.961** (rpt 0.96 ✓) | **−19.45 %** (rpt −19.4 ✓) | **0.992** (0.99 ✓) | **4.82** (4.8 ✓) |
| 2.0 bp | 0.909 | — | 0.98 | 0.779 | −22.7 % | 0.942 | 3.98 |

Au spread headline 1.5 bp, **toutes** les métriques du rapport reproduisent au centième :
skew +0.348 (rpt +0.35), β vs gold 0.0036 (≈0.01), α +3.0 bp/j t_HAC +4.63 (rpt +2.95/+4.84),
rendement +7.75 %/an, vol 6.83 %, hit 52.4 %, skew mensuel +0.27, pire mois −5.8 %, WF 5/5.
La table d'attribution annuelle reproduit aussi : **2018 −1.2 bp/SR −2.18, 2019 +0.7 bp/SR −0.30,
2021 +8.3 bp/SR +2.37** (un nouveau creux **2022 −0.0 bp/SR −0.67** apparaît hors-rapport).

**Le docstring du code (1.18/1.07/−15.6 %/t3.9/DSR0.92) NE reproduit PAS** : Sharpe surévalué ~+0.08,
maxDD sous-évalué ~4 pts. **PASS-repro sur le RAPPORT** (source conservatrice et exacte) ;
le docstring est la source périmée/optimiste — DIVERGENCE documentée.

## Q2 — Survie aux gates FTMO 2-step : NON-VIABLE (le point critique)

**Méthode (pré-enregistrée).** Moteur barre v2.2 audité (`engine_v22.py`, pin `605f4a4`, pooled
contractuel 0.87) réutilisé read-only ; ASIA injectée par wrapper sandbox (`asia_inject.py`) comme
P&L d'ouverture de jour + contrôle de barrière sur le **plus-bas intraday** (la fenêtre 01:00–09:00 CET
clôture au 1er segment du book 09:00). **Validation du wrapper** : ASIA OFF reproduit le pooled
**87.01** (att 3.24, n=462, identité cash exacte) → injection non-invasive prouvée. Le standalone
(book OFF) se réduit exactement à un first-passage daily ; le sim lean `asia_fp` est **validé au
centième contre le moteur barre** (|Δ| = 0.0 pt à K=1.5 et K=3.0).

**Sweep K × variantes (V0 baseline / V2 MA100-gate / V3 régime-drift / V4 = les deux ; budget 3-mods épuisé) :**

| variante | K | p(funded) | IS | OOS | att | bust | med_t (j) | DD p5 | DD pire |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| V0 | 1.0 | 0.0 % | 0.0 | 0.0 | 1.02 | 2.0 % | — | −5.2 | −11.2 |
| V0 | 2.0 | 8.2 % | 9.0 | 7.4 | 1.12 | 10.6 % | 63 | −9.1 | −13.2 |
| V0 | 3.0 | 19.5 % | 18.4 | 20.5 | 1.49 | 31.2 % | 56 | −10.1 | −26.2 |
| **V0** | **4.0** | **35.1 %** | 28.3 | 41.9 | 1.91 | **46.4 %** | 54 | −10.8 | −35.0 |
| V2 | 3.0 | 16.9 % | 15.9 | 17.9 | 1.26 | 18.0 % | 56 | −8.8 | −12.7 |
| V2 | 4.0 | 25.1 % | 18.4 | 31.9 | 1.48 | 30.6 % | 55 | −9.8 | −19.3 |
| V3 | 4.0 | 29.4 % | 25.3 | 33.6 | 1.74 | 41.6 % | 54 | −10.3 | −35.0 |
| V4 | 4.0 | 24.5 % | 18.4 | 30.6 | 1.44 | 28.3 % | 55 | −9.5 | −19.3 |

*(grille complète : `results/q2_standalone.json`)*

**Lecture.**
1. **Aucune config n'approche le seuil VIABLE de 0.50.** Le maximum est V0 K=4 = 35.1 % [26.8, 43.3]
   — borne 95e à 43.3 %, toujours sous 0.50 — et au prix d'un **bust 46.4 %/tentative** (>> plafond
   « contrôlé » 0.35). Les variantes V2/V3/V4 réduisent le bust MAIS aussi le p(funded) (elles coupent
   l'exposition) → aucune ne franchit 0.30 avec bust contrôlé.
2. **La barrière daily −5 % est le verrou.** Le plus-bas intraday (pire −7.76 % à K=1) la perce dès
   qu'un jour à levier 3× rencontre une surprise de vol ; à K≥2 c'est récurrent. Le cap de vol-target
   à 3× est trop haut pour un barrière daily de 5 %.
3. **EV négatif.** Triplet standalone : K=4 (0.351, 1.91, **−$150**) ; K=3 (0.195, 1.49, **−$124**).
   Le funded_value tombe à ~$96 (refund seul) car le compte funded buste sur les excursions → on paie
   les frais et on n'extrait rien.
4. **Contre-vérification `firstpassage.py`** (close-to-close, block-bootstrap, **borne optimiste** sans
   plus-bas intraday) : p(funded ≤ 63 j-bourse) = 2.3 %/20.7 %/29.4 % à K=1.5/3/4 — **concorde** avec
   `asia_fp`. Le *terminal* (sans mur) atteint 58–66 % MAIS avec **médiane 200–300 j** à K≤1.5 → l'edge
   ne se matérialise que sur >1 an, pendant lequel le risque de régime-mort (−19.4 %/4.7 ans) menace.
   C'est l'artefact temps-illimité, pas une viabilité challenge.

**Verdict Q2 = NON-VIABLE.** *Note de probité (author≠auditor)* : les seuils pré-enregistrés laissent
un interstice — la seule config ≥0.30 (V0 K=4, 35.1 %) a un bust 46.4 % « non-contrôlé » (>0.35), donc
elle ne satisfait NI VIABLE (exige ≥0.50) NI le CONDITIONNEL (exige bust contrôlé en [0.30,0.50)). J'adjuge
**NON-VIABLE** car aucun sizing ne délivre des chances de funding acceptables sans bust inacceptable
(~moitié), sans déplacer aucun seuil. L'auditeur pourra ré-examiner cet arbitrage.

## Q3 — Conflit avec la sleeve or-trend : décorrélée en rendement, mais sans bénéfice book + marge empilée

**(a) Corrélation** (rendements daily net sleeve-level ; gold_trend reconstruite de `cleanroom.build_signals`) :

| fenêtre | n | Pearson | Spearman |
|---|--:|--:|--:|
| full | 4 979 | **0.084** | 0.073 |
| IS (2013–19) | 1 605 | −0.073 | −0.076 |
| OOS (2020–26) | 1 658 | +0.188 | +0.165 |
| régime-mort 2018–19 | 512 | +0.007 | −0.035 |

Corrélation **basse** (< 0.50, régime-instable mais faible en magnitude). gold_trend n'est long que
**25.8 % des jours** (dead-zone |s|<0.34) ; ASIA est toujours long → ils n'« empilent du gold » que ~26 %
du temps. **Ce n'est pas de la concentration de RENDEMENT déguisée.**

**(b) Marge (Swing métal XAU 1:9 = 0.1111).** ASIA empreinte marge = 0.11 × K × pos de l'équité :

| K | p50 | p99 | max |
|--:|--:|--:|--:|
| 0.5 | 0.057 | 0.122 | 0.143 |
| 1.0 | 0.115 | 0.245 | 0.287 |
| 2.0 | 0.229 | 0.490 | 0.574 |
| 2.5 | 0.286 | 0.612 | **0.717** |

Le book lie déjà le **cap 60 % 56 % des jours** sous Swing (spec : need p50 0.687, p99 3.946). gold_trend
étant tenu en continu, les deux jambes XAU **coexistent pendant 01:00–09:00 CET** chaque jour où gold_trend
est long. La marge ASIA s'empile dessus → combiné > 60 % (de-lever forcé du book / risque de stop-out
réel ; **le moteur ne modélise PAS la marge intra-fenêtre** — risque hors-sim). À K≥2.5 ASIA seule dépasse
60 %. **Axe marge = concentration/coût opérationnel sous Swing.**

**(c) Chevauchement horaire.** gold_trend rebalancé 22:05 CET et tenu en continu (Swing, week-ends inclus) ;
ASIA 01:00→09:00 CET. → chevauchement TOTAL chaque matin où gold_trend est long.

**(d) Ablation book vs book+ASIA** (moteur barre audité, mêmes cohortes ; funded_value book **$1442 ≈
spec $1422** → méthode EV validée) :

| config | p(funded) | Δp | attempts | funded_value | EV | ΔEV |
|---|--:|--:|--:|--:|--:|--:|
| **book seul** | 87.01 % | — | 3.24 | $1 442 | **+$943** | — |
| book+ASIA K=0.5 | 83.33 % | **−3.68** | 3.31 | $1 470 | +$908 | −$36 |
| book+ASIA K=1.0 | 87.45 % | +0.43 | 3.15 | $2 124 | +$1 554 | +$611 |
| book+ASIA K=1.5 | 84.63 % | **−2.38** | 3.33 | $2 126 | +$1 479 | +$536 |
| book+ASIA K=2.0 | 87.01 % | +0.00 | 3.39 | $1 538 | +$1 013 | +$70 |

Les **Δp(funded) ∈ [−3.7, +0.4] pt sont DANS le bruit de cohorte** (CI bloc du book ±4.3 pt, spec
[0.823, 0.916]) et non-monotones → **ASIA n'améliore PAS de façon fiable le passage du challenge**.
L'uplift EV à K=1 vient du **stage funded** (ASIA ajoute des retraits une fois funded) et est K-fragile
(négatif à K=0.5). Per les seuils pré-enregistrés (DIVERSIFIANTE exige Δp ≥ −0.02 **ET** marge ≤ 60 %),
la condition marge échoue sous Swing → **Q3 = CONCENTRATION (axe marge), pas de bénéfice book démontré**.
Nuance honnête : décorrélée en rendement OUI, mais sans gain de pass-rate + coût marge → ne qualifie pas
comme add-on DIVERSIFIANT au sens pré-enregistré.

## Q4 — Rollover / swap sur l'infra FTMO : SWAP-FREE CONFIRMÉ

Fuseau serveur confirmé **read-only** (`ftmo_live/lib/market_hours.py`) : **EEST = UTC+3 (été, jusqu'au
2026-10-25), EET = UTC+2 (hiver)**. Rollover swap = 00:00 serveur = **21:00 UTC (été) / 22:00 UTC (hiver)**.
ASIA tient **23:00 UTC (entrée) → 07:00 UTC (sortie)**.

| saison | rollover | dans [23:00, 07:00+1j) ? | écart entrée↔rollover |
|---|--:|:--:|--:|
| été EEST (UTC+3) | 21:00 UTC | **NON** | 2 h |
| hiver EET (UTC+2) | 22:00 UTC | **NON** | 1 h |

- **0 nuit de swap facturée** : le rollover précédent (21:00/22:00 UTC) est AVANT l'entrée 23:00 ; le
  suivant (21:00/22:00 UTC le lendemain) est APRÈS la sortie 07:00. La fenêtre ne traverse jamais le
  rollover, **été comme hiver** (condition stratégie « rollover ≤ 22:00 UTC » satisfaite). **DST safe.**
- **Entrée hors trou de liquidité** : 23:00 UTC est 1–2 h après l'instant de rollover (gel TimeCurrent).
- **Wednesday triple-swap** (XAU `triple_dow`=2) : **N/A** tant que swap-free (jamais tenu sur un rollover).
- **Contrefactuel** (si le swap −1.518 bp/nuit ÉTAIT facturé) : Sharpe **1.14 → 0.55** (1×/jour) → **0.41**
  (avec triple mercredi). Le swap-free n'est pas un détail : c'est ~la moitié du Sharpe. **Il EST satisfait.**

**Verdict Q4 = SWAP-FREE CONFIRMÉ** (swap-leak effectif 0 bp/nuit). Caveat orthogonal (non-swap) : la
session asiatique a un **spread plus large** et le **fill précis à 23:00 UTC** est le make-or-break
(rapport : entrée +1 h ⇒ Sharpe 0.37) → **non mesurable hors paper-trade**.

## Q5 — Verdict de recherche

Per la règle de décision pré-enregistrée : **(c) NON-VIABLE pour FTMO**, car **Q2 = NON-VIABLE**
(suffisant à lui seul). Synthèse par axe :

| axe | résultat | sens |
|---|---|---|
| Q1 reproduction | RAPPORT exact ; docstring optimiste | la stratégie est ce que dit le rapport (conservateur) |
| Q2 gates FTMO | **NON-VIABLE** (max 35 % p-funded @ 46 % bust ; EV < 0) | **disqualifiant** |
| Q3 conflit gold | décorrélée (ρ 0.08) mais 0 gain book + marge Swing empilée | pas d'add-on diversifiant |
| Q4 swap/rollover | **SWAP-FREE confirmé** (le seul positif net) | nécessaire-non-suffisant |

**Pourquoi NON-VIABLE et pas conditionnel.** Le conditionnel supposait Q2 ∈ {VIABLE, CONDITIONNEL}.
Or Q2 échoue à la racine : à sizing survivable l'edge est trop lent pour 91 j ; au sizing qui atteint la
cible, le bust est ~50 %. Aucun overlay pré-enregistré (MA100, régime, combo) ne sauve l'arbitrage
vitesse-vs-survie. C'est structurel (forme de la distribution vs barrière symétrique — L24), pas un
problème de réglage. Le swap-free (Q4) et la décorrélation (Q3a) sont réels mais ne compensent pas.

### Ce qu'il faudrait pour ré-ouvrir (hors périmètre pré-enregistré — EXPLORATOIRE, non décisionnel)
1. **Un véhicule prop-firm sans mur temporel court** : le *terminal* firstpassage (58–66 %) suggère un
   passage éventuel à bas K — mais médiane 200–300 j et risque régime-mort 4.7 ans → dominé par le book
   (87 % en 91 j). Donc même là, non compétitif.
2. **Cap de vol-target ≪ 3×** (p.ex. 1.0–1.5×) pour dompter les excursions intraday qui percent le daily
   −5 %. C'est une **4e modification** (budget pré-enregistré épuisé à V4) → exigerait un NOUVEAU
   pré-enregistrement en session fraîche, pas un ajustement post-hoc ici.
3. **Si jamais reconsidéré, mesures paper-trade obligatoires** (le make-or-break) :
   - slippage réel du fill 23:00 UTC en session asiatique (cible spread effectif ≤ ~1.5 bp RT) ;
   - confirmation empirique swap-free sur le compte (relevé des swaps facturés, mercredis inclus) ;
   - drift glissant 12 m vs le prior 19 ans (kill si négatif > 6 mois).

---

## Reproductibilité
- Pré-registration : `PREREGISTRATION.md` (commit `fdf40b4`, avant résultats).
- Code (`code/`) : `q1_reproduce.py`, `asia_series.py` (série + plus-bas intraday, label-semantics
  vérifiée), `asia_inject.py` (wrapper moteur barre v2.2, validé ASIA-OFF→87.01), `asia_fp.py`
  (first-passage lean, validé |Δ|=0 vs barre), `q2_q3_sim.py`, `q3_conflict.py`, `q4_swap.py`, `q2_ci.py`.
- Résultats (`results/`) : `q1_reproduction.json`, `q2_standalone.json`, `q2_ci.json`,
  `q3_conflict.json`, `q4_swap.json`.
- Données : `data/deep_history_utc/XAUUSD_M1.csv` (true-UTC, local). Engine v2.2 pin `605f4a4`.
- Env : `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3, statsmodels 0.14.6).
- **Aucun fichier live touché.** Lecture seule sur `ftmo_live/lib/market_hours.py` (fuseau serveur) et
  `data/ftmo_portfolio/v22/` (spec/engine).
