# PLAN 01 — audit de la couche narrative

**Date de l'audit : 2026-09-08.** Périmètre : documents qui racontent ce que le projet EST et où il
en est (constitution, README, ledgers, études orphelines, `_meta/`, `docs/`). **Aucun fichier n'a
été modifié, déplacé ni supprimé** — ce document est un plan, pas une exécution. Pour chaque
candidat à la suppression, les citations ont été vérifiées par `grep -r` avant tout verdict.

État de référence utilisé pour juger de la péremption : `git log` des 25 derniers commits (tous du
2026-09-06/07/08, programme macro + flag FOMC), `_meta/lessons_registry.md` (à jour au 2026-09-07,
L61-L67), `_meta/TODO.md` (2026-09-01), `_meta/decision_calendrier_overnight_2026-09.md`
(2026-09-01), et les dossiers `Multi_Asset/research/active/*_2026-09/`. `tools/check_register_integrity.py`
tourne **clean** au moment de l'audit (chaîne ledger `[108, 112, 115, 117]` monotone) — aucune des
recommandations ci-dessous ne le casse tant qu'elle est appliquée en respectant les notes de
citation.

---

## 1. Racine du dépôt

| Fichier | Ce qu'il affirme | Toujours vrai ? | Cité ailleurs |
|---|---|---|---|
| `CLAUDE.md` | Constitution complète : hard rules, gates, snapshot des 3 stratégies (A gelée, B testnet, C annulée), book FTMO funded, registre L11-L67, ledger n_tests. | **Oui.** Dernier commit 2026-09-01, cohérent avec tous les faits vérifiés (état FTMO, closes de septembre absentes seulement parce qu'elles n'existaient pas encore au 09-01 — normal). | Cité partout (racine du système de citation du dépôt) |
| `README.md` | Vitrine recruteur : book FTMO funded, méthodologie en 5 règles, extraits du registre L, carte du dépôt. En-tête **« Status — August 2026 »**. | **Partiellement.** Les chiffres (Sharpe 0.83, $10k, 23 jours, 154 mois) restent défendables. Mais (a) l'en-tête date d'août alors qu'on est en septembre, et (b) §« Reading this repository » renvoie vers `_meta/roadmap_ftmo_2026.md` comme référence de « where the work is going » — **exactement le document que le propriétaire cite comme périmé**. | C'est le point d'entrée du dépôt — cité nulle part en tant que cible, mais c'est lui qui cite les autres |
| `research_history.md` | Registre archive « DO NOT re-propose » (crypto n=159, FX n=181, equities/futures, options, deferred, untested). | **Oui**, par construction — c'est un registre figé de résultats négatifs historiques, pas une affirmation d'état courant. Aucun signe qu'un axe listé ait été rouvert sans y être noté. | 21 fichiers |
| `N_ledger.md` (racine) | Ledger détaillé du programme `btc_intraday_ftmo` (crypto CFD FTMO, juillet 2026) : BTC intraday long-only tué, spread-MR indices tué, semivar-reversal tué, mois-fin-rebond validé mais pas déployé. | **Orphelin.** Aucune mention de `btc_intraday_ftmo` dans aucun document de septembre, aucune trace dans le book déployé actuel (overnight US100/GER40 + ORB — zéro crypto). Le contenu lui-même est un verdict daté, pas faux — mais il vit à la racine au lieu de `Crypto/research/{active,archived}/`, en violation de la carte du dépôt que `README.md` affiche lui-même. | `SLEEVE_month_end_bounce.md`, `design/PREREG_audit_month_end_20260712-1644.md`, `_meta/cleanup/inventaire_untracked.csv` |
| `STRATEGY_RESEARCH_LOG.md` | En-tête : **« Strategy A (TSMOM): LIVE on testnet — Strategy B: LIVE on testnet — Strategy C: RESEARCH ONGOING »**. | **Faux au sens strict, aujourd'hui.** A est gelée depuis 2026-05-30, C est annulée depuis 2026-06-10. Le fichier est **déjà correctement étiqueté « superseded »** dans `docs/RESEARCH_JOURNAL_2026-05.md:29` — mais ce bandeau ne vit PAS dans le fichier lui-même. Quelqu'un qui ouvre `STRATEGY_RESEARCH_LOG.md` directement (fichier root, 32 Ko, nom qui sonne comme LE journal de recherche) ne voit aucun avertissement. | 14 fichiers, dont 3 le citent comme provenance de leçons gravées (L37-L39) — **ne jamais réécrire le contenu** (convention « artefacts jamais réécrits ») |
| `SLEEVE_month_end_bounce.md` | Fiche-sleeve BTC crypto FTMO « candidate validée », datée 2026-07-12, présentée avec un front de sizing complet comme si elle attendait un feu vert de déploiement. | **Orphelin, statut ambigu.** Ni confirmée déployée ni explicitement abandonnée nulle part. Le book déployé (CLAUDE.md, README) ne contient aucune sleeve crypto. Un lecteur ne peut pas savoir si c'est « en attente » ou « mort silencieusement ». | `N_ledger.md` (racine, réciproque) |
| `STUDY_BREAKOUT_CONTAINER_2026-06-20.md` | Étude verdictée « DILUTES » (une sleeve breakout dilue la survie funded), datée 2026-06-20, avec pré-registration et VERDICT explicites. | **Contenu exact**, mais **0 citation nulle part dans le dépôt** — orpheline complète, invisible depuis `README.md`, `_meta/research_active.md` ou tout autre index. | **0** |
| `STUDY_REGIME_DIAGNOSTIC_2026-06-20.md` | Diagnostic verdicté « DISPERSED » (pas d'axe macro robuste pour un overlay de régime), même date, même format frozen. | **Contenu exact**, même problème : **0 citation**. | **0** |

**Lecture d'ensemble racine** : le dépôt affiche sa propre carte dans `README.md` (« Repository map »)
— `<AssetClass>/research/{active,archived}/` — et 4 fichiers à la racine (`N_ledger.md`,
`SLEEVE_month_end_bounce.md`, `STUDY_BREAKOUT_CONTAINER_2026-06-20.md`,
`STUDY_REGIME_DIAGNOSTIC_2026-06-20.md`) contredisent cette carte par leur simple emplacement. Ce
n'est pas un problème de véracité du contenu (les 4 sont honnêtes, verdictés, datés) — c'est un
problème de **navigabilité** : un recruteur qui suit la carte affichée ne les trouvera jamais, et un
recruteur qui liste la racine tombe sur des fichiers non annoncés par la carte.

**Verdicts et actions** :
- `CLAUDE.md` → **GARDER**.
- `README.md` → **METTRE À JOUR** : (1) rafraîchir l'en-tête « August 2026 » → septembre + chiffres
  au jour ; (2) remplacer ou corriger le pointeur vers `_meta/roadmap_ftmo_2026.md` (voir §2) — soit
  le roadmap est réécrit d'abord, soit le pointeur est redirigé vers `_meta/TODO.md`, seul document
  réellement à jour sur « où va le travail ».
- `research_history.md` → **GARDER**.
- `N_ledger.md` (racine) → **DÉPLACER** vers `Crypto/research/archived/btc_intraday_ftmo/` (ou
  `active/` si le mois-fin-rebond reste une candidate vivante — à trancher par le propriétaire, pas
  par ce plan). Mettre à jour les 2 citations (`SLEEVE_month_end_bounce.md`,
  `design/PREREG_audit_month_end_20260712-1644.md`) pour pointer vers le nouveau chemin.
- `STRATEGY_RESEARCH_LOG.md` → **METTRE À JOUR (minimal)** : ajouter une ligne de bandeau en tout
  premier caractère du fichier — `⚠ ARCHIVÉ — superseded, contenu antérieur au 2026-06-09 (Strategy
  A et C ont depuis changé de statut). Conservé comme provenance des leçons L37-L39. État courant :
  CLAUDE.md.` — **sans toucher au corps** (convention artefacts non réécrits). Ne pas déplacer : le
  chemin racine est cité tel quel par 3 leçons gravées.
- `SLEEVE_month_end_bounce.md` → **DÉPLACER** avec `N_ledger.md` vers le même dossier
  `Crypto/research/{active,archived}/btc_intraday_ftmo/`, et ajouter une ligne de statut explicite
  (« déployé : non » ou « abandonné : depuis telle date ») — décision du propriétaire.
- `STUDY_BREAKOUT_CONTAINER_2026-06-20.md`, `STUDY_REGIME_DIAGNOSTIC_2026-06-20.md` → **DÉPLACER**
  vers `Multi_Asset/research/archived/` (verdicts négatifs, 0 déploiement, cohérents avec le style
  des autres dossiers `Multi_Asset/research/active/*_2026-08/`). Sûr : 0 citation à corriger.

---

## 2. `_meta/`

| Fichier | Ce qu'il affirme | Toujours vrai ? | Cité ailleurs |
|---|---|---|---|
| `roadmap_ftmo_2026.md` | Daté 2026-08-20 : compte funded « armé depuis 3 jours », solde 10 013.88, plan détaillé vers $200k funded (scaling fermé, achat direct de $200k, TODO priorisée §4). | **Non — l'exemple cité par le propriétaire.** Trois semaines de dérive : le solde a changé, la section TODO §4 a été en grande partie remplacée par `TODO.md` (2026-09-01, plus précis : dérapage ORB N=30, décision ORB octobre) et par `decision_calendrier_overnight_2026-09.md` (question tranchée qui n'apparaît nulle part dans le roadmap). Le narratif dominant de septembre — programme macro à 6 rounds, filtre FOMC prêt pour le 12 — **n'existe pas** dans ce document, qui reste centré sur un objectif $200k dont rien dans les 25 derniers commits ne parle plus. | `README.md` (pointeur « where the work is going »), `Multi_Asset/research/active/funded_reference_2026-09/CHIFFRES_REFERENCE.md` (citation historique, correcte en contexte), 2 rapports d'audit passés |
| `current_focus.md` | En-tête « Last updated: 2026-06-10 ». Bloquants : bascule mainnet B (~2026-07-17, dépassée de 2 mois), reboot VPS. Chiffre SR corrigé une fois (08-24) mais le reste (axes de recherche §, décisions pendantes) intact depuis juin. | **Non.** 90 jours de dérive au jour de cet audit. Le fichier lui-même se présente comme « mis à jour à chaque session » — c'est démontrablement faux : `_automation/synthesis/_state.json` (pipeline automatique du dépôt lui-même) l'a signalé stale **7 semaines de suite** (W28→W33, 39→67 jours de dérive) avant même cette session. La correction du 08-24 n'a traité qu'un seul chiffre (SR 2.31), pas la fraîcheur générale. | **Cité directement par `CLAUDE.md`** (§Current focus) comme LE pointeur vers l'état opérationnel courant — c'est la citation la plus dangereuse du dépôt : la constitution elle-même mène un lecteur vers un document obsolète |
| `TODO.md` | « État au 2026-09-01. » Le plus à jour des documents `_meta/` — items datés, priorisés, avec critère de fin. | **Globalement oui**, mais une semaine derrière les commits du 09-06/07 (conclusion du programme macro round 6, audit du filtre FOMC « GEL avant samedi » = déploiement 12/09, étude bust 5 ans zéro-bust, kill Ranaldo). L'item #1 (payout, solde au 01/09) et #4 (liste de branches à merger) sont probablement dépassés une semaine plus tard. | 1 fichier (`RAPPORT_navigabilite.md`, historique) |
| `open_questions.md` | Daté 2026-05-29 : question infra non tranchée (placement de `manual_signal.sh`/`plist`, Strategy C vs D). | **Toujours ouverte, vérifiée** : les deux emplacements (`Futures/live/strategy_c_live/` et `Futures/research/active/strategy_d/infra/`) existent encore aujourd'hui, non résolus. Honnêtement présentée comme « à trancher », donc pas une fausse affirmation — mais 100+ jours sans qu'aucune session ne la reprenne. | 7 fichiers, tous des audits `_audit/` de mai (historiques) |
| `research_active.md` | Inventaire des chantiers ouverts. §Tronc Multi_Asset mis à jour 2026-08-24 (48 dossiers). Section hors-Multi_Asset explicitement marquée « datent de 2026-05-30, non retouchées ». | **Le fichier ment moins qu'il n'en a l'air** : il s'auto-dénonce déjà comme partiellement périmé (bonne pratique). Mais le tableau Multi_Asset s'arrête à 08-24 et ne couvre pas les ~20 nouveaux dossiers de septembre (`macro_round1-6_2026-09`, `flag_calendaire_2026-09`, `bust_intraday_2026-09`, `funded_5ans_2026-09`, etc. — visibles dans `Multi_Asset/research/active/`). | 6 fichiers |
| `lessons_registry.md` | Registre L11-L67 + section « CANDIDATES nommées en session ». | **À jour** — dernière écriture 2026-09-07 (L67 gravée, candidate « attribution-du-kill » en attente de réconciliation). | 19 fichiers |
| `n_tests_ledger.md` | Convention de comptage n_tests, milestones figés à 321. | **Oui**, document de convention stable par construction. | 7 fichiers |
| `l_aliases.md` | Table d'alias historiques (« L33 candidate » → L45, etc.). | **Oui**, cohérente avec `CLAUDE.md` §Aliases historiques. | 2 fichiers |
| `data_governance.md` | Règles de gouvernance des données, audit du 2026-06-10. | **Oui**, règles stables, aucun signe de dérive. | 3 fichiers |
| `reconciliation_2026-06-10.md` | Journal de la session de réconciliation du 10 juin. | **Oui** — document d'archive ponctuel, ne prétend pas décrire l'état courant. | 2 fichiers |
| `plan_book_perso_2026-08.md` | Plan du book IBKR perso (2026-08-28) : sleeve month-end ZN « déployable aujourd'hui », compte pas encore ouvert. | **Oui, cohérent** avec `TODO.md` (« Ouvrir le compte IBKR » listé en Nov-déc, chemin critique ~2 semaines) — ne prétend pas que le compte est ouvert. | 1 fichier |
| `decision_calendrier_overnight_2026-09.md` | Décision tranchée le 2026-09-01, calendrier lundi+mardi maintenu. | **Oui**, à jour, cohérent avec le book déployé décrit dans `CLAUDE.md`. | 1 fichier |
| `README.md` (`_meta/`) | Index du dossier `_meta/`, avec avertissement explicite « check "last updated" before trusting it » sur `current_focus.md`. | **Oui** — méta-document bien conçu, s'auto-protège déjà contre la dérive qu'il décrit. | Aucune citation entrante trouvée, mais rôle d'index local |
| `_meta/cv/` | Ne contient QUE `.DS_Store` sur le disque. `git status` montre `contexte_pour_claude_cv_2026-09.md` (le dossier de contexte pour la recherche de stage — projets au centre, écrit le 09-04) comme **supprimé, non commité**. | **Anomalie opérationnelle à signaler, pas à corriger ici.** Ce fichier est exactement le document qui sert de pont entre ce dépôt et un recruteur — sa disparition (accidentelle ou volontaire ?) mérite une question directe au propriétaire avant tout arbitrage. `.DS_Store` est un résidu macOS sans valeur, à ignorer via `.gitignore` s'il ne l'est pas déjà. | Aucune citation (isolé) |
| `_meta/veille/` (2 rapports) | Revues de littérature externe (notebooks Dedale, modèle macro Hawkline). Datés 2026-08. | **Oui**, activement utilisés en amont des programmes macro de septembre. | 3 fichiers, dont 2 programmes de recherche actifs de septembre |
| `_meta/cleanup/` (4 rapports + CSV) | Rapports d'audits de nettoyage passés (branches, navigabilité, rescue, untracked). | **Oui**, documents d'archive ponctuels correctement datés, aucun ne prétend décrire l'état courant. Le rapport `RAPPORT_navigabilite.md` (2026-08-22) a d'ailleurs déjà traité 4 des problèmes de sévérité haute/moyenne trouvés à l'époque (corrections du 08-24 vérifiées tenir encore aujourd'hui). | Auto-référencés entre eux |

