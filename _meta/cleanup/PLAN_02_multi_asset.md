# Plan de rangement — `Multi_Asset/research/active/` (72 dossiers)

**2026-09-08. PLAN SEULEMENT — aucun fichier déplacé, modifié ni supprimé.** Lecture complète des
rapports principaux des 72 dossiers (`git ls-files`, en-têtes/verdicts des `RESULTS.md` /
`RAPPORT.md` / `RESULTATS.md` équivalents), vérification des tailles trackées par git et des
citations croisées (`grep -rl` sur tout `.md` du dépôt, plus vérification ciblée de
`tools/check_register_integrity.py`, `CLAUDE.md` et `_meta/research_active.md`).

## Deux constats préalables qui changent le diagnostic

1. **`tools/check_register_integrity.py` ne vérifie qu'un seul fichier** :
   `PropFirms/ftmo/program_2026-06/positive_dsr_register/REGISTER.md`. Aucun des 72 dossiers n'y
   est cité (vérifié par grep exhaustif) — **déplacer n'importe lequel des 72 ne casse PAS ce
   contrôle**. La contrainte dure de la mission ne s'applique donc à aucun cas ici. En revanche,
   **47 des 72 dossiers sont cités dans `_meta/research_active.md`** (l'index narratif, non
   vérifié par le script) et un nombre variable (0 à 14) le sont dans d'autres rapports du dépôt —
   ce sont des citations de *confort de lecture*, pas de contrôle d'intégrité, mais un
   déplacement doit les corriger pour rester honnête (voir §Exécution en fin de document).
2. **Il n'y a pas de problème de poids git.** `du -sh` sur certains dossiers affiche des
   tailles impressionnantes (`mr_intraday_grille_2026-08` 656 Mo, `mr_univers_complet_2026-08`
   331 Mo, `overnight_futures_2026-07` 161 Mo) — mais ce sont des **caches locaux gitignorés**.
   Le total réellement **tracké par git** dans tout `research/active/` est **24 Mo**, et seuls
   **2 fichiers `.parquet`** y sont trackés (`growth_engine_2026-07/audit_growth_returns.parquet`,
   91 Ko ; `swapkilled_futures_2026-07/audit_sleeve_returns.parquet`, 19 Ko) — négligeables. Le
   problème du dépôt n'est donc **pas la donnée**, c'est la **taxonomie** : 72 dossiers étiquetés
   « actifs » quand la quasi-totalité a rendu un verdict.

## Vue d'ensemble par grappe

Les 72 dossiers ne sont pas 72 sujets indépendants : ils forment **10 grappes thématiques**
cohérentes (un chantier étalé sur plusieurs sessions cite presque toujours le précédent). Masquer
cette structure derrière une liste plate de 72 entrées est la première cause de « ça a l'air en
désordre ». Le tableau ci-dessous porte une colonne **Grappe** pour cette raison.

| Grappe | Contenu | N | Statut dominant |
|---|---|--:|---|
| **A. Programme macro (sept. 2026)** | 6 rounds + revue indépendante + 6 tests dérivés | 13 | CLOS, série cohérente |
| **B. Décision desk oct. 2026** | Go/no-go ORB + overnight, en cours | 4 | **VIVANT** |
| **C. Risque du compte funded** | Simulations de ruine/bust sur le book réellement déployé | 4 | CLOS |
| **D. Audit du ledger ORB / NQ** | Chaîne d'audits qui a mené à l'armement du sleeve ORB funded | 7 | CLOS (1 contradiction) |
| **E. Sleeves overnight / or / gap** | Audits et re-screenings des sleeves gold/J1/overnight | 9 | CLOS |
| **F. Familles MR / dose-réponse intraday** | Grilles exhaustives MR + contrôles de placebo/régime | 11 | CLOS, famille MORTE |
| **G. Fondations véhicule/coût/screening** | Documents de référence cités par presque tout le reste | 11 | CLOS, **très cités** |
| **H. Stat-arb / paires** | Cointégration et facteurs multivariés sur CFD | 3 | CLOS |
| **I. Compte perso IBKR (futures)** | Le book personnel réellement construit | 5 | CLOS, **live** |
| **J. Mur temporel / sizing** | Économie de la barrière FTMO et du sizing phase 2 | 5 | CLOS (1 inachevé) |

