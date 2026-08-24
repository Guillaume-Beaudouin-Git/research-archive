# PRÉ-REGISTRATION — Améliorations overnight-drift CIBLÉES FTMO (4 pistes)

**Horodatage (committé AVANT tout résultat) :** 2026-06-20
**Worktree dédié :** `../Algo_claude_overnight_improve` · **Branche :** `claude/overnight-ftmo-improve` (off origin/main)
**Auteur :** session Claude Code (author≠auditor) · **Cadre :** RECHERCHE PURE, lecture seule live, AUCUN déploiement.
**Règle d'or : seuils figés, non ajustables après résultats.**

## 0. Objectif et cadrage critique
Objectif = **FTMO (challenge + funded)**, PAS le Sharpe absolu (book futures hors-propfirm = projet futur, hors scope).
Les 4 études précédentes ont établi que le mur FTMO n'est PAS le Sharpe mais : **edge LENT** (mauvais pour la
vitesse-challenge) + **PLEINE-VOL** (dilue la survie-funded via le drawdown cumulé vs floor statique $9 000).
**Une amélioration ne vaut QUE si elle touche un de ces deux axes** : réduire le **DRAWDOWN CUMULÉ** (funded)
ou augmenter la **VITESSE** vers +10% (challenge). Toute amélioration qui ne monte que le Sharpe (vol-target,
confirmations cross-asset) = **HORS SCOPE / ÉCHEC FTMO** (sert le book futures futur, pas FTMO).

Leçons appliquées : `funded-survival-is-drawdown-governed-not-Sharpe` ; `funded-daily-loss-binds-not-the-static-floor`
(daily $500 fixe/plancher mobile solde_minuit−$500 ; max-loss statique $9 000) ; `two-FTMO-stages-reward-opposite-axes`
(challenge=vitesse/vol, funded=faible DD cumulé) ; **ablation funded sur FUNDED_WINDOWS canoniques** (pas fenêtre de
convenance — artefact attrapé au panier).

## 1. Setup (FIXE) — réutilise le moteur audité (pas de réimplémentation)
- **Moteur** : `overnight_series` (build GOLD/SILVER/WTI/SOYBEAN, reproduit le rapport), `basket_series`,
  `basket_inject` (injection funded v2.2 audité, **validé sleeve-OFF → pooled 0.87**), `basket_fp` (challenge
  first-passage), extraits **verbatim de `claude/overnight-basket-ftmo`** (provenance notée), important le moteur
  v22 + caches **read-only du main dir**.
- **Ablation funded** : **FUNDED_WINDOWS canoniques** (`C22.FUNDED_WINDOWS` = IS 2013-17 + OOS 2020-24,
  `FUNDED_STEP`), métrique **`survive252`** (p survie 12 m) + Δ vs book-only. `fundedV` = 0.8·(retraits+résidu)+$96.
- **Challenge** : `basket_fp.cohort_run` sur `WINDOWS`/`COHORT_STEP=7`, mur 91 j → p_funded (vitesse).
- **Signal exogène Piste 1** : FRED **DTWEXBGS** (Broad Trade-Weighted USD index, 2010-2026, cache `data/raw/`),
  ffill, défaut trade-ON où NaN (pré-2010/trous récents).
- Coût : spread 2 bp RT (convention métaux/panier). Swap-free (fenêtre 23:00→07:00 UTC ne traverse pas le rollover).

## ⚠️ ANTI-OVERFIT STRICT (cumul famille)
La famille overnight a DÉJÀ consommé ~beaucoup de trials (gold solo+funded, soybean, silver, WTI, panier, gold-dosing).
**DSR pénalise le cumul famille : n_trials_cumulé = 160** (90 due-diligence gold + ~70 études famille) ; +1 par piste.
**Chaque piste = UNE hypothèse économiquement motivée, UNE spécification pré-fixée. Pas de balayage de paramètres.
Si une piste échoue à sa 1ère spec, elle échoue — pas de 2e essai.** Rapporter les échecs = résultat valide.