**Doublons identifiés** :
- **`N_ledger.md` (racine) vs `_meta/n_tests_ledger.md`** : **pas un doublon**, malgré le nom
  proche. `_meta/n_tests_ledger.md` est LA convention de comptage globale (milestone 321,
  méthodologie). `N_ledger.md` (racine) est le ledger LOCAL d'UN programme (`btc_intraday_ftmo`) —
  exactement comme `Forex/research/active/fx_intraday_deepdive/N_ledger.md` en est un autre. Le
  vrai problème n'est pas la duplication conceptuelle, c'est l'**emplacement** : ce ledger-programme
  est le seul de tout le dépôt à vivre à la racine au lieu de dans son dossier de recherche (voir §1).
- **`STRATEGY_RESEARCH_LOG.md` (racine) vs `research_history.md` (racine) vs `CLAUDE.md`** : chaîne
  de supersession à trois niveaux, déjà partiellement documentée (`docs/RESEARCH_JOURNAL_2026-05.md`
  dit se substituer à `STRATEGY_RESEARCH_LOG.md` ; `README.md` dit que le journal est lui-même
  superseded). Chaque maillon s'auto-déclare — sauf `STRATEGY_RESEARCH_LOG.md` qui ne porte AUCUNE
  mention de son propre statut (voir action §1).
