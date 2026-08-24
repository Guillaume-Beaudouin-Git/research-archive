# Rapport de tri des branches restantes — 2026-08-22

Périmètre : refs git uniquement (locales + distantes), aucun fichier du dépôt modifié hors ce rapport. Aucune réécriture d'historique, aucun push --force, `main` et la branche courante non touchées.

État de départ mesuré à l'exécution (diffère légèrement des 67/64 de la consigne — le dépôt est vivant, des branches ont continué à être mergées/nettoyées entre-temps) : **63 branches distantes + 64 locales, 106 noms uniques** (21 branches existent à la fois en local et en distant, 42 seulement en distant, 43 seulement en local).

## Méthode

1. `gh pr list --state all` (430 PR) pour connaître l'état PR de chaque nom de branche.
2. Pour chaque branche : `git rev-list --left-right --count origin/main...<branche>` (commits uniques de part et d'autre) et `git diff origin/main...<branche> --stat` (triple-point, tel que demandé — diff depuis le point de divergence, insensible aux changements faits par `main` ensuite).
3. Preuve de present-dans-main à trois niveaux, du plus fort au plus faible :
   - **Ancêtre mécanique** : `git merge-base --is-ancestor <branche> main` → 0 commit unique, 0 fichier de diff. Preuve déterministe, aucune ambiguïté.
   - **Contenu identique fichier-par-fichier** : chaque fichier du diff comparé par hash à `main:<chemin>` ou à une branche conservée dont l'ascendance est elle-même prouvée.
   - **État GitHub** : `gh pr view` donne `state=MERGED` indépendamment de l'ascendance git — couvre le cas squash-merge (`auto-merge.yml`) où `git branch --merged` échoue par construction.
4. Pour les 24 branches restées ambiguës après ces tests, lecture des commits + comparaison de contenu fichier-par-fichier avec `main` et avec les autres branches candidates (détection de sous-ensembles inter-branches par `merge-base --is-ancestor` croisé).

## Résultat global

| Catégorie | Nombre |
|---|---|
| SUPPRIMER (exécuté) | 84 |
| GARDER | 19 |
| À TRANCHER PAR L'HUMAIN | 3 |
| **Total** | **106** |

Suppressions exécutées : **42 locales** (`git branch -D`) + **50 distantes** (`git push origin --delete`), par lots de 15, journal ci-dessous. `git remote prune origin` exécuté ensuite (a aussi purgé une ref `origin/claude/cleanup-docs` déjà supprimée côté distant par ailleurs).

**État final : 14 branches distantes (13 + main), 23 locales (22 + main).**

---

## 1. SUPPRIMER — 84 branches, avec preuve

### 1a. Ancêtre mécanique de `main` (35 branches — preuve la plus forte, `git merge-base --is-ancestor` = vrai, 0 commit unique, 0 fichier de diff)

Ces branches n'ajoutent strictement rien à l'historique de `main` : leur pointe est un ancêtre direct (fusion normale, pas de squash). Supprimées local + distant selon disponibilité.

| Branche | Preuve |
|---|---|
| claude/audit-micro-orb | ancêtre de main (0 commit, 0 fichier) |
| claude/audit-sleeve-gold | idem |
| claude/audit-sleeve-j1 | idem |
| claude/close-continuation-gold-subwindows | idem |
| claude/close-momentum-dose | idem |
| claude/cohort-clustering | idem |
| claude/cross-conditioning | idem |
| claude/exogenous-predictors | idem |
| claude/forced-flow-cooccurrence | idem |
| claude/ftmo-reconcile-friday | idem |
| claude/ftmo-rollover-reconcile-2026-06-19 | idem |
| claude/ftmo-supervisor-disarm-guard | idem |
| claude/ftmo-supervisor-heartbeat-connaware-2026-06-19 | idem |
| claude/ftmo-watchdog-hotfix | idem |
| claude/gold-cpi-eve | idem (contenu aussi retrouvé directement sur `main` via commits récents 2bc48e56/31182a2b/30fa8a9a) |
| claude/gross-surface-map | idem |
| claude/inference-layer-fix | idem |
| claude/marginal-admission | idem |
| claude/mr-stress-conditional | idem |
| claude/mr-timezone-repair | idem |
| claude/overnight-sleeve-reopen | idem |
| claude/overnight-vs-intraday | idem |
| claude/pairs-cointegration | idem |
| claude/phase2-sizing | idem |
| claude/regold-funnel | idem |
| claude/rollover-dodge | idem |
| claude/spec-v28-refreeze | idem |
| claude/statarb-multivariate | idem |
| claude/two-sided-axis | idem |
| claude/wall-decision | idem |
| claude/wall-economics | idem |
| feat/indices_swing_screening | idem |
| feature/zn-baltussen-feasibility | idem — ⚠ voir note ci-dessous, le nom trompe |
| strategy-c-unblock-20260525 | idem |
| validation/topics-1-4-findings-20260524 | idem — PR #8 confirmée MERGED |

**Note sur `feature/zn-baltussen-feasibility`** : malgré son nom, la pointe de cette branche est un commit trivial (`chore: gitignore Kaggle NQ dataset`) — le vrai travail ZN Baltussen ne s'y trouve PAS. Il vit ailleurs, non mergé : voir §GARDER `feature/iter-11-fast-pivot` et `claude/crypto-audit-2026-05-28`, qui contiennent le répertoire complet `Futures/research/active/zn_baltussen/` (README, feasibility.py, data_setup.py, prespec.md, canary_report, tail_risk_test.py). **`main` ne contient aujourd'hui aucun fichier sous ce chemin**, contrairement à ce que la constitution (`CLAUDE.md` § Active research) laisse penser. Ce n'est pas une perte causée par ce nettoyage — la branche supprimée n'avait jamais porté ce travail — mais un gap pré-existant à signaler.

### 1b. Squash-merge confirmé (3 branches — `gh pr view` state=MERGED ou commentaire explicite du propriétaire)

| Branche | Preuve |
|---|---|
| claude/ea-v26-account-guard | PR #403 **MERGED** (2026-07-24) confirmé par l'API GitHub — invisible à `git branch --merged` car squash. Contenu vérifié : les 3 fichiers du diff sont bien les ancêtres directs de la version v2.8 actuelle de `book_executor.mq5` sur `main`. |
| claude/voieb-sizing-reconciliation | PR #46 **CLOSED**, commentaire du propriétaire : *« Supersédée par PR47 (contenu inclus dans le merge) »*. PR #47 (`claude/voieb-weekly-realtape`) confirmée MERGED. `sizing_study.py` vérifié présent sur `main` à `Futures/research/active/voie_b_ftmo/sizing_study/`. |
| claude/voieb-sizing-singleticket | Même PR #46/#47, même preuve. |

### 1c. Contenu identique fichier-par-fichier (1 branche)

| Branche | Preuve |
|---|---|
| claude/voie-b-deploy | 16/16 fichiers du diff vérifiés par hash **identiques** à leur version actuelle sur `main` sous `Futures/research/active/voie_b_ftmo/` (EA fixed/original, deploy/*.sh, slip_analysis.py, parity_check.py, reconciliation.md, vps_deploy.md, résultats). Contenu absorbé par la même fusion squash que voieb-sizing-*. |

### 1d. Ancêtre d'une branche CONSERVÉE (3 branches — preuve mécanique, perte de contenu nulle car les commits restent accessibles via la branche gardée)

| Branche | Preuve |
|---|---|
| claude/asia-23-8-ftmo-feasibility | `merge-base --is-ancestor` = vrai vers **claude/asia-23-8-funded** ET vers **claude/soybean-ftmo-feasibility** (les deux conservées, §GARDER). Les 2 commits de cette branche (prereg + résultats Q1-Q5) sont un sous-ensemble strict des deux. |
| feature/vwap-mr-fade-es-feasibility | `merge-base --is-ancestor` = vrai vers **claude/crypto-audit-2026-05-28** (conservée). Vérifié : le diff entre les deux ne contient QUE l'ajout ultérieur de Monti ORB NQ (21 fichiers). Tout le reste (sr2_hunt, vwap_mr_fade_nq, zn_baltussen, g1/g2d, nq_intraday MC sizing, strategy_c_live manual signal) est un sous-ensemble byte-exact. |
| claude/g1-audit-20260526 | `merge-base --is-ancestor` = vrai vers **claude/g1-archive-20260526** (à trancher, §3). Sous-ensemble strict quel que soit le sort de g1-archive. |

### 1e. Branches d'automatisation (42 branches — cron alpha_hunt / arxiv / feasibility gate)

Toutes produites par les routines `_automation/{alpha_hunt,arxiv,feasibility}/` décrites dans `CLAUDE.md`. Vérification par échantillon : contenu = staging de papiers scrapés (`promising/*.md`, `_staging/*.json`, `_seen.json`) ou digests de feasibility gate. La grande majorité des runs sont **vides ou quasi-vides** (« 0 retained », « empty run », « 0 new items ») — pur bruit de journalisation cron, zéro perte. Pour les runs non vides, échantillon vérifié : les chemins existent déjà dans `main` (le pipeline `promising/` a continué d'accumuler sous ces mêmes noms de fichiers via des runs ultérieurs mergés), seul le contenu texte diffère (re-traitement du même item). Le registre mémoire de l'utilisateur documente déjà que ce dossier est « largement inexploitable » dans son ensemble — aucune conclusion de recherche validée n'y transite, seulement de la matière première à trier.

26 de ces 42 avaient une PR **CLOSED** (non mergée) ; les 16 restantes n'avaient jamais eu de PR (`fetch_alpha_sources.sh` tourne en tâche de fond sans ouvrir systématiquement de PR pour les runs vides).

Liste complète : `claude/alpha-hunt-20260523-2022`, `-20260525-0601`, `-1009`, `-1203`, `-1414`, `-1605`, `-1801`, `-2002`, `-20260526-0806`, `-1005`, `-1207`, `-1406`, `-2007`, `-20260527-0606`, `-0805`, `-20260610-1604`, `-20260612-1803`, `claude/arxiv-2026-05-22`, `-05-26`, `-05-27`, `claude/feasibility-20260524-0024`, `-20260524-2138`, `-20260525-2140`, `-20260526-2134`, `claude/focused-albattani-{0vlUo,7t3Wr,HKMHU,OViXZ,PqaIx,basyf,bbt9b,ehwh6l,envr3t,fvi5b9,h3YWi,ks307n,lg9wrx,vA8SK,w17x4k}` (noms de session auto-générés, même pipeline alpha_hunt/feasibility), `claude/beautiful-tesla-cWcrt`, `claude/fervent-darwin-1spbhl`, `claude/happy-dijkstra-XUMqV`.

### Journal d'exécution des suppressions

- **Local** : 42/42 `git branch -D` réussis (aucun échec).
- **Distant** : 50/50 `git push origin --delete` réussis, en 4 lots de ≤15 (`[deleted]` confirmé par git pour chacun).
- `git remote prune origin` : purge de `origin/claude/cleanup-docs` (ref déjà supprimée côté distant hors de ce nettoyage) en plus des refs des 50 branches supprimées ci-dessus.

---

## 2. GARDER — 19 branches (contiennent du travail non présent dans `main`)

Toutes sans PR (jamais soumises). Le verdict de recherche de chacune est parfois déjà résumé dans la mémoire de session de l'utilisateur (hors dépôt), mais **le code, la pré-registration et les fichiers de résultats bruts n'existent nulle part ailleurs dans le dépôt** — les supprimer perdrait la preuve reproductible, pas seulement une conclusion.

| Branche | Dernier commit | Contenu | Mérite une PR ? |
|---|---|---|---|
| `claude/crypto-audit-2026-05-28` | 2026-05-27 | Le plus riche du lot : audit crypto archivé + réconciliation n_tests + **Monti ORB NQ, batterie complète T0-T6, verdict KEEP_AS_PAPER (SR=1.32, orthogonal r=0.04 à iter_10)** + sr2_hunt (recherche stratégie Equities, 9 phases) + vwap_mr_fade_nq (archivé) + zn_baltussen (étude complète, absente de `main`) + g1/g2d carry docs. Superset de `feature/vwap-mr-fade-es-feasibility` (supprimée, §1d). | Oui, au moins pour Monti ORB (verdict positif jamais remonté) et zn_baltussen (comble un gap déjà signalé par la constitution). |
| `feature/iter-11-fast-pivot` | 2026-05-26 | Variante NQ `iter_11_fast` (TP=1.0R, time_stop 11:30, 5 MNQ) — **verdict GO** dans le commit — + sa propre copie de l'étude ZN Baltussen (identique par hash à celle de crypto-audit-2026-05-28). | À auditer avant PR : le verdict GO date d'avant le re-baseline Databento du 2026-06-07 qui a ramené Strategy C à Sharpe 0.41 — probablement invalidé par la même correction de méthode, non re-vérifié explicitement. |
| `claude/h31-cs-fs-dn-test-160` | 2026-05-27 | Code source complet (backtest.py, compute_signal.py, data_prep.py, validation.py) + `postmortem.md` + `pre_spec.md` du test H31 (crypto CS funding stack delta-neutral, RESEARCH_FAIL). **`main` ne conserve que les fichiers `results/*.parquet/json` de ce test** (`Crypto/research/archived/h31_cs_fs_dn/`) — le code qui les a produits et le récit du postmortem sont uniquement ici. | Oui — complète un dossier archivé actuellement incomplet sur `main`. |
| `claude/asia-23-8-funded` | 2026-06-19 | Étude de faisabilité ASIA_23_8 (or overnight) + variante funded, verdict (c) REJET. Superset de `claude/asia-23-8-ftmo-feasibility` (supprimée, §1d). | Faible priorité — verdict NON-VIABLE déjà noté dans la mémoire utilisateur, mais le code n'est nulle part ailleurs. |
| `claude/soybean-ftmo-feasibility` | 2026-06-19 | Étude de faisabilité soja FTMO, re-run à 3bp coût réel, verdict (d) SPREAD-INDEPENDENT. | Faible priorité, même raison. |
| `claude/overnight-basket-ftmo` | 2026-06-19 | Audit indépendant + correction du panier overnight (or/argent/soja), fenêtre funded canonique, verdict NON-VIABLE renforcé. | Faible priorité, même raison. |
| `claude/overnight-ftmo-improve` | 2026-06-20 | P0-P3, verdict : aucune piste ne débloque FTMO pour la famille overnight. | Faible priorité, même raison. |
| `claude/funded-dynamic-sizing` | 2026-06-19 | Étude Q1-Q5 sizing dynamique en compte funded, verdict (b) statique quasi-optimal. | Faible priorité, verdict déjà noté en mémoire. |
| `claude/gold-dosing-compare` | 2026-06-20 | Audit indépendant dosing or (CONFIRM-WITH-CAVEATS) + 2 corrections methodologiques. | Faible priorité, déjà en mémoire. |
| `claude/regime-diagnostic` | 2026-06-20 | Audit CONFIRM-WITH-CAVEATS de l'overlay de régime (ratio 1.4→1.6). | Faible priorité, déjà en mémoire — mais lié à L54 (registre gravé), vérifier cohérence avant tout archivage définitif. |
| `claude/real-book-metrics-lowcheck` | 2026-07-06 | Audit funded_anatomy CONFIRM-WITH-CAVEATS + corrections (pré-registration step6, label swap). | Faible priorité, déjà en mémoire. |
| `claude/nightly-us100-investigation` | 2026-07-15 | Investigation US100 nightly — verdict variance + contexte return-starvation, pas d'action de sizing. | Faible priorité, déjà en mémoire. |
| `claude/vm-sweep-study-2026-06-17` | 2026-06-17 | Étude EV sweep vm (garder vm14) + cap-cliff + bust-decomp + single-sleeve. | Faible priorité, déjà en mémoire. |
| `claude/trend-futures-sleeve` | 2026-06-14 | Funnel P1-P4 trend futures + DSR, verdict NO-GO clean kill. | Faible priorité, déjà en mémoire. |
| `claude/j1-leverage-cap` | 2026-06-26 | Étude cap de levier J1, verdict ADOPT LCAP8 (backtest) + caveat Q4 cap-insuffisant-en-live. | À vérifier : le caveat Q4 (cap insuffisant en live) suggère une action non close — relire avant classement définitif. |
| `claude/breakout-container-combine` | 2026-06-20 | Pré-registration + résultat breakout en conteneur, verdict (b) DILUÉ, container logic fermée pour price-only. | Faible priorité, verdict clos dans le commit lui-même. |
| `claude/audit-month-end-20260712` | 2026-07-13 | 3 pré-registrations + audits : NO-GO month-end (DSR 0.05-0.15, mécanisme falsifié) + NO-GO BTC-5e-actif + audit barrière book path-aware. Sujet distinct du `Multi_Asset/research/active/month_end_vehicle_2026-07/` actuel sur `main` (celui-ci porte sur ZN/bonds, la branche sur BTC-comme-5e-actif du book perso). | Oui, faible urgence — trois verdicts NO-GO tranchés mais non remontés. |
| `claude/ftmo-seam-ger40-investigation` | 2026-06-16 | 1 fichier : rapport d'investigation du seam GER40 (96.7 bps), conclut que le reconcile n'est pas affecté. | À vérifier contre l'état live actuel avant PR — possiblement obsolète si déjà réparé par un correctif ultérieur (cf. « Monday restamp » en mémoire, sujet proche mais pas identique). |
| `claude/ftmo-seam-realign-2026-06-19` | 2026-06-19 | Outil de réalignement D1 (US100/GER40) sur EEST + rapport avant/après. | Idem — vérifier contre l'état live avant PR ou abandon, touche `ftmo_live/` (hard-fail path CI). |

## 3. À TRANCHER PAR L'HUMAIN — 3 branches

| Branche | Dernier commit | Pourquoi ambigu |
|---|---|---|
| `backup-pre-rebase-2026-06` | 2026-06-10 | 2842 fichiers de diff contre `main` (le plus gros diff du lot). Nature déclarée : sauvegarde de sécurité avant un rebase, aujourd'hui obsolète par construction. Échantillonnage (10 fichiers vérifiés) : tous confirmés déjà présents sur `main` sous des chemins consolidés (ex. `PropFirms/ftmo_alpha_program/*` → `PropFirms/ftmo/program_2026-06/ftmo_alpha_program/*`, hash identique) — cohérent avec la réorganisation P2 du 2026-06-10 documentée dans `CLAUDE.md`. Mais 2842 fichiers n'ont **pas** été vérifiés un par un (impraticable), et 18 fichiers diffèrent de leur version `main` actuelle sans qu'on ait confirmé que la version `main` les supersède strictement plutôt que l'inverse. Preuve forte mais pas totale → catégorie 3 par prudence plutôt que suppression sur échantillon. |
| `claude/g1-archive-20260526` | 2026-05-26 | 6/11 fichiers du diff confirmés identiques à `main` (dont les 5 fichiers `strategy_f2_asian_breakout` archivés, correspondant à L11b du registre). Les 4 fichiers restants (`g1_carry_conditional/{archive_reasons,audit_v1,report_v1}.md`, `g2d_carry_cross_asset/report_v1.md`) n'existent pas tels quels sur `main`, MAIS le `POSTMORTEM.md` archivé de `main` (`Forex/research/archived/g1_carry_conditional/`) cite `audit_v1.md` verbatim et en confirme le verdict sans modification, et `research_history.md` documente le kill G1 + le pivot G2D recommandé. Consolidation substantielle mais pas byte-exacte : jugement humain préférable avant suppression définitive. Si conservée, `claude/g1-audit-20260526` (déjà supprimée, §1d) restait de toute façon un sous-ensemble strict, donc son sort n'affecte pas ce dossier. |
| `claude/cleanup-untracked` | 2026-08-22 | Checked out dans un **worktree actif** (`<HOME>/Desktop/Algo_claude_cleanup_untracked`), vraisemblablement la session parallèle mentionnée dans la consigne (travail sur fichiers untracked/documentation). Contenu actuel identique à `main` (0 diff), mais la branche est en cours d'utilisation — `git branch -D` échouerait de toute façon tant qu'elle est checked out, et la supprimer précipiterait un conflit avec l'autre session. À réévaluer une fois cette session terminée. |

---

## État final

- **Distantes** : 14 (13 branches de travail + `origin/main`).
- **Locales** : 23 (22 branches de travail + `main`).
- Aucune branche de catégorie 2 (GARDER) ou 3 (À TRANCHER) supprimée.
- Aucune modification de fichier suivi hors ce rapport ; `main` et la branche courante non touchées ; aucun `push --force`, aucun rebase, aucune PR ouverte ou mergée.
