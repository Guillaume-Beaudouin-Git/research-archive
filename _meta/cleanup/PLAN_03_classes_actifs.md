# PLAN 03 — Rangement des classes d'actifs (hors Multi_Asset) & PropFirms

**Date de l'audit : 2026-09-08.** Périmètre : `Crypto/research/`, `Forex/research/`,
`Futures/research/` + `Futures/live/`, `Equities/research/`, `Commodities/research/`, `ETF_Vol/`,
`Options_Vol/`, **`PropFirms/`**, `yt_strategy_replications/`, `Algorithm_Brieuc/`,
`research_artifacts/`, `regime_diag/`, `breakout_container/`, `ftmo_profile_study/`, `model_store/`,
`outputs/`, `infra/`, `design/`, `Claude Vault/`. `Multi_Asset/` est hors périmètre (traité par un
collègue — voir `PLAN_01_narratif.md` et le tronc `_meta/research_active.md`).

**Aucun fichier n'a été modifié, déplacé ni supprimé.** Pour chaque candidat à
l'archivage/suppression, les citations ont été vérifiées (`grep -rl --include='*.md'`) avant
verdict. `tools/check_register_integrity.py` tourne **clean** au moment de l'audit (chaîne ledger
`[108, 112, 115, 117]`) — cette chaîne cite exclusivement des chemins sous
`PropFirms/ftmo/program_2026-06/`, donc **toute réorganisation de ce sous-arbre doit repasser le
script avant d'être exécutée**.

**Fait d'ancrage qui domine tout le périmètre PropFirms** : le compte FTMO est **funded depuis
2026-08-17**. Le programme `PropFirms/ftmo/program_2026-06/` (861 fichiers, 97 % du dossier
PropFirms) est le journal de recherche qui a *précédé* ce succès — y compris son propre
**mémo de décision qui recommandait explicitement de ne pas financer** (§1.4). Ce n'est pas une
faute : c'est un aléa temporel normal d'un dossier vivant. Mais un recruteur qui l'ouvre sans cette
clé de lecture comprendra l'inverse de la réalité.

---

## 0. Vue d'ensemble chiffrée

| Dossier | Fichiers trackés | Poids disque | Lecture d'ensemble |
|---|---|---|---|
| `PropFirms/` | 870 | 144 Mo | 99 % dans un seul sous-arbre (`ftmo/program_2026-06`), historique riche mais non curé |
| `Crypto/research/` | 363 | — | `active/` (6 dossiers) **entièrement périmé** (dernier commit ≤ 2026-06-10) ; `passed/` mal nommé |
| `Forex/research/` | 322 | — | 13 actifs dont une famille de 6 (Dédale) légitimement en cours ; 1 misclassé (`fix_reversal` invalidé mais en `active/`) |
| `Equities/research/` | 211 | — | 2 actifs (1 stale, 1 vraiment clos) ; 7 archivés propres |
| `yt_strategy_replications/` | 156 (4 Mo trackés / 841 Mo avec cache local non-tracké) | 4 Mo | Vitrine de qualité, quasi rien à corriger |
| `Futures/research/` | 118 | — | actif et alimente le book funded (ORB) — le seul chantier où l'activité récente est réelle |
| `Futures/live/` | 41 | — | infra de déploiement, à vérifier vs `ftmo_live/` (canonique) |
| `Commodities/research/` | 35 | — | 1 actif en cours, reste propre |
| `Algorithm_Brieuc/` | 24 | — | audit conclu, mais fichiers `.lnk`/`.ex5` non professionnels |
| `research_artifacts/` | 13 | — | 6 études closes, propres, jamais reliées à un index |
| `outputs/` | 12 | — | 4 audits adversariaux légitimes mais orphelins d'un dossier `Multi_Asset` |
| `regime_diag/`, `breakout_container/` | 10, 10 | — | doublons probables de fichiers racine déjà signalés par `PLAN_01` |
| `Options_Vol/`, `ETF_Vol/` | 9, 8 | — | propres, un seul verdict chacun |
| `Claude Vault/` | 9 | — | **coffre Obsidian par défaut, jamais utilisé, 0 contenu réel** |
| `ftmo_profile_study/` | 7 | — | étude close, propre, orpheline |
| `infra/` | 3 | — | 3 snapshots crontab historiques |
| `design/` | 3 | — | pré-registrations liées à `outputs/` et à `Multi_Asset` |
| `model_store/` | 6 fichiers **non trackés** | 144 Ko | pas un problème git — fichiers locaux orphelins d'avril |

---

## 1. `PropFirms/` — le chantier prioritaire

### 1.1 Les 5 firmes hors FTMO

| Dossier | Conclusion | Statut | Poids | Cité ailleurs | Action |
|---|---|---|---|---|---|
| `PropFirms/apex/rules.md` | Règles non vérifiées (training data) | VIVANT (évaluable au cas par cas depuis L51) | 1 fichier | CLAUDE.md | GARDER ACTIF |
| `PropFirms/mffu/rules.md` | idem, MFFU autorise l'overnight (pivot L51) | VIVANT | 1 | CLAUDE.md | GARDER ACTIF |
| `PropFirms/phidias/rules.md` | Données très limitées | INACHEVÉ | 1 | — | GARDER (coût nul) |
| `PropFirms/topstep/rules.md` | Non vérifié | VIVANT (évaluable) | 1 | CLAUDE.md | GARDER ACTIF |
| `PropFirms/tradeify/{rules,sources}.md` | Programme Tradeify **annulé** 2026-06-10, URLs 403 | CLOS | 2 | CLAUDE.md ("Tradeify ANNULÉ") | GARDER (coût nul, mémoire utile) |