## PISTE 0 (préalable, peut clore 2 instruments) — Edge vivant ou mourant ?
**Spec :** sur SILVER (post-2014, déjà restreint) et SOYBEAN, sur `win_w` (rendement fenêtre, le brut de l'edge) :
(a) Sharpe glissant 252 j + CI 90% (block-bootstrap) sur tout l'historique ; (b) **test de rupture (Chow)** sur la
moyenne, split au changement de régime documenté (silver pré/post-2014 ; soybean pré/post-2022-01).
**VERDICT MORT (figé) :** un instrument est déclaré **MORT** (et exclu des pistes suivantes) si la moyenne
post-rupture n'est PAS significativement positive (**t_HAC < 1.5**) OU le Sharpe glissant 12 m récent (derniers 2-3 ans)
a son CI 90% **entièrement ≤ 0**. Sinon VIVANT. (Soybean OOS 0.49<IS 1.08 ; silver négatif 2003-09.)

## PISTE 1 (la principale) — Overlay de régime sur GOLD, signal EXOGÈNE (DTWEXBGS)
**Hypothèse :** l'edge gold-overnight meurt en régime USD fort (mort 2018-19) ; couper la sleeve dans ces régimes
réduit le DRAWDOWN CUMULÉ (axe funded).
**Spec UNIQUE (pré-fixée, non tunée) :** trader gold overnight **seulement si la variation 63 j-bourse (3 m) de
DTWEXBGS ≤ 0** (USD non-appréciant sur le trimestre glissant) ; **flat (pos=0) sinon**. Seuil = 0 (frontière
naturelle apprécie/pas), causal (`.shift(1)`, données passées seules).
**Métriques :** drawdown gold AVEC overlay vs SANS (coupe-t-il le −19% ?) ; Sharpe overlay (rapporté, PAS le critère) ;
**ablation funded book+gold_overlay vs book-only (canonique)** → Δsurvie, comparée au **baseline dilutif
book+gold_sans-overlay** ; split IS/OOS (whipsaw = danger : couper après mauvaise passe et rater le rebond 2021).
**SUCCÈS FTMO (figé) :** l'overlay rend gold **NON-dilutif** : `Δsurvie(book+gold_overlay) ≥ −3 pt` **ET**
nettement meilleur que `Δsurvie(book+gold_sans-overlay)` **ET** robuste OOS (bénéfice tient en OOS, pas que IS).
C'est la piste qui peut débloquer FTMO. Verdict net oui/non.

## PISTE 2 — Spread SILVER/GOLD (hedge du facteur commun) — *SAUTÉE si silver MORT (Piste 0)*
**Hypothèse :** le facteur commun gold/silver (~0.57) rend le panier dilutif ; long silver − β·gold isole l'edge
spécifique silver, décorrélé du book → moins dilutif funded.
**Spec UNIQUE :** β = OLS de `win_w_silver` sur `win_w_gold` (plein échantillon, ratio de hedge du facteur commun),
pré-fixé. Spread = silver_overnight − β·gold_overnight (positions superposées même fenêtre, swap-free).
**Métriques :** Sharpe spread, drawdown, **corrélation au book** (gold_trend daily), **ablation funded book+spread
vs book-only** → Δsurvie.
**SUCCÈS FTMO (figé) :** `Δsurvie(book+spread) ≥ −3 pt` (non-dilutif) **ET** corr(spread, gold_trend) < 0.3 (le
drawdown décorrélé bat la dilution solo silver).

## PISTE 3 — Sortie précoce (réduction du temps en position) — GOLD + WTI
**Hypothèse :** l'edge est les 1ères heures post-rollover ; les heures tardives ajoutent du drawdown sans edge.
Sortir plus tôt réduit l'exposition intraday (axe funded) et peut aider la vitesse (axe challenge).
**Spec UNIQUE :** sortie **05:00 UTC** au lieu de 07:00 → fenêtre heures **[23,0,1,2,3,4]** (6 h au lieu de 8,
−25% de temps en position ; le rapport dit la sortie 06:00-07:00 « forgiving », on teste plus tôt). UNE règle.
**Métriques (gold ET WTI) :** drawdown intraday (worst low) réduit ? Sharpe préservé (**≥ 90%** du plein) ?
**ablation funded Δsurvie ET challenge p_pass** vs la version pleine fenêtre.
**SUCCÈS FTMO (figé) :** worst-intraday-low réduit (en magnitude) **ET** Sharpe ≥ 90% du plein **ET**
(`Δsurvie funded` amélioré [moins dilutif] **OU** `p_pass challenge` amélioré).

## Verdict global (figé)
Pour CHAQUE piste : touche-t-elle vraiment l'axe FTMO visé (drawdown cumulé funded OU vitesse challenge),
**OUI/NON, chiffres** ? Une piste qui monte le Sharpe mais ne change ni vitesse ni drawdown cumulé = **ÉCHEC FTMO**
(le noter comme tel). Triplets funded `(survie %, fundedV $, Δsurvie)` et challenge `(p_pass, attempts, p_bust)`
partout. **DSR cumulé (n_trials=160) reporté pour chaque Sharpe positif.** Comparaison explicite aux verdicts solo
(gold/soybean REJET). **Le verdict doit dire : une piste débloque-t-elle l'overnight-drift POUR FTMO, ou la famille
reste-t-elle inadaptée aux deux étages ?** Author≠auditor : si un interstice apparaît, adjuger sans déplacer les seuils.

## Livrable
`STUDY_OVERNIGHT_FTMO_IMPROVE_2026-06-20.md`, branche dédiée, pré-reg figée AVANT résultats, tableaux, triplets,
DSR cumulé. Aucun déploiement, book live + EA intacts.