- **`_meta/current_focus.md` vs `_meta/TODO.md`** : se recouvrent largement (axes de recherche,
  décisions pendantes, blocages). `TODO.md` est structurellement plus récent et mieux tenu. Une fois
  `current_focus.md` remis à jour ou retiré, envisager de fusionner les deux — sinon le dépôt garde
  deux pointeurs concurrents vers « ce qui se passe maintenant », et celui que `CLAUDE.md` cite
  (`current_focus.md`) est le plus périmé des deux.

**Verdicts et actions** :
- `roadmap_ftmo_2026.md` → **METTRE À JOUR intégralement** (réécriture, pas retouche : solde,
  section §4 TO-DO à refaire contre l'état de `TODO.md` + les conclusions de septembre, ou retirer
  la section « roadmap $200k » si l'objectif n'est plus le narratif actif) — **priorité 1**, voir §5.
- `current_focus.md` → **METTRE À JOUR intégralement**, ou fusionner dans `TODO.md` et repointer
  `CLAUDE.md` §Current focus vers `TODO.md` — **priorité 2**, voir §5.
- `TODO.md` → **METTRE À JOUR** (rafraîchissement léger : items 1 et 4 contre l'état du 09-08).
- `open_questions.md` → **GARDER**, mais demander un arbitrage (trancher ou clore explicitement).
- `research_active.md` → **METTRE À JOUR** : ajouter les ~20 dossiers de septembre au tableau Tronc
  Multi_Asset (travail mécanique, verdicts déjà écrits dans chaque dossier).
- `lessons_registry.md`, `n_tests_ledger.md`, `l_aliases.md`, `data_governance.md`,
  `reconciliation_2026-06-10.md`, `plan_book_perso_2026-08.md`,
  `decision_calendrier_overnight_2026-09.md`, `_meta/README.md`, `_meta/veille/`, `_meta/cleanup/`
  → **GARDER**.
- `_meta/cv/contexte_pour_claude_cv_2026-09.md` → **NE PAS AGIR** (hors périmètre : question à
  poser au propriétaire — suppression volontaire ou accident ?). `.DS_Store` → à ajouter au
  `.gitignore` s'il ne l'est pas.

---

## 3. `docs/`

| Fichier | Ce qu'il affirme | Toujours vrai ? | Cité ailleurs |
|---|---|---|---|
| `docs/ARCHITECTURE.md` | Cartographie du système live (`ftmo_live/`) — chaîne EA/brain/supervisor/reconcile, sourcée sur le code tracké + un audit du 08-18. | **Oui**, écrit et audité récemment (2026-08-22), aucun signe de dérive. | 5 fichiers |
| `docs/RESEARCH_METHOD.md` | Cycle de recherche (pré-registration → RESULTS.md → amendement), méthodologie stable. | **Oui** — document de méthode, pas d'état, n'a pas de date de péremption naturelle. | 5 fichiers |
| `docs/RESEARCH_JOURNAL_2026-05.md` | Journal historique de mai 2026, 138 Ko. | **Correctement encadré** : `README.md` le présente explicitement comme « historical journal, superseded but kept for the record » et note que « several of its figures have since been corrected — corrections are documented rather than overwritten ». Aucune action requise — c'est le modèle à suivre pour `STRATEGY_RESEARCH_LOG.md`. | 2 fichiers |
| `docs/archive/` | `legacy_crypto_readme.md` + sous-dossier `2026-04/`. | Correctement rangé sous `archive/`, hors périmètre d'audit approfondi (nom de dossier auto-descriptif, aucun signal de contradiction trouvé en survol). | Non vérifié en détail |

**Verdicts** : `docs/ARCHITECTURE.md`, `docs/RESEARCH_METHOD.md`, `docs/RESEARCH_JOURNAL_2026-05.md`,
`docs/archive/` → **GARDER**. C'est le sous-dossier le plus propre de tout l'audit.

---

## 4. Hors périmètre git — mentionné dans la mission

| Fichier | Constat |
|---|---|
| `<HOME>/CLAUDE.md` | Fichier séparé, **hors dépôt git** (`<HOME>/`, pas de `.git` parent), donc **invisible à tout recruteur qui clone/consulte le dépôt** — `check_register_integrity.py` ne peut ni le voir ni le casser. Daté du **23 mai 2026** (jamais retouché depuis), 2.7 Ko contre 41.9 Ko pour la constitution du dépôt : profil « M1 IEF » (obsolète), aucune trace des stratégies actuelles, du book FTMO funded ni du registre L. Risque réel mais différent : ce fichier influence les sessions Claude Code futures lancées **hors du dossier du dépôt**, pas l'image donnée à un recruteur. **Action recommandée (hors du présent plan git)** : soit le supprimer (le `CLAUDE.md` du dépôt suffit dès qu'on travaille dedans), soit le réduire à un pointeur d'une ligne vers le dépôt. Ne compte pas dans les verdicts GARDER/METTRE À JOUR/DÉPLACER/SUPPRIMER puisqu'il n'est pas trackable par l'outil d'intégrité. |

