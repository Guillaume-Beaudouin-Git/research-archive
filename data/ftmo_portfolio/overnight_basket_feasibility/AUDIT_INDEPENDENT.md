# AUDIT INDÉPENDANT — Panier overnight-drift (gold+silver+WTI±soybean) sur FTMO

**Date :** 2026-06-19 · **Auditeur :** session Claude Code indépendante (author≠auditor, fresh eyes)
**Worktree isolé :** `Algo_claude_basket` (lecture seule sur live/v22/cleanroom/deep_history ; aucun `git`)
**Objet audité :** `STUDY_OVERNIGHT_BASKET_FTMO_2026-06-19.md`, verdict **(c) NON-VIABLE**.
**Environnement de re-run :** `/usr/bin/python3` (numpy 2.0.2, pandas 2.2.3). Tous les scripts `code/`
ré-exécutés ; moteur v2.2 audité (`engine_v22.py`, pin `605f4a4`) réutilisé via chemin absolu MAIN.

---

## VERDICT GLOBAL : **CONFIRM-WITH-CAVEATS**

Le verdict **(c) NON-VIABLE** est **CORRECT et robuste**. L'axe décisif (challenge p_pass < 0.30) se
reproduit au bit près et est invariant à toute fenêtre raisonnable. Le funded est DILUTIF sous toute
fenêtre testée. Les wrappers sont valides, le plus-bas intraday diversifié est calculé correctement
(pas de sous-estimation du risque), et les seuils pré-enregistrés sont appliqués honnêtement.

**MAIS deux réserves matérielles, qui vont toutes deux DANS LE SENS du rejet (l'étude est, si quoi
que ce soit, trop GÉNÉREUSE envers le panier sur l'axe funded) :**

1. **[CAVEAT majeur] La fenêtre de cohortes funded est NON-CANONIQUE et flatte le panier.** Le headline
   « l'agrégation réduit la dilution funded, B4 K=1 Δ−6.8 vs solo −28 » repose sur une fenêtre funded
   **codée en dur `2018-06-01 → 2024-06-30`** (q2_basket.py:39), qui n'est PAS le `FUNDED_WINDOWS`
   canonique du moteur (`config_v22.py:45` = IS 2013-17 + OOS 2020-24). Sur la fenêtre **canonique**,
   le panier B4 K=1 dilue **Δ−26.7** — soit **≈ les solos (Δ−28)**, pas « bien moins ». Le « Δ−6.8 »
   est un artefact de fenêtre (soybean-favorable). Détail §E/§G.

2. **[BUG latent, dormant] `basket_fp.run_campaign` a une `UnboundLocalError` sur `mn1`** (basket_fp.py:35) :
   le garde d'entrée `return dict(..., min_eq=mn1)` référence `mn1` avant assignation. Confirmé reproductible.
   N'a affecté **aucun** chiffre rapporté (les cohortes ne tombent jamais à ≤4 barres de la fin : start
   max idx 3221 / n=3295, distance 73), mais c'est un défaut de correction à corriger. Détail §A.

Aucune de ces réserves ne renverse le verdict. La #1 le **renforce** (funded encore plus dilutif que dit).

---

## Item A — Validité des wrappers : **PASS**

`code/validate_basket.py` ré-exécuté :
- **(ii) book ON + basket OFF = 87.01 %** (accept [86,91]) → **PASS**. Wrapper non-invasif confirmé :
  le `basket_inject` ne perturbe pas le book quand `basket_on=False`/absent.
- **(iii) basket_fp vs moteur barre (book off, basket on)** : K=1.5 → `|Δ| 0.00pt` ; K=3.0 → `|Δ| 0.00pt`
  → **PASS**. Le moteur first-passage est fidèle au moteur barre.
- (iv) intersection exit-morning ∩ book dates = 2598/3962 (65.6 %) — cohérent (le panier trade toutes
  les nuits calendaires ; le book un sous-ensemble).

