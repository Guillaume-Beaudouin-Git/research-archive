# PRÉ-REGISTRATION — ASIA_23_8 en FUNDED-only avec stop intraday (suite)

**Horodatage (committé AVANT tout résultat) :** 2026-06-19
**Branche :** `claude/asia-23-8-funded` · **Auteur :** session Claude Code (author≠auditor)
**Cadre :** RECHERCHE PURE, sandboxée. AUCUN déploiement. AUCUN toucher au book live
(`ftmo_live/`, EA gelé, FLAT, compte armé). Lecture seule. **Règle d'or : seuils figés, non
ajustables après résultats.**

## 0. Contexte et question
Le verdict CHALLENGE est acquis et accepté : **NON-VIABLE** (cible +10 % incompatible avec sizing
survivable + percement intraday du daily −5 %). On ne force PAS le challenge.
**Nouvelle question, format différent :** ASIA_23_8 a-t-elle sa place en **FUNDED** — où il n'y a
**PAS de cible de profit**, seulement les barrières de risque (daily −5 %, max −10 % statique) ? La
lenteur cesse d'être un handicap sans cible (logique ORB : OFF challenge, ON funded).
**Risque structurel identifié a priori (à mesurer, pas à supposer) :** le stop intraday corrige le
percement du daily −5 %, mais le **floor statique −10 % peut être percé par un saignement multi-mois**
en régime mort (ASIA SR 2018 ≈ −2.2 → perte ~15 % à K=1) qu'aucun stop intraday n'adresse.