---

## 5. Les 5 corrections qui comptent le plus

Par ordre de dégât potentiel si un recruteur les voit en l'état :

1. **`README.md` → `_meta/roadmap_ftmo_2026.md`.** C'est le tout premier document que la page
   d'accueil du dépôt recommande de lire en second (« Then `_meta/roadmap_ftmo_2026.md` for where
   the work is going »). Le document cible est daté d'il y a trois semaines, centré sur un objectif
   ($200k funded) dont plus aucun commit récent ne parle, et c'est **littéralement l'exemple donné
   par le propriétaire** de document périmé. Un lecteur qui suit le README à la lettre atterrit
   directement sur le pire cas.
2. **`_meta/roadmap_ftmo_2026.md` lui-même.** Au-delà du pointeur cassé, le contenu doit être
   réécrit contre l'état de `TODO.md` (2026-09-01) et des 25 derniers commits — sinon la correction
   du point 1 ne fait que déplacer le problème d'un clic.
3. **`STRATEGY_RESEARCH_LOG.md`.** Fichier de 32 Ko à la racine, sans aucun bandeau, dont la
   première ligne lisible affirme « Strategy A: LIVE on testnet » et « Strategy C: RESEARCH
   ONGOING » — deux affirmations que `CLAUDE.md`, à 30 secondes de lecture plus loin, contredit
   frontalement (A gelée, C annulée). C'est exactement le scénario « fait douter de tout le reste »
   décrit dans la mission : deux documents à la racine, contradiction directe, aucun signal de
   hiérarchie entre eux pour qui ne connaît pas la convention interne.