---

## Tableau complet (72 dossiers)

Colonnes : **Fichiers** = fichiers trackés git. **Cité** = cité hors de son propre dossier dans un
`.md` du dépôt (nombre d'occurrences externes). **Action** : ARCHIVER / GARDER ACTIF / FUSIONNER /
regroupement de grappe.

### Grappe A — Programme macro 2026-09 (13 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `macro_score_2026-09` | Round 1 : score macro cross-sectionnel REJETÉ avant backtest (IR trop faible) ; la famille événementielle intraday-flat devient le projet | CLOS | 7 | 6 | ARCHIVER (bloc A) |
| `macro_round2_2026-09` | 5 axes triés : B3 prioritaire puis **auto-corrigé mort** (déjà testé ailleurs, L48), C reclassé outil, 2 hypothèses réfutées | CLOS | 19 | 7 | ARCHIVER (bloc A) |
| `macro_round3_2026-09` | 4 axes : 3/4 ont pour maison IBKR et non FTMO ; test §6.4 confirme que B1 (month-end) survit au régime de corrélation post-2021 | CLOS | 7 | 3 | ARCHIVER (bloc A) |
| `macro_round4_2026-09` | Génération d'idées hors terrain couvert (liquidité nette, etc.), conception seule | CLOS | 1 | 2 | ARCHIVER (bloc A) |
| `macro_round5_2026-09` | Idées issues de la littérature académique de référence, conception seule | CLOS | 1 | 0 | ARCHIVER (bloc A) |
| `macro_round6_2026-09` | Ré-ouverture n°1 : l'arithmétique de coût confirme Ranaldo bilatéral en gross — teste dans `ranaldo_multipaires` | CLOS | 2 | 1 | ARCHIVER (bloc A) |
| `macro_review_2026-09` | Revue indépendante des rounds 1-3 : le raisonnement de breadth tient, une divergence trouvée et documentée | CLOS | 1 | 2 | ARCHIVER (bloc A) |
| `flag_calendaire_2026-09` | Balayage de 51 cellules d'exposition : 0 franchit Šidák — rien de plus qu'un vendredi cosmétique | CLOS | 9 | 0 | ARCHIVER (bloc A) |
| `eia_surprise_2026-09` | Hypothèse pré-enregistrée REJETÉE, kill mécanique (437 événements) | CLOS | 4 | 0 | ARCHIVER (bloc A) |
| `naaim_positioning_2026-09` | Résidu orthogonalisé NAAIM : KILL, excédent indistinguable de zéro aux deux horizons | CLOS | 2 | 0 | ARCHIVER (bloc A) |
| `net_liquidity_2026-09` | Effet de surface (t 2,67) REJETÉ : c'est du bêta récolté par un taux de base asymétrique | CLOS | 7 | 0 | ARCHIVER (bloc A) |
| `pretests_gratuits_2026-09` | 2 pré-tests gratuits : prémisse du nowcast survit sur l'inflation seule ; le choix de contrat IBKR s'inverse | CLOS | 1 | 0 | ARCHIVER (bloc A) |
| `ranaldo_multipaires_2026-09` | KILL DÉFINITIF sur 7 majeures : l'effet n'est pas général (3/7 significatives), agrégation dégrade | CLOS | 3 | 0 | ARCHIVER (bloc A) |

### Grappe B — Décision desk octobre 2026 (4 dossiers, VIVANTE)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `desk_orb_2026-09` | Dossier de décision go/no-go ORB funded pour octobre — sleeve armée en prod, décision **pas encore tranchée** dans ce doc | **VIVANT** | 12 | 0 | **GARDER ACTIF** |
| `desk_overnight_2026-09` | « Garder lundi ET mardi » — verdict d'ouverture donné, mais dossier de décision explicitement lié à `desk_orb` (agents parallèles) | **VIVANT** | 10 | 1 | **GARDER ACTIF** |
| `macro_context_2026-09` | Cadre macro explicatif (frise des régimes 2010-2026) en appui de la décision d'octobre, non un verdict de stratégie | **VIVANT** | 1 | 2 | **GARDER ACTIF** |
| `regime_diagnostic_2026-09` | Diagnostic de régime funded : rupture 2014-2015 vient de l'ORB, non détectable ex ante — nourrit la décision d'octobre | **VIVANT** | 6 | 1 | **GARDER ACTIF** |

### Grappe C — Risque du compte funded (4 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `funded_5ans_2026-09` | Zéro bust journalier sur toutes les cohortes 6 mois→3 ans ; tous les busts passent par le plancher statique | CLOS | 1 | 1 | ARCHIVER (mis en avant, cf. infra) |
| `bust_intraday_2026-09` | Complète le précédent au minute-par-minute : zéro franchissement intraday, pire excursion 44 % de la barrière | CLOS | 2 | 0 | ARCHIVER (mis en avant, cf. infra) |
| `funded_reference_2026-09` | Consolidation de 3 études de périmètres différents en une table de chiffres de référence unique | CLOS | 1 | 0 | ARCHIVER (référence utile, à indexer) |
| `funded_1y_mono_2026-08` | Analyse de risque (retraits/DD/ruine) sur trajectoires déjà simulées, book MONO déployé | CLOS | 25 | 7 | ARCHIVER (bloc C) |

### Grappe D — Audit du ledger ORB / NQ funded (7 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `audit_entree_109_2026-08` | Ambiguïté d'entrée = biais PESSIMISTE (pas optimiste comme supposé), 14.7-27.4 % des trades | CLOS | 32 | 2 | ARCHIVER (bloc D) |
| `audit_ledger_orb_2026-08` | Le vrai tueur est le spread/microstructure, pas le gap d'entrée/sortie ; SHORT échoue même à coût nul | CLOS | 19 | 1 | ARCHIVER (bloc D) |
| `audit_micro_orb_2026-08` | Le compteur de jours micro-ORB reproduit exactement les ancres du moteur committé (462/462 cohortes) | CLOS | 11 | 3 | ARCHIVER (bloc D) |
| `audit_moteur_bracket_2026-08` | Biais de départage intra-barre mesuré, éliminable ; marché réel dilue l'artefact d'un facteur 6-7× | CLOS | 10 | 10 | ARCHIVER (bloc D) |
| `audit_reconcile_2026-08` | Incident opérationnel du 2026-08-21 (résidu -$23,11) diagnostiqué : sleeve ORB funded non modélisée dans le pipeline | CLOS | 1 | 0 | **HORS TAXONOMIE — voir cas embarrassants** |
| `orb_cost_funded_2026-08` | Verdict propre = ORB_KILL (t sous 2.0 même corrigé) — **mais le sleeve est armée en production** | CLOS | 27 | 10 | ARCHIVER — **voir cas embarrassants** |
| `orb_variants_2026-08` | 37 variantes balayées : la spec déployée est proche du haut d'un nuage plat, rien ne bat de façon robuste | CLOS | 12 | 1 | ARCHIVER (bloc D) |

### Grappe E — Sleeves overnight / or / gap (9 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `audit_sleeve_gold_2026-08` | Dead-zone exacte mécaniquement, fausse économiquement : filtre qui s'auto-finance, la sleeve n'a plus d'edge net | CLOS | 1 | 2 | ARCHIVER (bloc E) |
| `audit_sleeve_j1_2026-08` | J1 n'est pas une sleeve : long USDJPY vol-targeté à 65 %, identique à un long inconditionnel (Δp = +0,00) | CLOS | 9 | 1 | ARCHIVER (bloc E) |
| `gap_pattern_rehab_2026-07` | DSR corrigé (1.000) mais REJECTED quand même : 51 % du P&L de S035 vient de fourchettes quotidiennes nulles | CLOS | 19 | 2 | ARCHIVER (bloc E) |
| `gold_cpi_eve_2026-08` | Test confirmatoire sur 232 événements : REJETÉ (règle R4), mais dates BLS validées à 100 % | CLOS | 19 | 5 | ARCHIVER (bloc E) |
| `overnight_sleeve_reopen_2026-08` | Ré-ouverture justifiée (géométrie+véhicule) mais **UNDERPOWERED**, pas PASS pas REJECTED | CLOS | 14 | 6 | ARCHIVER (bloc E) |
| `overnight_vs_intraday_2026-08` | Répond à la question du propriétaire du compte (« pourquoi sort-on en journée ? ») avec le tableau demandé | CLOS | 28 | 1 | ARCHIVER (bloc E) |
| `regold_funnel_2026-08` | Re-passage de l'écran or au coût mesuré (1.84 vs 3.50 bps de catalogue) | CLOS | 13 | 2 | ARCHIVER (bloc E) |
| `rollover_dodge_2026-08` | KILL : décaler l'entrée après le rollover ne sauve pas la sleeve | CLOS | 18 | 1 | ARCHIVER (bloc E) |
| `two_sided_axis_2026-08` | Axe du signe FERMÉ structurellement : le différentiel de swap est 89 % du taux sans risque | CLOS | 26 | 3 | ARCHIVER (bloc E) |

### Grappe F — Familles MR / dose-réponse intraday, MORTES (11 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `ath_regime_review_2026-08` | ATH = état le plus sûr mais REJECTED (L54 reproduite), conditionneur = proxy de vol dégradé | CLOS | 24 | 7 | ARCHIVER (bloc F) |
| `close_continuation_gold_subwindows_2026-08` | Deux tests indépendants pré-enregistrés, verdicts lus dans la grille figée | CLOS | 7 | 5 | ARCHIVER (bloc F) |
| `close_momentum_dose_2026-08` | REJECTED : courbe de dose plate, contrôle négatif XAUUSD seul monotone (sens inverse à l'attendu) | CLOS | 7 | 3 | ARCHIVER (bloc F) |
| `cross_conditioning_2026-08` | Conditionnement croisé de deux edges sous-puissants, verdict pré-enregistré rendu | CLOS | 6 | 3 | ARCHIVER (bloc F) |
| `forced_flow_cooccurrence_2026-08` | REJECTED : courbe plate une fois retirés 2 confondants exposés par le protocole lui-même | CLOS | 6 | 3 | ARCHIVER (bloc F) |
| `momentum_intraday_2026-08` | Famille MORTE comme sa sœur MR : 341 cellules, 0 franchit Šidák (N cumulé 1867) | CLOS | 13 | 1 | ARCHIVER (bloc F) |
| `mr_grille_suite_2026-08` | Famille toujours morte + 2ᵉ démonstration indépendante du piège de placebo (faux positifs cette fois) | CLOS | 18 | 5 | ARCHIVER (bloc F) — **cache local 656 Mo, gitignoré** |
| `mr_intraday_grille_2026-08` | Famille morte, 396 cellules, t moyen -1.21 ; artefact de mesure partiellement expliqué | CLOS | 10 | 10 | ARCHIVER (bloc F) — **cache local 656 Mo, gitignoré** |
| `mr_stress_conditional_2026-08` | REJECTED : le profil par quantile de stress est PLAT, pas monotone comme Nagel le prédit | CLOS | 7 | 4 | ARCHIVER (bloc F) |
| `mr_timezone_repair_2026-08` | REJECTED sur les 3 indices US ; GER40 vit entièrement dans les 5 min de l'auction Xetra | CLOS | 6 | 10 | ARCHIVER (bloc F) |
| `mr_univers_complet_2026-08` | Famille reste morte, univers complété (FX crosses, énergie, JP225) | CLOS | 12 | 6 | ARCHIVER (bloc F) — **cache local 331 Mo, gitignoré** |

### Grappe G — Fondations véhicule / coût / screening, TRÈS CITÉES (11 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `cost_denominator_2026-07` | Découvre 2 tables de coûts incompatibles (or sur-pénalisé 1,9×) — **document racine du coût réel** | CLOS | 1 | **12** | ARCHIVER, **mettre en avant** |
| `edge_inventory_2026-07` | 118 edges mesurés catalogués, dont 9 à t≥3 tués pour une raison autre que le signal | CLOS | 6 | **8** | ARCHIVER, **mettre en avant** |
| `month_end_vehicle_2026-07` | B1 capturable à 93 % sur futures CME — mais ne pas acheter de propfirm, le lot minimum tient dans le capital perso (L53) | CLOS | 9 | **11** | ARCHIVER, **mettre en avant** |
| `reaudit_vehicule_2026-08` | Sur 118 edges, 74 morts mécaniquement (fermés), 11 vivent potentiellement sur véhicule futures | CLOS | 18 | 8 | ARCHIVER, **mettre en avant** |
| `gross_surface_map_2026-08` | 8695 cellules balayées, vraie queue statistique mais shortlist économique VIDE — réplique L43 indépendamment | CLOS | 24 | 6 | ARCHIVER, **mettre en avant** |
| `exogenous_predictors_2026-08` | 241 cellules post-2021, 0 clôt le gate économique — 3ᵉ réplication indépendante du ratio 0.34-0.38 | CLOS | 24 | 4 | ARCHIVER (bloc G) |
| `marginal_admission_2026-08` | Sur 118 edges, 29 seulement atteignables par un test marginal — critère de portefeuille, pas de signal | CLOS | 16 | 1 | ARCHIVER (bloc G) |
| `strategy_taxonomy_2026-08` | Taxonomie d'hypothèses par profil de distribution, screening conceptuel (N0, 0 backtest) | CLOS | 1 | 2 | ARCHIVER (bloc G) |
| `literature_review_2026-08` | Audit de 2 verdicts bloquants (MR indices, L43) + revue de littérature orientée mécanisme | CLOS | 1 | 2 | ARCHIVER (bloc G) |
| `literature_sweep_2026-08` | Revue de littérature hors pairs/statarb/mur temporel, 0 essai consommé | CLOS | 1 | 3 | ARCHIVER (bloc G) |
| `carto_reouverture_2026-08` | Cartographie partielle des pistes rouvrables — **agent mort en session, couverture avouée incomplète** | CLOS (partiel) | 2 | 2 | ARCHIVER — **voir cas embarrassants** |

### Grappe H — Stat-arb / paires sur CFD (3 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `decorrelated_sleeves_2026-07` | Vérification indépendante (auteur≠auditeur) : les 3 verdicts confirmés, 2 renforcés | CLOS | 58 | 4 | ARCHIVER (bloc H), le plus abouti méthodologiquement des trois |
| `pairs_cointegration_2026-08` | REJECTED, famille fermée sur ce véhicule (deux verdicts distincts, kill nature documentée) | CLOS | 7 | 9 | ARCHIVER (bloc H) |
| `statarb_multivariate_2026-08` | 3 branches, toutes REJECTED (Sharpe brut <0.70, R<1.5, ou walk-forward 1-2/5 folds) | CLOS | 11 | 4 | ARCHIVER (bloc H) |

### Grappe I — Compte personnel IBKR, futures (5 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `growth_engine_2026-07` | **Livre final** : trend+bonds SR 1.02, corr 0.01 — le book personnel réellement construit | CLOS | 9 | 4 | ARCHIVER, **mettre en avant en priorité** |
| `overnight_futures_2026-07` | 1 sleeve/4 survit au passage CFD→futures ; découvre L56/L57 (horloge d'échange, coût fixe) | CLOS | 40 | 14 | ARCHIVER, **mettre en avant** |
| `swapkilled_futures_2026-07` | H9 confirmé, **H4 tué en roll-artefact** — son propre `DEPLOYMENT_PLAN.md` (14 % H4) est donc caduc | CLOS | 21 | 3 | **FUSIONNER** (provenance) avec `growth_engine_2026-07` — voir cas embarrassants |
| `treasury_auction_2026-07` | REJECTED — cost-dead & underpowered, non redondant avec B1 mais tué ailleurs | CLOS | 10 | 5 | ARCHIVER (bloc I) |
| `prefomc_drift_2026-07` | REJECTED sur split de régime (L31), après avoir corrigé une troncature d'échantillon accidentelle | CLOS | 1 | 2 | ARCHIVER (bloc I) |

### Grappe J — Mur temporel / sizing phase 2 (5 dossiers)

| Dossier | Verdict de l'étude | Statut | Fich. | Cité | Action |
|---|---|---|--:|--:|---|
| `wall_economics_2026-08` | Prix le mur de 91 jours : passer à 182j vaut +5,09 pt de p(campagne), Pace indistinguable de zéro | CLOS | 16 | 4 | ARCHIVER, **mettre en avant** |
| `wall_decision_2026-08` | Complète le précédent (canal Pace agrégé + V audité), 3 findings ordonnés par poids de décision | CLOS | 36 | 2 | ARCHIVER, **mettre en avant** |
| `cohort_clustering_2026-08` | Pas de clustering temporel au-delà du chevauchement des cohortes (placebo clusterise MOINS) | CLOS | 39 | 1 | ARCHIVER (bloc J) |
| `regime_overlay_ftmo_2026-07` | REJECTED : l'overlay est un dé-levier déguisé, pire que le `vm` déjà existant | CLOS | 8 | 8 | ARCHIVER (bloc J) |
| `phase2_sizing_2026-08` | **Code + 8 tables de résultats, ZÉRO rapport écrit** — sert de harnais réutilisé par `cohort_clustering_2026-08` | **INACHEVÉ** | 19 | 2 | **GARDER, documenter d'abord** — voir cas embarrassants |

---

## À mettre en avant (ce qu'un recruteur devrait voir en premier)

Par ordre de priorité de lecture :

1. **`Multi_Asset/README.md`** (déjà narratif, à vérifier qu'il pointe vers les 4 items suivants).
2. **`growth_engine_2026-07`** — le livre personnel réellement construit (trend + bond month-end,
   SR combiné 1.02, corrélation 0.01). C'est la seule étude de cette liste qui débouche sur un
   **produit fini et déployé**, pas seulement un verdict. À citer en tête de tout dossier candidat
   à un entretien.
3. **La chaîne `cost_denominator_2026-07` → `edge_inventory_2026-07` → `reaudit_vehicule_2026-08`
   → `month_end_vehicle_2026-07`** — la colonne vertébrale méthodologique du dépôt : un audit du
   dénominateur de coût, un inventaire exhaustif de 118 essais déjà mesurés, un ré-audit
   systématique par nature de kill (mécanique/véhicule/coût/puissance/géométrie), et une étude de
   cas qui applique tout cela à une trouvaille réelle (B1 sur IBKR). C'est le meilleur argumentaire
   « méthode » du dépôt — plus convaincant que n'importe quel Sharpe individuel.
4. **`gross_surface_map_2026-08`** — 8695 cellules balayées, une vraie queue statistique
   documentée, une shortlist économique explicitement VIDE, et une réplication indépendante d'une
   leçon gravée (L43) par une méthode totalement différente. Démontre la discipline « ne pas se
   laisser convaincre par son propre bruit ».
5. **Le programme macro complet (grappe A, 13 dossiers)** — voir section dédiée ci-dessous : à
   regrouper, puis à indexer en haut de la table des matières comme *étude de cas de méthode*.
6. **`funded_5ans_2026-09` + `bust_intraday_2026-09`** — les deux études les plus récentes,
   rigoureuses et lisibles en 30 secondes (zéro bust journalier, mesuré minute par minute).
   Bon point d'entrée court pour un lecteur pressé.
7. **`wall_economics_2026-08` + `wall_decision_2026-08`** — exemple propre de recherche
   actionnable qui chiffre une décision (+5,09 pt de p(campagne) pour un changement de paramètre
   à coût nul).

### Le programme macro (grappe A) : faut-il un dossier parent unique ?

**Oui, sans hésitation.** Les 13 dossiers ne sont pas 13 sujets — c'est **une seule investigation
en 7 étapes** (score → round2 → round3 → round4/5 en parallèle → round6 → revue indépendante) plus
**6 tests d'exécution** dérivés de ces étapes (`flag_calendaire`, `eia_surprise`,
`naaim_positioning`, `net_liquidity`, `pretests_gratuits`, `ranaldo_multipaires`). Preuves de
cohérence trouvées dans les rapports eux-mêmes : `macro_round3` cite `macro_score_2026-09` et
`macro_review_2026-09` ; `macro_round4`/`macro_round5` listent explicitement les dossiers déjà lus
pour éviter les doublons ; `macro_round6` teste l'hypothèse que `ranaldo_multipaires` exécute ;
`macro_round2` **s'auto-corrige** en réalisant que son axe B3 prioritaire était déjà mort ailleurs
(exactement la faute L48 qu'il nomme lui-même). C'est un exemple rare et montrable de discipline
scientifique en temps réel — mais **seulement s'il est présenté comme UN programme**, pas comme
13 lignes dans une liste de 72. Éparpillé, il se lit comme du bruit ; regroupé avec un README
d'une page qui raconte la séquence, il se lit comme une preuve de méthode.

**Recommandation concrète (à exécuter plus tard, pas ici)** : créer
`Multi_Asset/research/archived/macro_program_2026-09/` avec sept sous-dossiers
(`round1_score/`, `round2/`, `round3/`, `round4_idees/`, `round5_litterature/`, `round6_reouverture/`,
`revue_independante/`) plus les 6 dossiers d'exécution en enfants directs ou en sous-dossier
`tests/`, et un `README.md` de tête qui raconte la séquence en 15 lignes. Conserver les suffixes
de date existants (aucun des 3 dossiers déjà dans `archived/` n'en a — mais renommer casserait
plus de citations que ça n'en vaut la peine).

---

## À archiver en bloc

Toutes les grappes **C, D, E, F, G (hors les 4 mis en avant), H, I (hors growth_engine), J (hors
phase2_sizing)** — soit **51 des 72 dossiers** — sont des études CLOSES au sens strict : verdict
rendu, rien à décider, rien en attente. Elles doivent partir en bloc de `active/` vers `archived/`,
grappe par grappe, avec un `README.md` d'index par grappe plutôt que 51 déplacements isolés.
Bénéfice de lisibilité immédiat : un lecteur qui ouvre `research/archived/` verra ~10 dossiers de
grappe au lieu de 72 études individuelles, et `research/active/` tombera de 72 à moins de 10.

Cas particulier à signaler : les caches locaux énormes (`mr_intraday_grille_2026-08` 656 Mo,
`mr_univers_complet_2026-08` 331 Mo, `overnight_futures_2026-07` 161 Mo) sont **gitignorés** — ils
ne bougent pas avec `git mv` et n'alourdissent pas le dépôt. Ils alourdissent en revanche le
disque local ; un nettoyage (`rm -rf` sur les répertoires de cache, régénérables) est une
opportunité **indépendante** de ce plan de rangement, à ne pas confondre avec lui.

---

## Les cas embarrassants

Par ordre de gravité pour un lecteur externe :

1. **`orb_cost_funded_2026-08` contredit le déploiement réel.** Le corps du rapport conclut
   `ORB_KILL` (le t-stat de la jambe ORB reste sous le seuil R2=2.0 même après correction du coût,
   §5 : *« Le compte funded démarre donc sans moteur validé »*). Mais l'en-tête du document
   lui-même signale, en amendement, que **le sleeve est armée en production**
   (`FU_ORB_RISK=0.0025`, compte <ACCOUNT_ID>) *« par [décision antérieure, hors périmètre de cet
   audit] »*. Le dossier est honnête sur la contradiction — il ne la cache pas — mais un
   recruteur qui lit uniquement le titre du dossier (`orb_cost_funded`) sans lire l'amendement
   verra une stratégie tuée par sa propre équipe de recherche et pourtant vivante en compte réel.
   **Ce n'est pas un dossier à archiver silencieusement** : il faut soit lier `desk_orb_2026-09`
   (le dossier de décision go/no-go en cours, grappe B) explicitement à cette contradiction dans
   son README, soit ajouter une ligne de tête très visible expliquant que la décision d'octobre
   2026 est précisément le lieu où cette contradiction doit se trancher.

2. **`phase2_sizing_2026-08` est INACHEVÉ au sens strict.** Huit tables de résultats (`tables/*.csv`)
   et huit scripts (`code/*.py`) — mais **zéro fichier `.md`, zéro verdict écrit**. Ce n'est pas un
   dossier vide : `cohort_clustering_2026-08/RESULTS.md` réutilise littéralement son harnais
   (*« the `phase2_sizing_2026-08` harness is reused verbatim »*), donc il fonctionne et sert de
   bibliothèque à un autre chantier. C'est le cas le plus gênant à montrer tel quel : un dossier
   « actif » depuis août 2026 qui n'a jamais produit de texte. Deux options, pas d'archivage
   simple : (a) écrire a posteriori un `RESULTS.md` de 10 lignes résumant ce que les 8 tables
   montrent, puis archiver normalement ; (b) le requalifier explicitement en **bibliothèque**
   (déplacer son code vers un chemin de lib partagée, par exemple à côté de
   `data/ftmo_portfolio/audit_v2_independent/cleanroom/`) plutôt que de le laisser dans
   `research/`, et corriger la citation dans `cohort_clustering_2026-08`.

3. **`audit_reconcile_2026-08` n'est pas de la recherche.** Un seul fichier, un incident
   opérationnel du 2026-08-21 (résidu de réconciliation -$23,11 sur le compte funded, cause
   trouvée : bug de pipeline). C'est un rapport d'exploitation utile, mais il n'a pas sa place
   taxonomique dans `research/active/` à côté d'études de signal — il devrait vivre à côté des
   autres artefacts opérationnels du compte funded (`ftmo_live/`, ou un futur `_ops/incidents/`),
   pas être « archivé comme une étude close ».

4. **`swapkilled_futures_2026-07/DEPLOYMENT_PLAN.md` est un artefact interne caduc.** Il propose un
   book à 3 sleeves (H3/H4/H9, H4 pondérée à 14 %) — mais le `ROLL_AUDIT.md` du **même dossier**,
   écrit après, tue H4 comme artefact de roll-yield sur données propres (« flag NOT lifted »). Le
   livre final réel (`growth_engine_2026-07/FINAL_BOOK.md`, une semaine plus tard) ne contient
   d'ailleurs plus H4. Un lecteur qui tombe sur `DEPLOYMENT_PLAN.md` seul verrait une
   recommandation de déploiement qui a été invalidée dans son propre dossier trois fichiers plus
   loin. Recommandation : fusionner la provenance (`swapkilled_futures_2026-07` devient un
   "brouillon de travail" cité par `growth_engine_2026-07`, pas un plan de déploiement autonome).

5. **`carto_reouverture_2026-08` avoue sa propre incomplétude en première ligne** : *« L'agent
   Fable 5 lancé sur cette mission est mort sur limite de session sans rien écrire. Ce document
   est donc partiel et honnête sur son périmètre »*. C'est en réalité une preuve de robustesse du
   processus (reprise propre après échec d'un agent, honnêteté du scope) plutôt qu'un problème —
   mais seulement si le README de la grappe G l'explique ainsi ; laissé sans contexte, un titre
   « cartographie » suivi d'un aveu d'inachèvement se lit mal en survol.

6. **Chevauchement (pas doublon strict) `month_end_vehicle_2026-07` / `reaudit_vehicule_2026-08`.**
   Les deux posent « quel edge tué sur le coût vit sur un véhicule futures ? » — mais à des
   échelles différentes : `reaudit_vehicule` balaie les 118 edges catalogués (63 % fermés
   mécaniquement, 11 vivants potentiels), `month_end_vehicle` est l'étude de cas approfondie sur
   UN de ces 11 (B1, le seul déjà validé et déployé). Ce n'est pas un doublon à fusionner — c'est
   une relation générique→spécifique qu'il faut simplement rendre explicite (le README de grappe G
   doit dire : « voir reaudit_vehicule pour le tri, month_end_vehicle pour le cas qui a marché »).

---

## Exécution (hors périmètre de ce plan — pour référence future)

Si ce plan est approuvé et exécuté dans une session ultérieure, l'ordre correct est :
1. Créer les README d'index de grappe (10 fichiers) **avant** tout `git mv`.
2. `git mv` grappe par grappe (10 commits, pas 51 — plus facile à review et à annuler).
3. Après chaque `git mv`, `grep -rl "research/active/<nom>"` sur tout le dépôt et corriger les
   citations trouvées (chemins littéraux vers `active/` → `archived/`).
4. Mettre à jour `_meta/research_active.md` en dernier — retirer les 47 entrées archivées, ajouter
   une ligne pointant vers chaque nouveau README de grappe dans `archived/`.
5. Relancer `tools/check_register_integrity.py` (il ne devrait rien voir, mais coût nul à vérifier).
6. Ne PAS toucher aux 4 dossiers de la grappe B (`desk_orb`, `desk_overnight`, `macro_context`,
   `regime_diagnostic`) tant que la décision go/no-go d'octobre n'est pas tranchée.