Ces 6 fichiers sont légers, correctement étiquetés (`⚠️ UNVERIFIED`), sans action nécessaire.

### 1.2 `PropFirms/ftmo/program_2026-06/` — 861 fichiers, 97 Mo

Toutes les études ci-dessous sont **CLOSES** (le programme s'est arrêté le 2026-06-10 ; l'account a
ensuite été financé par une voie différente — EA v2.x, cf. mémoire `spec_chain_v28_ready_2026-07.md`
— absente de ce sous-arbre). Chacune a un README/VERDICT explicite ; le problème n'est **pas** la
rigueur, c'est le **volume et l'absence de tri** entre "narratif à montrer" et "scratch à compresser".

| Sous-dossier | Conclusion en une phrase | Fichiers | Poids | Cité ailleurs | Action |
|---|---|---|---|---|---|
| `ftmo_research/` | Corpus racine du programme (idées, validations, mémos) — voir détail §1.3 | 495 | 97 Mo | 73 .md dans tout le dépôt | GARDER (mémoire de projet), **compresser le sous-dossier `audit/`** |
| `ftmo_universe/` | Reconciliation de l'univers 16 instruments FTMO-exécutables | 65 | 4,3 Mo | INDEX.md cité par `top10_test` | ARCHIVER en l'état |
| `ftmo_alpha_program/` | Exécution du programme "Alpha Research" (Phases 0-2), gate p(pass) | 58 | 3,6 Mo | — | ARCHIVER en l'état |
| `top10_test/` | 164 tests catalogués, 0 strict — **aucun README/verdict**, 44 CSV bruts + 7 py | 51 | 1,4 Mo | `COST_AUDIT.md` (or sur-pénalisé 1,9×), mémoire "top10 rigorous" | ARCHIVER, **ajouter un README manquant** (dossier sans narratif) |
| `ftmo_portfolio_audit/` | Audit clean-room du book "3-sleeve" revendiqué — NOT-CONFIRMED, p(pass) 0,18-0,29 | 31 | 856 Ko | PROGRAM_DECISION_MEMO.md | ARCHIVER en l'état |
| `ftmo_3strats_audit_2026-06/` | Audit indépendant du rapport "FTMO 3 stratégies" — re-implémenté depuis specs PDF | 28 | 27 Mo | — | ARCHIVER — **vérifier le contenu des 6 parquet (27 Mo)** avant d'y toucher |
| `s076_replication/` | Réplication indépendante de "Ross Hook" (#76) — confirme, pas un artefact d'engine | 22 | 5,9 Mo | REGISTER.md | ARCHIVER en l'état |
| `ftmo_survivors_book/` | Book bottom-up (Ross Hook + TSMOM swap-net) — aucun horizon ne clear 0,50 | 20 | 1,3 Mo | container_eval | ARCHIVER en l'état |
| `ftmo_paper_edges/` | Harvest d'edges "papier" corrigés méthodologiquement — DSR à N réel | 18 | 548 Ko | — | ARCHIVER en l'état |
| `ftmo_candidate_funnel/` | Funnel itér. 1 : 66 configs, gate DSR>0.5 à N=66 — **shortlist vide** | 18 | 232 Ko | funnel v2 (suite directe) | ARCHIVER en l'état |
| `ftmo_candidate_funnel_v2/` | Funnel itér. 2 : 27 configs espaces non couverts — **0/27, exhaustion confirmée** | 14 | 112 Ko | funnel v1 | ARCHIVER en l'état |
| `propfirm_pass_plan/` | Plan opérationnel de passage | 9 | 56 Ko | — | ARCHIVER en l'état |
| `paper_triage/` | Tri de papiers académiques | 5 | 80 Ko | — | ARCHIVER en l'état |
| `edge_improvement/` | Amélioration d'un edge pré-enregistré | 5 | 44 Ko | — | ARCHIVER en l'état |
| `b1_feasibility/` | FINRA short-volume → NQ overnight : **FAIL au Gate 4 (IC)**, gate économisé | 5 | 1,5 Mo | — | ARCHIVER en l'état |
| `container_eval/` | Un changement de container seul ne suffit pas (p(pass) 0,371, CI [0.10,0.75]) | 4 | 28 Ko | ftmo_survivors_book | ARCHIVER en l'état |
| `commodity_carry_feasibility/` | Corroboration IC carry commodities | 4 | 88 Ko | CLAUDE.md (L32b) | ARCHIVER en l'état |
| `positive_dsr_register/` | **Ledger canonique** cité par `check_register_integrity.py` — DSR positif max = Ross Hook 0,98 à N=1 (0,00 au N=108 programme) | 3 | 32 Ko | script d'intégrité, 5 .md | **NE JAMAIS DÉPLACER** — c'est l'ancre du contrôle CI |
| `ftmo_decorrelated_portfolio/` | Reconciliation d'un portefeuille décorrélé | 2 | 24 Ko | — | ARCHIVER en l'état |
| `propfirm_scan/` | Scan EV des firmes pour un trader trend/momentum | 1 | 24 Ko | — | ARCHIVER en l'état |
| `build_top100_inventory.py` + `top100_strategy_candidates_2026-06-04.csv` (racine du programme) | Inventaire brut de 100 candidats scrapés | 2 | 84 Ko | — | Redondant avec `ftmo_universe/` mieux structuré — **fusionner ou marquer "superseded"** |
| `PROGRAM_DECISION_MEMO.md` | Synthèse à 3 angles : **"do-not-fund on free price data"** | 1 | 16 Ko | — | **GARDER mais banderoler "superseded 2026-08-17 — le compte a été funded par une voie hors programme"** (voir §1.4) |

### 1.3 `ftmo_research/` en détail — le point de compression prioritaire

`ftmo_research/` (495 fichiers, 97 Mo, presque le tiers de tout PropFirms) se décompose en :

- **`audit/` — 281 fichiers, 14 Mo, AUCUN sous-dossier.** Scripts one-off (`optim_stepN.py`,
  `iter10_*.py`, `orb_*.py`, `trade_step*.py`, `f1_bughunt_*.py`…) + leurs CSV + leurs `_output.txt`
  jetés à plat dans un seul répertoire, sans README ni index. C'est du vrai travail (walk-forward,
  bug-hunt, DSR, régime) mais **illisible tel quel** pour un tiers — aucun fichier ne dit dans quel
  ordre les lire ni lequel a produit quel verdict final. Aucune citation par chemin exact dans les
  .md du dépôt (seuls des noms de fichiers nus, hors du scope du contrôle d'intégrité) → **peut être
  compressé en une archive `.tar.gz` unique sans casser aucune citation**, ou a minima regroupé par
  préfixe (`optim_*`, `nq_*`, `trade_*`, `orb_*`, `iter10_*`, `f1_*`) en 6 sous-dossiers.
- **`EURUSD_m1.parquet` (34 Mo) + `eurusd_m1_spread.parquet` (22 Mo) + `EURUSD_m5.parquet` (7,6 Mo)
  + `EURUSD_m15.parquet` (4 Ko)** — 63 Mo+ de **données de marché trackées en git** dans un dossier de
  recherche, alors que la gouvernance data du dépôt (`_meta/data_governance.md`) prescrit des caches
  gitignorés et une source canonique unique. Ces fichiers **sont consommés par du code hors PropFirms**
  (`Multi_Asset/research/active/reaudit_vehicule_2026-08/funnel_reaudit/code/data_layer.py`,
  `data/deep_history_utc/`, `top10_test/data_loaders.py`, `_audit/2026-06_instrument_schema/`) — donc
  **ne pas supprimer sans migrer les consommateurs** (règle de gouvernance). Action recommandée :
  vérifier si `data/deep_history_utc/` possède déjà une série équivalente ; si oui, ces 63 Mo sont un
  doublon pur à dédupliquer ; si non, les déplacer vers `data/` (hors PropFirms) avec gitignore + un
  manifest, et laisser un pointeur.
- **89 fichiers `.md` narratifs bien formés** (IDEA_*, VALIDATION_*, ORB_*, OPTIM_*, RAPPORT_*,
  MEMO_*, STRATEGY_DOSSIER_*.docx) — c'est le vrai contenu "à montrer". Aucun index/sommaire ne les
  relie entre eux malgré leur nombre (89 fichiers à plat à la racine de `ftmo_research/`).
- **`code/` (19 fichiers), `figures/` (26 png), `tsmom/`, `backwardation_oil/`, `statarb_audnzd/`,
  `announcement_premium/`, `NQ_ORB_metrics/`, `NQ_overnight_metrics/`** — sous-études ciblées, propres,
  chacune avec son propre narratif.

**Recommandation pour `ftmo_research/`** : garder les 89 `.md` + les sous-dossiers thématiques tels
quels (c'est la mémoire du programme qui a mené au funded), mais (a) écrire un `INDEX.md` d'une page
listant les études par thème avec leur verdict en une ligne, (b) compresser ou sous-diviser `audit/`
(281 fichiers plats), (c) trancher le sort des 63 Mo de parquet EURUSD.

### 1.4 Le cas le plus embarrassant du dossier : `PROGRAM_DECISION_MEMO.md`

Daté 2026-06-08, ce mémo conclut noir sur blanc : **"Recommendation: do-not-fund on free price data"**,
avec p(pass) triangulé à 0,2-0,34 sur trois angles indépendants. C'est un travail honnête et bien
sourcé — mais le compte **a ensuite été financé** (2026-08-17, via l'infrastructure `ftmo_live/` /
EA v2.x, qui n'a **aucune trace** dans ce sous-arbre). Un recruteur qui ouvre ce fichier — le seul
"decision memo" au niveau du programme — lira une conclusion qui contredit frontalement l'état réel
du compte, sans aucun signal indiquant que le programme a été relancé et a fini par réussir par une
autre voie. **Action : ajouter un bandeau d'un paragraphe en tête du fichier** ("ce mémo documente
l'état de la recherche au 2026-06-08 ; le compte a depuis été financé via une architecture différente,
voir `ftmo_live/` et `_meta/current_focus.md`") — un des rares cas de ce plan où *ne pas* rédiger un
mot rendrait le dépôt trompeur.

---

## 2. `Crypto/research/`

| Dossier | Conclusion | Statut | Poids | Dernier commit | Action |
|---|---|---|---|---|---|
| `active/_preflight/` | Gate 1+2 FAIL — edge crypto orthogonal à A+B épuisé sur données gratuites | **CLOS mais dans `active/`** | 1 | 2026-05-23 | ARCHIVER |
| `active/ftmo_twoSided_makeOrBreak/` | En-tête du fichier dit lui-même **"Status: ARCHIVED at pre-flight"** | **CLOS mais dans `active/`** | 3 | 2026-06-09 | ARCHIVER (le fichier ment sur son propre statut vis-à-vis de sa localisation) |
| `active/pairs_btceth_D/` | NO-GO franc — Sharpe 2,23 de Park ne survit à aucun tueur | **CLOS** | 9 | 2026-06-10 | ARCHIVER |
| `active/session_I_crypto_flows/` | 0 survivant, 2 kills propres (unlock-drift sous placebo, funding-extrêmes = continuation) | **CLOS** | 17 | 2026-06-10 | ARCHIVER |
| `active/token_unlocks/` | "GATE 0 — awaiting user decision on data source" | **INACHEVÉ, en jachère 3,5 mois** | 1 | 2026-05-23 | ARCHIVER (relancer seulement avec un angle neuf, catégorie "Puissance" rouvrable) |
| `active/vrp_short_gamma/` | "GATE 0 — AWAITING GO PHASE 1" | **INACHEVÉ, en jachère 3,5 mois** | 1 | 2026-05-23 | ARCHIVER |
| `passed/halving_cycle/`, `hmm_transitions/`, `obv_signal/`, `vpt_cmf/` | Le code affiche lui-même `"→ SKIP ALL (IC + Sharpe criteria not met)"` | **En réalité CLOS/FAIL, pas "passed"** | 2 chacun | 2026-05-18 | Renommer sémantiquement ou ARCHIVER — le nom `passed/` est trompeur (comme dans toutes les classes d'actifs, c'est un dossier de convention vide ailleurs — ici il contient du contenu qui contredit son propre nom) |
| `archived/` (11 sous-dossiers, 279 fichiers) | Momentum, carry, mean_reversion, patterns, ml, regime, options, sentiment, h31_cs_fs_dn, etf_regime_overlay, `other/` (105 fichiers, le plus gros) | CLOS, déjà bien rangé | 279 | — | GARDER (rien à faire) |
| `archived/_frozen/` | Artefacts figés de Strategy A (code+state) au 2026-05-30 | CLOS, référence gelée | 27 | — | GARDER (cité par CLAUDE.md) |

**Verdict global Crypto** : **les 6 dossiers `active/` sont tous morts ou en jachère depuis 3 à 3,5
mois** (dernier commit ≤ 2026-06-10, on est au 2026-09-08). Aucun n'a d'activité récente. C'est
l'écart le plus net entre l'étiquette de dossier et la réalité rencontré dans tout l'audit.

---

## 3. `Forex/research/`

| Dossier | Conclusion | Statut | Poids | Dernier commit | Action |
|---|---|---|---|---|---|
| `active/fix_reversal/` | En-tête : **"⚠️ INVALIDÉ 2026-06-10 (audit tz)"** — tout le rapport était décalé de 2-3h | **CLOS mais dans `active/`** | 15 | — | ARCHIVER |
| `active/dedale_audit_2026-08/` | Audit indépendant en cours, se termine sur "prochaine étape suggérée" (AUDCAD/GBPNZD à récupérer) | **VIVANT, réellement inachevé** | 8 | récent (2026-08) | GARDER ACTIF |
| `active/dedale_broker_2026-08/`, `dedale_config_2026-08/`, `dedale_data_2026-08/`, `dedale_strategy_2026-08/` | Chaîne de réplication "Dédale" (EA tiers Brieuc) — biais d'anticipation démontré (mémoire `fx_carry_dedale_2026-08.md`) | VIVANT, piste à rouvrir explicitement marquée | 36+1+6+27 | 2026-08 | GARDER ACTIF (famille cohérente, ne pas fusionner en un seul dossier — chaque étape a un mandat distinct) |
| `active/fx_carry_2026-09/` | Suite directe post-Dédale, carry conditionnel comme filtre d'entrée | VIVANT (session la plus récente, 2026-09) | 14 | 2026-09 | GARDER ACTIF |
| `active/fx_events_2026-09/` | Axe événements macro datés — un candidat de drift survit à la correction complète | VIVANT | 71 | 2026-09 | GARDER ACTIF |
| `active/fx_libre_2026-09/` | Pré-enregistrement cohérence transitoire cross-rate, écrit avant tout accès aux données | VIVANT/INACHEVÉ (juste démarré) | 10 | 2026-09 | GARDER ACTIF |
| `active/fx_macro_score_2026-09/` | Révise un verdict antérieur "non reconstructible", trouve une source gratuite | VIVANT | 10 | 2026-09 | GARDER ACTIF |
| `active/fx_intraday_deepdive/` | Synthèse institutionnelle intraday FX M1 2007-2026 (source des L43/L44) | CLOS mais fondateur de leçons gravées | 20 | 2026-06-09 | ARCHIVER (mission accomplie, gravée dans le registre L) |
| `active/g2d_carry_cross_asset/` | Revue de littérature, verdict "CONDITIONNEL OUI — personnel uniquement, pas sur $25k" — **aucun backtest empirique exécuté**, juste 2 rapports desk research | **INACHEVÉ (dormant, jamais opérationnalisé)** | 2 | 2026-05-26 | GARDER en dormance explicite : "en attente de l'ouverture du compte IBKR" (fait d'actualité : pas encore ouvert) |
| `archived/` (12 sous-dossiers) | cip_eoq, fx_carry_em/fred/trend, fx_momentum_monthly, g1_carry_conditional, london_orb_v1, round_number_cascade, strategy_d_modified_carry(_v2), strategy_e_fix_flow, strategy_f2_asian_breakout | CLOS, bien rangé | — | — | GARDER |
| `passed/` | Dossier de convention (vide/placeholder) | — | — | — | GARDER (coût nul) |

**Verdict global Forex** : c'est la classe la mieux tenue du périmètre — la majorité des `active/`
sont *réellement* actifs (sessions 2026-08/09), à l'exception nette de `fix_reversal/` (invalidé) et
`fx_intraday_deepdive/` (mission terminée, gravée en L43/L44) qui devraient basculer en `archived/`.

---

## 4. `Futures/research/` & `Futures/live/`

| Dossier | Conclusion | Statut | Poids | Dernier commit | Action |
|---|---|---|---|---|---|
| `research/active/nq_intraday/` | Recherche ORB/NQ toujours vivante — variante `iter_11_fast` verdict **GO** daté, `monti_orb` verdict **KEEP_AS_PAPER**, 2026-08-24 | **VIVANT, réellement alimenté**, probablement la source de la sleeve ORB US100 aujourd'hui live sur le compte funded | 60 | 2026-08-24 | GARDER ACTIF — **c'est le dossier le plus légitimement "actif" de tout le périmètre** |
| `research/active/zn_baltussen/` | Feasibility Baltussen 2021, arrêtée au STOP-POINT 1 (data & calendrier), gates PASS/FAIL jamais évalués | INACHEVÉ, genuinement en pause | 11 | 2026-08-24 (remontée depuis une branche, "absente de main") | GARDER ACTIF, mais noter l'écart : recommis récemment pour combler une citation CLAUDE.md manquante |
| `research/active/strategy_d/` | Pré-registration + scaffolding infra (launchd plist) seulement — **aucun résultat**, "0 mods consumed" | **INACHEVÉ, 3,5 mois sans mouvement** | 4 | 2026-06-10 | GARDER ACTIF si intention réelle de reprendre, sinon ARCHIVER — poser la question à l'utilisateur |
| `research/active/voie_b_ftmo/` | Pivot MT5 EA pour Strategy A (crypto) — Strategy A est **gelée** depuis 2026-05-30 | **CLOS de fait (véhicule mort), en jachère 3 mois**, + un fichier `results/slip_report.csv` jamais tranché (commit ou ignore) depuis juin | ARCHIVER, résoudre le fichier orphelin en `.gitignore` avant | 26 | 2026-06-09 | 
| `research/archived/nq_intraday_vwap/` | N=19 insuffisant | CLOS | 3 | — | GARDER |
| `research/archived/orb_ivb_nq/` | — | CLOS | 9 | — | GARDER |
| `research/passed/` | `.gitkeep` + `__init__.py` seuls | — | 2 | — | GARDER |
| `live/orb_floor_ftmo/` | Infra de déploiement ORB live | VIVANT | — | — | Vérifier chevauchement avec `ftmo_live/` (canonique, hors périmètre) — pas de doublon détecté dans ce périmètre, mais à confirmer avec le propriétaire de `ftmo_live/` |
| `live/strategy_c_live/` | Infra live Strategy C — **Strategy C annulée** (pas de véhicule Tradeify) | Code conservé, correctement documenté "réutilisable" par CLAUDE.md | 41 | — | GARDER (le CLAUDE.md l'assume déjà explicitement) |
| `live/strategy_c_paper/` | Uniquement infra de log pré-existante (`log_trade.py`, csv) | — | — | — | GARDER (convention documentée dans CLAUDE.md — ne pas y ajouter de code) |

---

## 5. `Equities/research/`

| Dossier | Conclusion | Statut | Poids | Dernier commit | Action |
|---|---|---|---|---|---|
| `active/sector_hothand_propfirm/` | t_HAC 10,38 = drapeau rouge, MDD -13,3% > limite FTMO 10% ⇒ **BREACH en l'état, audit obligatoire** (déjà noté par CLAUDE.md) | **INACHEVÉ, "obligatoire" mais en jachère 3+ mois** | 12 | 2026-05-28 | GARDER ACTIF mais prioriser — un audit marqué "obligatoire" par la constitution du dépôt et resté sans suite 3 mois est un signal faible pour un recruteur qui lirait CLAUDE.md et vérifierait |
| `active/sr2_hunt/` | En-tête du fichier lui-même : **"HUNT DEFINITIVELY CLOSED, FORMAL EXHAUSTION DECLARED"** (2026-05-27) | **CLOS mais dans `active/`, exactement le même symptôme que Crypto** | 17 | 2026-08-24 (mise à jour récente malgré le statut clos) | ARCHIVER (le fichier date sa propre clôture au 2026-05-27, un commit ultérieur n'a pas changé le verdict) |
| `archived/indices_swing/` | FAIL→ARCHIVE documenté, Sprint 1 IC scan + Sprint 2 backtest, postmortem propre | CLOS, bien fait | 138 | 2026-05-23 | GARDER — c'est le plus gros dossier archivé (8,6 Mo) mais correctement justifié |
| `archived/jt_momentum_cs/`, `multi_asset_tsmom/`, `pairs_cointegration/`, `pairs_distance_gatev/`, `sector_reversal_cs/` | CLOS, petits, bien rangés | CLOS | 3-14 chacun | — | GARDER |
| `archived/vwap_mr_fade_nq/` | CLOS, activité la plus récente du groupe archivé (2026-08-24) | CLOS | 10 | 2026-08-24 | GARDER |
| `passed/` | `.gitkeep` + `__init__.py` | — | 2 | — | GARDER |

---

## 6. `Commodities/research/`, `ETF_Vol/`, `Options_Vol/`

| Dossier | Conclusion | Statut | Poids | Action |
|---|---|---|---|---|
| `Commodities/research/active/xs_basis_tsmom/` | Scan IC basis+TSMOM commodities, phase A incomplète (déjà noté CLAUDE.md) | INACHEVÉ légitime | 28 | GARDER ACTIF |
| `Commodities/research/archived/commodity_tsmom/` | CLOS | CLOS | 3 | GARDER |
| `Commodities/research/passed/` | placeholder | — | 1 | GARDER |
| `ETF_Vol/research/archived/vix_term_carry/` | Feasibility + summary, CLOS | CLOS | 3 | GARDER |
| `ETF_Vol/research/passed/` | placeholder | — | 1 | GARDER |
| `Options_Vol/research/archived/vrp_spx_angle_c/` | VRP options SPY **FALSIFIÉ sur chaînes réelles** (cité MEMORY.md) — postmortem + phase0/phase1 propres | CLOS, bien fait | 8 | GARDER |

Ces trois classes sont les plus propres du périmètre — rien à réorganiser.

---

## 7. `yt_strategy_replications/` & `Algorithm_Brieuc/`

### 7.1 `yt_strategy_replications/`

**156 fichiers trackés, seulement 4 Mo** (le `data_cache/` de 697 Mo visible sur disque n'est PAS
tracké par git — aucun problème de dépôt). README avec scorecard clair : 13 stratégies testées,
**1 seule** validée avec réserve (VRP, tail risk catastrophique), 1 réelle mais nécessitant des
données propriétaires (PEAD), tout le reste FAIL net de coûts.

**C'est la meilleure pièce de démonstration du périmètre pour un recruteur** : méthodologie
identique appliquée à des stratégies "hype" externes (contre-preuve de rigueur), moteur partagé
unit-testé, verdicts chiffrés et non complaisants ("real Sharpe not cherry-picked").

| Sous-dossier | Statut | Action |
|---|---|---|
| `engine/` | Moteur partagé, réutilisé par tous les modules | GARDER, mettre en avant |
| `reports/` (13 fichiers, dont README + VALIDATED_EDGES.md) | Narratif de synthèse | GARDER, mettre en avant en premier |
| `module_1` à `module_5`, `gold_research/`, `soybean_research/`, `metals_energy_research/`, `breakout_ftmo/`, `cs_macro_momentum_ftmo/`, `event_driven_ftmo/`, `intraday_mr_ftmo/`, `mr_subscale_ftmo/`, `nonovernight_research/` | Chacun avec ses `results/`, cohérent | GARDER |
| `archived/POSTMORTEM.md` | Seul fichier du dossier `archived/` — vérifier qu'il n'y a pas d'autre contenu manquant | GARDER, à vérifier que rien n'a été oublié d'archiver ici |

**Seule réserve** : `data_cache/` (697 Mo sur disque) n'est référencé dans aucun `.gitignore` explicite
visible à ce niveau — à confirmer qu'il est bien couvert par une règle globale, pour éviter qu'un
`git add .` accidentel un jour ne l'embarque.

### 7.2 `Algorithm_Brieuc/` — 24 fichiers

Audit conclu (biais d'anticipation démontré, per fait d'actualité) — bon contenu, mauvaise forme :

| Élément | Problème | Action |
|---|---|---|
| `DedaleDiag.mq5 (2).lnk`, `(3).lnk`, `.mq5.lnk`, `DedaleExport.mq5.lnk`, `DédaleFormation.mq5.lnk` | **5 fichiers `.lnk` (raccourcis Windows)** trackés en git — inertes, illisibles hors Windows, dupliqués jusqu'à 3× pour le même fichier source | SUPPRIMER (aucune valeur informative — un raccourci Windows n'est pas du code ni de la donnée) |
| `.ex5` (×3 : `DedaleDiag.ex5`, `DedaleExport.ex5`, `DédaleFormation.ex5`) | Binaires compilés MQL5, non lisibles, dérivables du `.mq5` source | Discutable : soit SUPPRIMER (régénérables depuis le `.mq5`), soit GARDER si le binaire fait preuve (ex. horodatage de compilation de l'auteur original) — trancher avec l'utilisateur |
| `Abruti.mq5` | Nom de fichier ("idiot" en français) — probablement un nom donné par l'auteur tiers Brieuc, pas par l'utilisateur, mais **visible tel quel dans le dépôt d'un candidat au recrutement** | Vérifier la provenance ; si c'est bien un fichier de l'EA tiers audité (pas le nôtre), documenter cette provenance dans un README pour qu'un lecteur ne l'attribue pas à l'auteur du dépôt |
| `Backtest brieuc.md`, `Transcript_Vidéos_Brieuc.md`, `recapitulatif_parametres.md`, `cases.png` | Matériel source de l'audit, légitime | GARDER |

**Ce dossier a un contenu d'audit solide (repris dans `Forex/research/active/dedale_*`, cité en
mémoire) mais sa forme brute — raccourcis Windows dupliqués, binaires, un nom de fichier
embarrassant — donne une première impression de désordre à quiconque l'ouvre en premier.**

---

## 8. Dossiers divers à la racine

Tous ces dossiers sont des études ponctuelles rigoureuses (pré-registration + verdict), mais **aucun
n'est rattaché à la hiérarchie `<AssetClass>/research/{active,archived}/`** que le dépôt affiche
comme sa propre carte (`README.md`) — ils vivent en dossiers racine au nom peu explicite. Plusieurs
recoupent des fichiers déjà signalés orphelins par `PLAN_01_narratif.md` (racine).

| Dossier | Conclusion | Statut | Poids | Cité ailleurs | Action |
|---|---|---|---|---|---|
| `research_artifacts/` | 6 études "deep research" (calendar spreads CME, funding dispersion, PEAD systematic, regime overlay, sector rotation macro, SPX VRP) — chacune KILL/DEFERRED/GO avec Sharpe net retail chiffré | CLOS, propre, jamais indexé nulle part | 13 | 0 | ARCHIVER en bloc — déplacer sous `Multi_Asset/research/archived/` ou `_meta/` serait plus navigable, mais **hors mandat unilatéral** (coordination avec le collègue Multi_Asset) |
| `regime_diag/` | Diagnostic régime macro, verdict rubric gelé, "mint 0 strategy trials" (consomme le registre comme un STOP) | CLOS | 10 | `outputs/`? à vérifier | Probable doublon de `STUDY_REGIME_DIAGNOSTIC_2026-06-20.md` (racine, signalé 0-citation par PLAN_01) — **fusionner les deux narrations d'un même travail** |
| `breakout_container/` | Étude "breakout dilue la survie funded" (verdict rubric gelé) | CLOS | 10 | — | Probable doublon de `STUDY_BREAKOUT_CONTAINER_2026-06-20.md` (racine, 0-citation, signalé par PLAN_01) — même remarque |
| `ftmo_profile_study/` | Profil FTMO-compatible : meilleur fit = "fast intraday mean-reversion, hard-stopped" | CLOS, propre | 7 | 0 | ARCHIVER en bloc |
| `outputs/` | 4 audits adversariaux datés 2026-07-12/13 ("Auditeur ≠ auteur") : portage path-aware du book, BTC 5e actif (NO-GO), sleeve month-end bounce (audit), postmortem process `btc_intraday_ftmo` | CLOS, rigoureux, gouvernance explicite | 12 | `N_ledger.md` racine (signalé orphelin par PLAN_01) | Ce nom générique ("outputs") est le pire du lot pour la navigabilité — même contenu que `design/` (pré-registrations sœurs). **Regrouper `outputs/` + `design/` sous un seul dossier nommé explicitement** (ex. `audits_book_funded_2026-07/`) |
| `infra/` | 3 snapshots crontab VPS (06-12, 06-13, 06-15) | Historique figé | 3 | — | GARDER (coût nul, traçabilité utile) |
| `design/` | 3 pré-registrations sœurs de `outputs/` (audit month-end, BTC 5e actif) + note d'archi | CLOS, sert de pré-reg à `outputs/` | 3 | Dupliqué dans 11 worktrees locaux (non trackés, hors scope) | Fusionner avec `outputs/` (même remarque) |
| `model_store/` | 2 modèles PyTorch (BTC/SOL) + scalers, **non trackés par git** | Orphelin d'un pipeline ML archivé (`Crypto/research/archived/ml/`, `Crypto/research/archived/other/train_and_save.py`) | 0 (non tracké) | 3 .py dans `Crypto/research/archived/other/` | Pas un problème de dépôt (déjà hors git) — purge locale au choix de l'utilisateur, sans urgence |
| **`Claude Vault/`** | **Coffre Obsidian par défaut — texte d'accueil intact ("Voici votre nouveau coffre… supprimez cette note")**, `Random thoughts.md` et `To do's list.md` **vides (0 ligne)**, `Trading strategy ideas.md` 1 ligne | **Jamais utilisé, aucun contenu réel, depuis 2026-05-12** | 9 (dont 5 fichiers de config `.obsidian/`) | 0 | **SUPPRIMER** — c'est le seul dossier de tout le périmètre sans la moindre valeur informative, probablement un `git add .` accidentel lors d'une initialisation Obsidian locale |

---

## À mettre en avant

1. **`yt_strategy_replications/`** — la meilleure vitrine du dépôt : méthodologie appliquée à des
   stratégies externes hypées, verdicts non complaisants, moteur unit-testé, scorecard lisible en
   30 secondes. À citer en premier dans tout README destiné à un recruteur.
2. **`PropFirms/ftmo/program_2026-06/`** (une fois trié) — la preuve d'un vrai programme de recherche
   institutionnel : trois angles indépendants qui convergent (`PROGRAM_DECISION_MEMO.md`), une
   réplication indépendante volontairement aveugle (`s076_replication/`), un ledger de DSR honnête qui
   n'hésite pas à afficher 0,00 (`positive_dsr_register/REGISTER.md`). Une fois le bandeau de
   péremption ajouté (§1.4) et `audit/` compressé, c'est un narratif de rigueur très fort.
3. **`Futures/research/active/nq_intraday/`** — seul dossier vraiment vivant qui se rattache
   directement à une sleeve funded aujourd'hui (ORB US100), avec des verdicts GO/KEEP_AS_PAPER
   datés d'il y a deux semaines.
4. **`Forex/research/active/dedale_*` + `fx_carry_2026-09` + `fx_events_2026-09`** — chaîne
   d'audit "auditeur ≠ auteur" appliquée à un EA tiers, avec biais d'anticipation démontré
   empiriquement (test de falsification chiffré) : bonne démonstration de scepticisme méthodique.

## À archiver en bloc

- **Tous les dossiers `active/` de `Crypto/research/`** (6 dossiers, tous morts/en jachère depuis
  ≥ 3 mois) → basculer vers `archived/` avec le statut réel de chacun.
- `Forex/research/active/fix_reversal/` (auto-invalidé) et `fx_intraday_deepdive/` (mission
  accomplie, gravée en L43/L44).
- `Equities/research/active/sr2_hunt/` (auto-déclaré clos depuis 2026-05-27) et
  `Futures/research/active/voie_b_ftmo/` (véhicule mort — Strategy A gelée).
- Les 18 sous-dossiers restants de `PropFirms/ftmo/program_2026-06/` listés "ARCHIVER en l'état"
  au §1.2 — ils sont déjà propres, il s'agit juste d'assumer qu'ils sont clos, pas de les modifier.
- `research_artifacts/`, `ftmo_profile_study/`, `regime_diag/`, `breakout_container/` — études
  closes root-level à regrouper (idéalement sous un même toit avec `outputs/`+`design/`).

## Les cas embarrassants

1. **`PROGRAM_DECISION_MEMO.md` recommande "do-not-fund"** alors que le compte est funded depuis
   trois semaines — le seul cas de ce plan où le contenu contredit frontalement l'état réel (§1.4).
2. **`Crypto/research/passed/{halving_cycle,hmm_transitions,obv_signal,vpt_cmf}/`** — le nom du
   dossier dit "passed", le code lui-même imprime `"→ SKIP ALL"`. Un recruteur qui lit le nom de
   dossier avant le contenu comprend l'inverse de ce qui s'est passé.
3. **`Crypto/research/active/ftmo_twoSided_makeOrBreak/README.md` affirme lui-même
   `"Status: ARCHIVED"`** tout en résidant physiquement dans `active/` — la contradiction est
   inscrite dans le fichier lui-même, pas seulement déduite de l'ancienneté.
4. **`Algorithm_Brieuc/`** — 5 raccourcis Windows `.lnk` (dont 3 copies du même fichier) et un
   fichier nommé `Abruti.mq5` sont le premier contenu visible d'un `ls` sur ce dossier ; le vrai
   travail d'audit (solide, cité en mémoire) est noyé sous ce bruit.
5. **`Claude Vault/`** — coffre Obsidian jamais initialisé, texte d'accueil par défaut inchangé
   depuis 4 mois, zéro contenu réel, candidat de suppression le plus net de tout l'audit.
6. **`Futures/research/active/strategy_d/`** — pré-registration + scaffolding infra seulement,
   "0 mods consumed" depuis 3,5 mois : soit une intention de recherche jamais concrétisée, soit un
   dossier à clore explicitement.
7. **`Equities/research/active/sector_hothand_propfirm/`** — CLAUDE.md qualifie son audit
   d'"obligatoire" (MDD breach détecté) et pourtant rien n'a bougé depuis 2026-05-28. Un recruteur
   qui croise ce dossier avec la constitution du dépôt verra un signal de risque non traité.
8. **`regime_diag/` et `breakout_container/` vs `STUDY_REGIME_DIAGNOSTIC_2026-06-20.md` et
   `STUDY_BREAKOUT_CONTAINER_2026-06-20.md`** (racine, signalés à 0 citation par `PLAN_01`) — même
   travail probablement raconté deux fois, à deux endroits, sans lien entre les deux versions.
9. **63 Mo de parquet EURUSD trackés en git** dans `PropFirms/ftmo/program_2026-06/ftmo_research/`
   — exactement le type de fichier que `_meta/data_governance.md` proscrit de suivre en git, et qui
   gonfle le clone du dépôt pour un recruteur pressé.

## Priorisation — par quoi commencer

1. **`Claude Vault/`** — suppression immédiate, zéro risque, zéro dépendance, gain de crédibilité
   disproportionné à son coût (un coffre Obsidian vide dans un dépôt de recherche quant est le genre
   de détail qu'un recruteur remarque).
2. **Bandeau de péremption sur `PROGRAM_DECISION_MEMO.md`** — un paragraphe, corrige la plus grosse
   contradiction du périmètre.
3. **Nettoyer `Algorithm_Brieuc/`** (retirer les `.lnk`, statuer sur les `.ex5`) — deuxième
   correction à fort ratio impact/effort.
4. **Rebasculer les dossiers `active/` morts** (Crypto ×6, Forex ×2, Equities ×1, Futures ×1) vers
   `archived/` — mécanique, sans risque, restaure la cohérence entre étiquette et réalité pour ~10
   dossiers d'un coup.
5. **`PropFirms/ftmo/program_2026-06/ftmo_research/`** : écrire l'`INDEX.md` manquant et statuer sur
   les 63 Mo de parquet + le sous-dossier `audit/` (281 fichiers plats) — le chantier le plus long
   mais celui qui pèse le plus sur la lisibilité globale (144 Mo, 870 fichiers).
6. **Regrouper `outputs/` + `design/` + `regime_diag/` + `breakout_container/` + `ftmo_profile_study/`
   + `research_artifacts/`** sous un même toit nommé explicitement — nécessite coordination avec le
   périmètre Multi_Asset (colleague), donc en dernier.
7. **`Equities/research/active/sector_hothand_propfirm/`** — relancer l'audit "obligatoire" ou le
   documenter comme volontairement en pause, pour que CLAUDE.md ne pointe pas vers un travail non fait.