4. **`CLAUDE.md` → `_meta/current_focus.md`.** La constitution elle-même — le document le plus
   digne de confiance du dépôt — pointe vers un fichier stable à 90 jours de retard, avec un
   en-tête qui prétend le contraire (« mis à jour à chaque session »). Le pipeline d'automatisation
   du dépôt l'a lui-même signalé sept semaines de suite avant cette session sans qu'aucune ne le
   corrige entièrement.
5. **Les 4 orphelins racine** (`N_ledger.md`, `SLEEVE_month_end_bounce.md`,
   `STUDY_BREAKOUT_CONTAINER_2026-06-20.md`, `STUDY_REGIME_DIAGNOSTIC_2026-06-20.md`). Contenu
   honnête individuellement, mais leur simple présence contredit la carte du dépôt que `README.md`
   affiche lui-même. Un recruteur compétent qui compare la carte annoncée à un `ls` de la racine
   remarque l'écart en quelques secondes — et un des quatre (`SLEEVE_month_end_bounce.md`) laisse
   planer une ambiguïté sur le statut (déployée ou non) d'une sleeve crypto qui n'existe nulle part
   ailleurs dans le narratif courant.

**Par quoi commencer** : 1 et 2 ensemble (un seul geste : réécrire le roadmap, corriger le pointeur
README) réparent le chemin que suivra tout lecteur qui fait ce que le README lui demande de faire.
Puis 3 (un bandeau d'une ligne, coût minimal, gain de crédibilité immédiat). 4 et 5 demandent plus
de travail de fond (réécriture ou fusion de documents, déplacements avec mise à jour de citations)
et peuvent suivre.