## ⚠️ ANTI-SUR-RECHERCHE (plafond DUR)
- **≤ 5 variantes au total**, listées et figées ci-dessous. J'en utilise **4** (réserve 1, discipline).
- **DSR pénalise explicitement** n_trials = **100** = 90 (trials due-diligence d'origine) + overlays
  de l'étude challenge + ces 4 variantes funded. Tout edge doit franchir ce DSR élevé.
- **Si aucune des 4 variantes ne passe (survie ET edge), J'ARRÊTE et je rapporte « rien ne passe ».**
  Je ne testerai PAS de 6e variante (ni régime-overlay, ni 4e niveau de stop) pour « trouver quelque
  chose ». Si l'idée régime-filter émerge, elle relève d'un NOUVEAU pré-enregistrement en session fraîche.

### Les 4 variantes FIGÉES (sizing K=1.0 fixé a priori, ~6.8 % vol annu compte)
1. **V_nostop** — funded, AUCUN stop intraday (référence : survie + plafond de Sharpe).
2. **V_stop_1.5** — stop intraday dur à **−1.5 %** (compte) : sortie si la position franchit −1.5 %.
3. **V_stop_2.5** — stop intraday dur à **−2.5 %**.
4. **V_stop_3.5** — stop intraday dur à **−3.5 %**.
*(5e variante : RÉSERVÉE, NON UTILISÉE.)*
K=0.5 et K=1.5 rapportés **uniquement en sensibilité de risque** (le Sharpe est ~invariant en K ;
seules survie/DD/rendement scalent) — **PAS** des recherches d'edge supplémentaires, **pas** comptés
en n_trials.

### Modèle du stop (transform au niveau SÉRIE, moteur INCHANGÉ)
Le stop −X % est en fraction de compte (à K=1). Par jour : `triggered = (K·low_base ≤ −X)` où
`low_base` = plus-bas intraday MTM de la fenêtre (bornes H1, net du demi-spread, déjà calculé/validé
en `asia_series`). Si déclenché : `realized = −X` (sortie au stop, le reste de la fenêtre est manqué) ;
sinon `realized = K·net_base`. `stopped_low = −X si déclenché sinon K·low_base`. On injecte
(`stopped_net`, `stopped_low`) dans le moteur funded v2.2 audité (`run_funded`, réutilisé read-only,
wrapper déjà validé ASIA-OFF→87.01) — **le moteur n'est pas modifié**, le stop est une transformation
de la série quotidienne (indépendante de l'état du compte, donc applicable hors-moteur).
Mécanisme d'érosion à mesurer : un jour où `low ≤ −X` mais `close > −X` = le stop sort sur une bougie
qui se retourne → alpha rendu = `K·net − (−X)` quand positif. Quantifié exactement.

### Cohortes funded (INCLUENT le régime mort 2018-2019 — délibéré)
Démarrages **tous les 21 j-bourse** sur **tout l'échantillon 2013-10-01 → 2025-06-30** (laisse 12 mois
pour l'horizon 252 j). Le `FUNDED_WINDOWS` de la spec saute 2018-2019 ; je ne le fais PAS (sinon survie
artificiellement flattée). Horizons : **126 j (6 mois)** et **252 j (12 mois)**. Moteur funded = pas de
cible, daily −5 %, floor statique −10 % (9000), retraits tous les 14 j-bourse (split trader 0.8).

## Q1 — Format funded (pas de cible)
Survie d'ASIA standalone (book OFF) en funded à K=1, **sans stop** : p(survie 6/12 mois sans buster),
rendement annualisé net (0.8·(retraits+résidu), annualisé), maxDD. Montre le risque résiduel
(percement intraday + saignement régime-mort).

## Q2 — Stop intraday (LE point qui décide)
Pour chaque niveau X ∈ {1.5, 2.5, 3.5} % :
- **Survie** : p(survie 6/12 mois), rendement annualisé net, maxDD (triplet funded).
- **Érosion de l'edge** : Sharpe net APRÈS stop (full + OOS), **DSR(n_trials=100)**, mean bp/j, % de
  jours déclenchés, **alpha rendu** (somme des `K·net−(−X)>0` sur jours déclenchés). Hypothèse à
  RÉFUTER : le stop mange l'alpha (sort sur les bougies qui se retournent). Quantifier où l'edge
  disparaît.

## Q3 — Apport au book FUNDED vs sleeve or-trend
Ablation funded : **book funded actuel** (CFG_FUNDED : gold_trend ON, ORB ON, vm=1) vs **+ ASIA stoppée
au meilleur niveau survivant**. Mesurer : Δp(survie 12 mois), ρ(ASIA stoppée, gold_trend daily), marge
métal cumulée sous Swing (XAU 1:9 ; deux jambes gold + ASIA — passe ou casse le cap 60 % ?), effet net
sur Sharpe/survie du book funded.

## Seuils GO/NO-GO (FIGÉS)
- **SURVIE** d'un niveau : p(survie 12 mois) **≥ 0.90** à K=1 (≤10 %/an de bust) ET ne réduit pas la
  survie du book funded de référence.
- **EDGE PRÉSERVÉ** : Sharpe stoppé (full) **≥ 0.70** (plancher RESEARCH_PASS) ET **DSR ≥ 0.90** ET
  mean stoppé > 0.
- **VERDICT :**
  - **(a) VIABLE funded-only** : ∃ niveau de stop avec SURVIE **ET** EDGE PRÉSERVÉ **ET** Q3 apporte
    (Δp_survie ≥ −bruit ET marge ≤ 60 % ET ρ < 0.5) → candidate funded-only, mérite paper-trade.
  - **(b) NON-VIABLE (le stop mange l'edge)** : la survie (p≥0.90) n'est atteinte qu'à des niveaux qui
    tuent l'edge (Sharpe < 0.70) — survie et edge incompatibles sur les 3 niveaux.
  - **(c) REJET (survit + edge mais sans apport)** : un niveau donne survie+edge, mais Q3 montre aucun
    apport book (breach marge OU dilutif OU redondant ρ≥0.5).
  - **Cas saignement** : si la survie échoue par le floor −10 % statique (bleed multi-mois) et NON par
    le daily −5 %, le rapporter explicitement — c'est un résultat valide (le stop n'adresse pas le bleed).
- **Probité (author≠auditor)** : si un interstice de seuil réapparaît, j'adjuge sans déplacer aucun
  seuil et je le signale.

## Livrable
`STUDY_ASIA_23_8_FUNDED_2026-06-19.md`, branche dédiée, pré-registration committée AVANT résultats.
Triplets/équivalents funded, tableaux, ablation. Aucun déploiement.

### Lessons applicables
- L30/L36 (swap pré-tue les primes tenues) : N/A ici, ASIA reste swap-free (Q4 étude précédente).
- L20/L21 (DSR obligatoire n_mod≥2 ; SR catégorie single-instrument 0.8-2.0) : DSR n_trials=100.
- L24 (forme de distribution vs barrière ; lumpy mal adapté) : le funded retire la barrière-cible mais
  garde le floor statique — c'est l'axe testé.
- L15 (overlays régime sur SR>1 : lift sub-seuil) : raison de NE PAS ajouter un régime-overlay ici.