**Bug latent trouvé (hors gate, dormant) :** `basket_fp.run_campaign` ligne 35 référence `mn1` avant
sa première assignation dans la branche garde-d'entrée. Reproduit en forçant `start ≥ n-5` ou `wall<0`
(`UnboundLocalError: local variable 'mn1' referenced before assignment`). **Impact sur les résultats :
NUL** (vérifié : aucune cohorte challenge/funded n'atteint l'index déclencheur, marge 73 barres). À
corriger (initialiser `mn1` ou retourner sans `min_eq` dans ce garde) pour la robustesse future
(extension OOS jusqu'à la fin de série, ou raccourcissement des données).

## Item B — Plus-bas intraday DIVERSIFIÉ (le cœur technique) : **PASS**

Re-dérivation **indépendante** (recompute from M1→H1, sans appeler `basket_series.build`) :

| panier | worst low (ma re-dérivation, raw, pré-spread) | worst basket_low (étude) | sum-of-mins naïf |
|---|--:|--:|--:|
| B3 (gold+silver+WTI) | **−2.660 %** | −2.670 % | −3.033 % |
| B4 (+soybean) | **−2.562 %** | −2.572 % | −2.583 % |
| B2 (silver+WTI) | **−3.710 %** | −3.720 % | −4.269 % |

- **min-of-summed-paths, pas sum-of-mins** : confirmé. La re-dérivation indépendante donne le même
  −2.6 % (l'écart de 0.01pp = le demi-spread que `basket_series` soustrait en plus). Le plus-bas
  diversifié est bien **moins profond** que le sum-of-mins naïf → la diversification est RÉELLE sur cet axe.
- **Construit sur chemins RAW (non-winsorisés)** : confirmé (le `_low_paths` n'applique pas `_wins`).
- **Soybean rejoint à 01:00** : confirmé correct (lp_23 et lp_0 = NaN → dip 0 avant entrée ; aucune
  contribution 23:00-01:00).
- **Le −2.6 % NE sous-estime PAS le risque par mauvais traitement des NaN.** J'ai testé l'hypothèse
  adverse (un trou de données intra-fenêtre remis à 0 ferait sauter la vraie pire heure d'une sleeve) :
  forward-fill du chemin à travers les trous vs NaN→0 → **0 jour** où NaN→0 sous-estime, worst-day
  **identique** (−2.562 %). Les trous intra-fenêtre sont négligeables (GOLD 1j, SILVER 3j, WTI 17j sur
  des milliers). Le « 286 jours où min-of-summed < sum-of-mins » que j'ai d'abord vu est un artefact de
  MON baseline de comparaison (l'inégalité min(Σ)≥Σ(min) ne tient que si toutes les sleeves sont
  présentes à toutes les heures ; soybean n'en couvre que 6/8), **pas** un défaut du `basket_low`.

→ Le plus-bas diversifié −2.6 % est **correct, reproductible, conservateur (raw)**. Aucun bug.

## Item C — Reproduction per-sleeve : **PASS**

`code/overnight_series.py` ré-exécuté + recompute indépendant (gross, bp/jour, skew) :

| sleeve | gross Sh (étude) | gross Sh (re-run) | gross bp/j | skew | net@2bp | net@3bp |
|---|--:|--:|--:|--:|--:|--:|
| SILVER | 1.45 | **1.46** | 5.38 (vs 5.30) | −0.14 ✓ | 1.01 | 0.75 |
| WTI | 1.09 | **1.10** | 3.56 (vs 3.51) | +0.43 ✓ | 0.61 | 0.34 |
| GOLD | ~asia | 1.81 | 4.64 | +0.31 | 1.01 | 0.59 |
| SOYBEAN | — | 2.48 | 8.77 | +0.40 | 1.96 | 1.68 |

Silver 1.46 / WTI 1.10 reproduisent le rapport (1.45/1.09 ; les µ-écarts viennent du filtre `pos>0` et
de simple-vs-log returns entre l'analyseur Q1 et `overnight_series` — immatériels). Skews exacts.

## Item D — Challenge « pire que les solos » : **PASS**

`code/q2_basket.py` ré-exécuté → **identique au bit près** au `q2_basket.json` stocké.
- **max p_pass sur toutes configs/K = 25.3 %** (B2 K=4, au prix d'un bust 50.1 %) **< 0.30** → NON-VIABLE.
- À **K=1** : vol B3 = 5.8 %, B4 = 4.7 % (vs gold solo ~7 %) → **plus basse** (diversification). p_pass=0 %.
- **Histoire causale (vol basse → plus lent → pire challenge) : SAINE.** Monotone et bidirectionnelle :
  quand K monte, vol monte ET p_pass monte (B3 : 0→1.5→8.4→19.3 %), mais le bust explose en parallèle
  (B3 K4 38.7 %, B2 K4 50.1 %). C'est exactement le compromis « vitesse vs survie » décrit. Le stop
  −2.5 % **nuit** (B3+stop 14.1 % < B3 19.3 % à K4) — cohérent avec « cape un edge déjà trop lent ».

## Item E — Ablation funded (décisive) : **PASS sur les chiffres, CAVEAT sur la fenêtre**

Re-run identique : book-only survie252 **100.0 %**, fundedV **$2144** ; book+B4 K=1 survie **93.2 %**
(Δ−6.8), fundedV $3518 ; book+B3 K=1 survie 84.8 % (Δ−15.2). « Aucun K ne tient les 2 gates » confirmé
(K=1 survit funded mais challenge 0 % ; K≥2 effleure challenge mais funded s'effondre 71→30 %).

**CAVEAT décisif (sensibilité de fenêtre — non documentée dans l'étude) :** le Δ−6.8 dépend de la
fenêtre funded codée en dur `2018-06-01 → 2024-06-30` (q2_basket.py:39), qui **n'est pas** la fenêtre
canonique du moteur. Re-run de l'ablation décisive (book vs book+B4 K=1) sur plusieurs fenêtres :

| fenêtre funded | n | book survie | book+B4 K1 survie | **Δ** |
|---|--:|--:|--:|--:|
| **report (2018-06→2024-06, step 12)** | 132 | 100.0 % | 93.2 % | **−6.8** |
| **canonique `FUNDED_WINDOWS`** (IS 2013-17 + OOS 2020-24) | 191 | 97.9 % | 71.2 % | **−26.7** |
| full 2013-10→2024-06 | 233 | 98.7 % | 74.2 % | **−24.5** |
| OOS-only 2020→2024 | 98 | 99.0 % | 90.8 % | −8.2 |

→ Sur la fenêtre **canonique**, la dilution B4 K=1 est **Δ−26.7 ≈ celle des solos (−28)** : la
« réduction de dilution par l'agrégation » **disparaît largement**. Le Δ−6.8 est l'artefact d'une
fenêtre soybean-favorable (soybean ne commence qu'en 2018-02 ; une fenêtre incluant 2013-17 le sous-
échantillonne ou l'exclut, d'où le choix 2018+). **Conséquence pour le verdict :** AUCUNE — Δ−6.8 est
déjà > −5pt = DILUTIF, et Δ−26.7 est encore plus clairement DILUTIF. Le caveat **renforce** le rejet.

**Cross-check « book-only $2144 == asia/soybean » : NON-VÉRIFIABLE depuis ce worktree** (solos sur
branches non montées). Note : l'état canonique v2.1 (`CANONICAL_AMENDMENT_PENDING.md`) cite une valeur
funded de **$1,204** (mono-stack, regen_all) et mon re-run canonique donne **$1,442** — soit nettement
< $2,144. Le $2,144 est donc spécifique à la fenêtre 2018-2024 et constitue une baseline book
**optimiste**. Le « == asia/soybean » n'est crédible QUE si les solos ont utilisé exactement cette même
fenêtre 2018-2024 ; à confirmer côté branches solo. **Si les solos utilisaient la fenêtre canonique, la
comparaison Δ−6.8-vs-−28 n'est pas apples-to-apples.**

## Item F — Artefact −3.5 % : **PASS (avec micro-nuance de transparence)**

`code/q3_basket.py` ré-exécuté → identique : report-style **−3.5 %** (gross/winsor/inv-vol/commun 1627j),
réaliste B3 **−7.7 %**, B4 −5.8 %, MC stationary-block **5e-pct −13.3 %**, 1er-pct −15.9 % → **perce le
floor −10 %**. Le label « artefact » est juste.

**Ablation à un-ingrédient (la mienne, sur le panier B4) :** partant du −3.5 % et en retournant UN seul
ingrédient à la fois : net2bp →−4.6 %, raw(no-winsor) →−3.6 %, eq-wt →−3.9 %, full-window →−4.0 %,
tout-réaliste B4 →−5.8 %. **Chaque flip aggrave**, donc « artefact » est directionnellement honnête, et
la décomposition ne truque PAS dans le sens du rapport. **Micro-nuance :** le « −7.7 % réaliste » du
headline est le **B3** (3 sleeves) ; le B4 réaliste n'est que −5.8 %. Le −3.5 % (config inverse-vol)
et le −7.7 % ne sont donc pas exactement le même jeu de sleeves — mais la table Q3 affiche les DEUX
explicitement (transparent) et la borne décisive (MC 5e-pct −13.3 %) est sur B3. Si biais il y a, il
est **contre** le panier (B4, le config qui gagne en funded, a un DD plus faible) → favorise le rejet.

## Item G — Discipline de pré-registration : **PASS (avec le caveat E)**

- Challenge : seuils figés VIABLE ≥0.50 / CONDITIONNEL [0.30,0.50) / NON-VIABLE <0.30. Max 25.3 % <0.30
  → NON-VIABLE. **Appliqué honnêtement, aucun déplacement de poteau.**
- Funded : NON-DILUTIF ssi survie ≥ book−0.02 ; DILUTIF ssi < book−0.05. B4 K=1 Δ−6.8 < −5pt →
  **DILUTIF**. **Correctement classé** (et Δ−26.7 canonique l'est a fortiori).
- **Écart de discipline (mineur, à signaler) :** la pré-reg (§Convention triplet, ligne 74) fige
  « cohortes 7j, IS 2013-19 / OOS 2020-26 » pour le challenge mais **ne pin pas explicitement la fenêtre
  funded** ; le code a choisi 2018-2024 (≠ canonique moteur) sans le justifier dans l'étude. Ce n'est
  pas du goalpost-moving sur un SEUIL, mais un **choix de fenêtre non pré-enregistré et non documenté**
  qui happe à flatter l'axe funded. À documenter (ou re-courir en canonique) pour la probité.

## Item H — Calibration du verdict : **PASS**

- **(c) NON-VIABLE est le bon appel.** Il repose sur le challenge (NON-VIABLE, <0.30, suffisant et
  **invariant à la fenêtre** car cohortes IS/OOS 2013-2026) + funded DILUTIF (vrai sous toute fenêtre).
- **Le headline insight (« les 2 étages récompensent l'opposé : diversification aide le funded-drawdown,
  nuit à la vitesse-challenge ») est SUPPORTÉ par les chiffres**, pas une sur-narration : survie funded
  monotone décroissante en K (B4 : 93→71→45 %) ET p_pass challenge monotone croissante en K (B4 :
  0→0.4→9.7→21 %) — relation bidirectionnelle propre, médiée par la vol. **Toutefois**, vu le caveat E,
  la branche « aide le funded » est **plus faible que présentée** : sur la fenêtre canonique, le panier
  n'aide quasi PAS le funded (Δ−26.7 ≈ solos). L'insight reste qualitativement vrai (vol↓ ⇒ DD intraday↓,
  −2.6 % réel) mais son ampleur funded est sur-vendue par la fenêtre 2018-2024.
- **Une lecture « GO conditionnel funded-only » est-elle possible ? NON.** L'étude la concède déjà comme
  « seule nuance positive » (compte déjà-funded, B4 K bas) puis la rejette (pas d'accès, dilutif,
  marge stackée, WTI swap-fragile). Mon caveat de fenêtre la rend **encore moins** défendable : sur la
  fenêtre canonique, B4 K=1 dilue autant que les solos → même le cadre « sleeve de revenu sur compte
  funded » ne survit pas à un funded-window honnête. La nuance est donc, au mieux, plus faible que dite.

---

## Synthèse des items

| Item | Sujet | Verdict |
|---|---|---|
| A | Validité wrappers (ii)/(iii) | **PASS** (+ bug latent dormant `mn1`) |
| B | Plus-bas intraday diversifié | **PASS** (correct, conservateur, pas de sous-estimation) |
| C | Reproduction per-sleeve | **PASS** (silver 1.46, WTI 1.10) |
| D | Challenge < 0.30 / vol plus basse | **PASS** (max 25.3 %, histoire causale saine) |
| E | Ablation funded décisive | **PASS-chiffres / CAVEAT fenêtre** (Δ−6.8 → Δ−26.7 canonique) |
| F | Artefact −3.5 % | **PASS** (micro-nuance B3-vs-B4 transparente) |
| G | Discipline pré-reg | **PASS** (caveat : fenêtre funded non pré-enregistrée) |
| H | Calibration verdict | **PASS** (insight funded sur-vendu, verdict correct) |

## Défauts/sur-affirmations nommés précisément

1. **`basket_fp.run_campaign` (basket_fp.py:35) — `UnboundLocalError` sur `mn1`** dans le garde
   d'entrée (`min_eq=mn1` avant assignation). Reproductible. Impact résultats = nul (dormant). À corriger.
2. **Fenêtre funded non-canonique codée en dur** (`q2_basket.py:39` `2018-06-01→2024-06-30` ≠
   `config_v22.FUNDED_WINDOWS`). Produit Δ−6.8 ; la fenêtre canonique donne **Δ−26.7** (≈ solos −28).
   La sur-affirmation à corriger : « l'agrégation réduit la dilution funded bien moins que les solos
   (Δ−6.8 vs −28) » → vrai SEULEMENT sur 2018-2024 ; faux/marginal sur la fenêtre canonique.
3. **Cross-check « book-only $2144 == asia/soybean »** non vérifiable ici et incohérent avec l'état
   canonique v2.1 ($1,204) / mon re-run canonique ($1,442) ; le $2,144 est une baseline book optimiste
   propre à la fenêtre 2018-2024. À reconfirmer que les solos ont la même fenêtre, sinon la comparaison
   Δ n'est pas apples-to-apples.
4. **Q4(b) `EDGE_BP[GOLD]=5.0` hardcodé** alors que le gross mesuré = 4.64 bp/j (sur-estimation mineure ;
   conclusion « WTI seul est wipé par 3.5bp swap » inchangée).

## Conclusion

**CONFIRM-WITH-CAVEATS.** Le verdict **(c) NON-VIABLE** tient et est bien étayé sur l'axe décisif
(challenge < 0.30, invariant à la fenêtre, reproduit au bit près) et sur le funded (DILUTIF sous toute
fenêtre). La méthodologie centrale (wrappers validés, plus-bas diversifié correct et conservateur,
décomposition −3.5 % honnête, seuils non déplacés) est saine. Les deux réserves matérielles — bug
latent dormant et **fenêtre funded non-canonique qui flatte la branche funded** — ne renversent pas le
verdict ; la seconde le **renforce** (le panier ne « bat » quasi pas la dilution solo sur une fenêtre
honnête). L'unique sur-affirmation à amender est la magnitude du bénéfice funded de l'agrégation
(Δ−6.8 → Δ−26.7 canonique). Aucun chemin « GO conditionnel funded-only » n'est défendable.
