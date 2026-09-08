# PLAN 04 — Audit opérationnel & code (2026-09-08)

Périmètre : `ftmo_live/`, `strategies/`, `Portfolio/`, `_automation/`, `data/`, `scripts/`,
`tools/`, `tests/`, `logs/`, `_downloads_logs/`, `_audit/`, plus deux découvertes hors
périmètre initial mais dans le même dossier racine (`.worktrees/`, bloat `.git`).
**Aucun fichier modifié, déplacé ou supprimé — lecture seule + `git log`/`git ls-files`/
`git rev-list` sur l'historique.** Aucun sous-agent, aucun moniteur, aucune connexion VPS.

Méthode : pour chaque module, `grep -rl` des imports/appels depuis l'extérieur, confrontation
au crontab documenté dans `ftmo_live/README.md` et `CLAUDE.md` (§VPS), puis verdict
VIVANT / MORT / DOCUMENTAIRE / À GITIGNORER.

---

## 1. Tableau par module

| Module | Fichiers | Statut | Preuve |
|---|---|---|---|
| `ftmo_live/brain.py` | 1 | **VIVANT** | cron `50 21 * * 1-5` (README:76) |
| `ftmo_live/reconcile.py` | 1 | **VIVANT** | cron `0 23 * * 1-5` (README:77) |
| `ftmo_live/supervisor.py` | 1 | **VIVANT** | cron reports 08:30/22:20 + daemon `screen` 60s (README:78-84) |
| `ftmo_live/tg.py`, `lib/*.py` (9 fichiers) | 10 | **VIVANT** | importés par brain/supervisor/reconcile, miroir de l'EA (governor, invariants, signals, spec, swaps…) |
| `ftmo_live/watchdog_mt5.sh`, `start_mt5.sh`, `supervisor_keepalive.sh` | 3 | **VIVANT** | `@reboot start_mt5.sh` existant sur VPS (README:58), watchdog cité `_meta/roadmap_ftmo_2026.md:25` |
| `ftmo_live/mt5/book_executor.mq5/.ex5`, `spec_v22.mqh/.sha256` | 4 | **VIVANT** | EA MT5 réellement chargé côté broker, invariants hard-codés miroir de `lib/invariants.py` |
| `ftmo_live/mt5/build_*.log` (7 fichiers) | 7 | **DOCUMENTAIRE** | logs de compilation historiques, aucun consommateur, racontent la chaîne de versions v22→v29 |
| `ftmo_live/monday_restamp.py` | 1 | **VIVANT (probable, non confirmé au cron)** | `MONDAY_RESTAMP_PREREG.md` le décrit comme composant additif figé 2026-06-29 ; **absent du bloc crontab README** — à vérifier directement sur le VPS avant tout archivage (ne pas trancher à l'aveugle) |
| `ftmo_live/tests/` (14 fichiers + conftest) | 15 | **VIVANT** | 145 tests cités README comme garde-fou miroir==oracle, `.pytest_cache` présent (exécutés récemment) |
| `ftmo_live/*.md` incidents (`SEAM_GER40_*`×2, `WATCHDOG_INCIDENT_*`, `OPS_G2_EOD_FIX_*`, `RECONCILE_OPTA_*`, `RUNBOOK_BURNIN_SWING.md`, `MONDAY_RESTAMP_PREREG.md`, `DOC_SIGNAL_PIPELINE.md`) | 8 | **DOCUMENTAIRE** | tous marqués « LECTURE SEULE », « PRÉPARÉ NON DÉPLOYÉ » ou « EN ATTENTE DE GO » dans leur propre en-tête — ce sont des comptes-rendus d'incident/design, pas du code actif |
| `ftmo_live/runtime/cache_live/*.parquet` (135 fichiers, 57 Mo) | — | **À GITIGNORER (déjà fait)** | `runtime/` est dans `ftmo_live/.gitignore` ligne 2 — 0 fichier tracké, RAS |
| `ftmo_live/config/j1_gate.json`, `token_blocklist.sha256` | 2 | **VIVANT** | consommés par `lib/j1_gate.py` et `tg.py` (garde-fou secrets) |
| `strategies/tsmom_v2_propfirm/execution/run_rebalance.py` + `execution/*` | 8 | **VIVANT (gelé)** | entry point Propr documenté dans son propre docstring (cron `5 0 * * 1`) ; **Propr gelé depuis 2026-05-11** (CLAUDE.md) — le code tourne encore en config, la position ne bouge plus |
| `strategies/tsmom_v2_propfirm/signal.py`, `sizing.py`, `config.py` | 3 | **VIVANT (gelé)**, mais **PAS le code réellement cron'd côté HL testnet** | voir finding critique §3 — `run_tsmom.sh` (racine) invoque `tsmom_live.py`, une réimplémentation séparée du signal, pas `strategies/tsmom_v2_propfirm/signal.py` |
| `strategies/tsmom_v2_propfirm/breakout_simulator.py`, `challenge_optimizer.py`, `challenge_simulator.py`, `_breakoutprop_fit.py`, `backtest_v2.py`, `vol_spike_filter.py` | 6 | **DOCUMENTAIRE** | outils de recherche ayant produit la validation gelée (Sharpe 1.33/0.566 excess), non appelés en prod |
| `strategies/delta_neutral/live_trader.py`, `binance_testnet.py`, `hl_perp_client.py`, `universe.py` | 4 | **VIVANT** | `run_delta_neutral.sh` (racine) → `python -m strategies.delta_neutral.live_trader`, cron 8h documenté |
| `strategies/delta_neutral/backtest.py` | 1 | **DOCUMENTAIRE** | backtest ayant produit le Sharpe 4.10 **déclaré CADUC** dans CLAUDE.md — garder pour la trace, jamais reciter |
| `strategies/tsmom_v3/` (3 fichiers) | 3 | **MORT (orphelin de la doc)** | dernier commit 15/05, importé seulement par du code archivé + `Portfolio/integration/load_returns.py` (chargeur générique, pas un import de production) ; **le nom "TSMOM v3" du CLAUDE.md désigne en réalité `tsmom_v2_propfirm` + `tsmom_live.py`** — ce dossier est un vestige de nommage, source de confusion pour un lecteur externe |
| `strategies/trend_futures/` (10 fichiers) | 10 | **MORT (recherche tranchée NO-GO)** | dernier commit 24/08 "verdict NO-GO clean kill" — c'est Strategy D du CLAUDE.md, funnel terminé, code de recherche pas de code live ; mal placé sous `strategies/` (qui devrait être réservé au live) |
| `Portfolio/risk/`, `validation/`, `admission/`, `reporting/`, `state/`, `integration/` | 45 | **VIVANT** | 51 fichiers hors `Portfolio/` l'importent (`grep -rl "from Portfolio"`), dont tout `Multi_Asset/research/active/` récent, `Futures/research/active/`, `PropFirms/`. C'est la bibliothèque la plus réutilisée du dépôt — **à mettre en avant pour un recruteur** |
| `_automation/alpha_hunt/process_raw.py`, `process_raw_filter.py` | 2 | **VIVANT** | seul code Python du dossier, tourne via `scripts/fetch_alpha_sources.sh` (cron `*/30`) |
| `_automation/alpha_hunt/promising/*.md` (554 fiches) | 554 | **QUASI-MORT** | notes MEMORY.md : « largement inexploitables, fiches tronquées » — matière première non retraitée, gonfle le compteur de fichiers sans usage démontré (aucun `grep -rl` ne les référence hors 2 mentions dans des rapports de veille) |
| `_automation/alpha_hunt/_seen/` (33), `_staging/` (50), `runs/` (203), `tested/` (1) | 287 | **VIVANT (état du pipeline)** | anti-churn `_seen.json`, staging avant promotion — nécessaires au fonctionnement, pas du bruit |
| `_automation/alpha_hunt/_raw/` | 0 tracké | déjà gitignoré | patch 2026-06-10 correctement appliqué **en HEAD** — mais voir §3 bloat historique |
| `_automation/arxiv/` (2,6 Mo, structure `_raw`/`_seen`/`_staging`) | — | **VIVANT** | cron `30 6 * * 1-5 fetch_arxiv.sh` (CLAUDE.md, note « silent fail » à vérifier) |
| `_automation/feasibility/` (handlers, stats, digests, runs, weekly, triage) | — | **VIVANT** | pipeline à 3 niveaux documenté, `data/cache/` (288 Ko) trackée par erreur mineure |
| `_automation/synthesis/` | 180 Ko | **VIVANT** | synthèse hebdo citée (`2026-W32.md` référence `tsmom_v2_propfirm`) |
| `_automation/revisits/`, `research_weekly/`, `methodology/`, `code_health/` | 4 dossiers vides ou quasi | **MORT / JAMAIS ACTIVÉ** | 0 octet pour 3 des 4 — infrastructure prévue, jamais peuplée |
| `data/raw/`, `data/metadata/` | — | **VIVANT, conforme gouvernance** | sources immuables + manifest, comme prescrit `_meta/data_governance.md` |
| `data/deep_history_utc/` (8,8 Go), `data/panels/` (3,6 Go), `data/deep_history_m1/` (2,3 Go) | — | **À GITIGNORER — déjà fait pour l'essentiel** | correctement gitignorées et non trackées (933 fichiers trackés / 2 761 total dans `data/`, 32 Mo trackés / 16 Go sur disque) — la règle **tient toujours**, contrairement à la crainte du brief |
| `data/panels/ftmo_{close,open,low,high}.csv` (4,1 Mo trackés) | 4 | **À VÉRIFIER** | trackés malgré un pattern `data/panels/*.csv` en `.gitignore:146` — gitignore n'a pas d'effet rétroactif ; probablement ajoutés avant la règle. Faible enjeu (4 Mo) mais incohérent avec la doc de gouvernance |
| `scripts/*.sh`, `run_with_env.sh` | 5 | **VIVANT** | invoqués par tout le crontab VPS (préfixe systématique) |
| `scripts/inspect_alpha_raw.py`, `cleanup_dedup_2026-06-10.sh` | 2 | **DOCUMENTAIRE** | outils ponctuels de l'audit 2026-06-10, plus appelés en cron |
| `tools/check_register_integrity.py` | 1 | **VIVANT** | check obligatoire de fin de session (CLAUDE.md) |
| `tests/test_dsr.py` (racine) | 1 | **VIVANT** | seul test hors `Portfolio/`, `ftmo_live/`, `strategies/execution/` — bug DSR corrigé 2026-08-04 y est probablement couvert |
| `logs/`, `_downloads_logs/` | 7 | **DOCUMENTAIRE** | logs locaux non trackés en majorité, `_downloads_logs/*.py/.sh` = scripts one-off Dukascopy déjà backfillés (mission close, cf. MEMORY dukascopy_backfill) |
| `_audit/` (44 fichiers) | 44 | **DOCUMENTAIRE (canonique)** | cité 20+ fois dans CLAUDE.md/registre L comme source de vérité (`verification_2026-05-30.md`, `dedup_audit_2026-06-10.md`…) — **ne pas toucher**, c'est la mémoire d'audit citée par le check d'intégrité |

---

## 2. Ce qui tourne réellement (la liste courte pour un recruteur)

1. **`ftmo_live/`** — compte FTMO funded réel : `brain.py` (signal 21:50), `book_executor.mq5/.ex5` (EA MT5), `supervisor.py` (surveillance + alertes Telegram), `reconcile.py` (audit quotidien du Δ sim/live), `lib/` (miroir Python de l'EA), `watchdog_mt5.sh`/`start_mt5.sh`. 145 tests.
2. **`tsmom_live.py`** (racine) + `run_tsmom.sh` — cron HL testnet quotidien de Strategy A (⚠ implémentation séparée de `strategies/tsmom_v2_propfirm/signal.py`, voir finding §3).
3. **`strategies/tsmom_v2_propfirm/execution/run_rebalance.py`** — cron hebdo Propr de Strategy A (gelé depuis 2026-05-11, mais le code tourne toujours en config).
4. **`strategies/delta_neutral/live_trader.py`** + `run_delta_neutral.sh` — cron 8h de Strategy B (HL testnet).
5. **`Portfolio/`** — bibliothèque interne (risk, validation, admission, reporting) importée par >50 fichiers de recherche actifs ; c'est le morceau le plus « ingénierie logicielle » du dépôt.
6. **`_automation/`** (hors `promising/`) — pipeline scraping → filtre → feasibility à 3 niveaux → synthèse, tourne sur crons VPS `*/30` et quotidiens.
7. **`tools/check_register_integrity.py`** — garde-fou CI-like de fin de session.

## 3. Findings critiques (au-delà du tableau)

- **Divergence Strategy A signal-live vs signal-documenté.** `run_tsmom.sh` (racine, cron HL testnet réel) exécute `python tsmom_live.py`, un script autonome avec son propre `VOL_TARGET=0.15` et son propre `vol_scalar` — **il n'importe PAS** `strategies/tsmom_v2_propfirm/signal.py` (qui, lui, documente `VOL_TARGET_LIVE=0.18`, cf. CLAUDE.md). Les deux fichiers de signal existent, divergent sur au moins un paramètre documenté, et rien dans le dépôt n'explique le lien entre eux. **À trancher avant de montrer le dépôt** : soit `tsmom_live.py` doit être refactorisé pour importer le module canonique, soit la doc doit admettre qu'il y a deux implémentations parallèles et dire laquelle fait foi.
- **Bloat `.git` : 293 Mo aujourd'hui contre 65 Mo annoncés après le nettoyage 2026-06-10** (CLAUDE.md). Cause identifiée : **2 037 Mo de blobs uniques** (`_automation/**/_raw/*.xml`, fetch toutes les 30 min, 23-05 → 09-06-2026) sont **toujours dans l'historique** bien qu'absents du HEAD depuis le patch anti-churn du 10/06 — ils représentent **2 052 Mo sur ~2,2 Go de contenu total d'historique** (tous top-levels confondus), soit la quasi-totalité du bloat. Le patch a arrêté le saignement mais n'a jamais purgé l'existant. Une réécriture d'historique (`git filter-repo`) rapatrierait le `.git` vers l'ordre de grandeur de 65-90 Mo — **opération destructive hors périmètre de ce plan, à faire QUE si l'utilisateur confirme** (réécrit tous les hash de commit, casse tout clone existant et le VPS).
- **11 worktrees orphelins, 1,6 Go, gitignorés (donc invisibles à `git status`) mais bien réels sur disque** : `dedale-audit`, `desk-orb`, `desk-overnight`, `funded-numbers`, `fx-carry`, `fx-events`, `fx-libre`, `fx-macro`, `macro-context`, `macro-deepdive`, `regime-diag` — tous créés fin août/début septembre 2026, aucun retiré après merge (violation de la procédure `git worktree remove` du CLAUDE.md). **9/11 sont 100% mergés dans `main`** (`ahead_of_main=0`, suppression sans perte). **2/11 contiennent du travail non mergé** :
  - `claude/macro-context` : 1 commit non mergé, `RAPPORT_MACRO_CONTEXTE.md` (349 lignes, cadre macro ORB/overnight US100-GER40).
  - `claude/macro-deepdive` : 1 commit non mergé, `RAPPORT_MACRO.md` (379 lignes, deep-dive Dedale/Hawkline, verdict IJR chiffré, conclusion « non reconstructible »).
  **Ces deux rapports doivent être rapatriés (cherry-pick ou merge) avant toute suppression de worktree**, sinon perte de travail de recherche déjà écrit.

## 4. Code mort à supprimer (candidats, gain modeste en volume mais fort en lisibilité)

| Cible | Poids | Justification |
|---|---|---|
| `strategies/tsmom_v3/` (3 fichiers) | ~15 Ko | Vestige de nommage : dernier commit 15/05, la doc appelle "TSMOM v3" ce qui vit dans `tsmom_v2_propfirm` + `tsmom_live.py`. Garder seulement si `Portfolio/integration/load_returns.py` en a un besoin fonctionnel réel (à vérifier avant suppression, un seul import trouvé) |
| `strategies/trend_futures/` (10 fichiers) | ~120 Ko | Recherche tranchée NO-GO le 24/08, ne devrait pas vivre sous `strategies/` (réservé au live) — **déplacer** vers `Futures/research/archived/` plutôt que supprimer (contient le verdict, valeur documentaire) |
| `_automation/revisits/`, `research_weekly/`, `methodology/`, `code_health/` | quasi 0 | 3 des 4 dossiers sont à 0 octet — infrastructure jamais activée, aucun coût à retirer, mais gonfle le compteur « 1 314 fichiers » du brief sans rien apporter |
| `scripts/inspect_alpha_raw.py`, `scripts/cleanup_dedup_2026-06-10.sh` | ~10 Ko | Outils ponctuels d'un audit clos, non re-callés — déplacer vers `_audit/` (déjà le dépôt des scripts d'audit ponctuels) plutôt que `scripts/` (qui devrait être réservé aux wrappers cron actifs) |
| **11 worktrees `.worktrees/*`** | **1,6 Go disque (pas .git)** | Après rapatriement des 2 commits non mergés (§3), `git worktree remove` sur les 11 — gain disque immédiat, aucun gain `.git` (déjà gitignorés) |

**Ne PAS toucher sans procédure explicite** : `ftmo_live/*.md` incidents (documentaire, voir §5), `strategies/tsmom_v2_propfirm/*` (gelé mais vivant), `strategies/delta_neutral/backtest.py` (caduc mais cité comme tel — sa suppression casserait la traçabilité de la correction de Sharpe 4.10→caduc).

## 5. Data à sortir de git (gain estimé)

| Cible | Gain estimé | Nature |
|---|---|---|
| **Historique `_automation/**/_raw/*` (2026-05-23 → 2026-06-09)** | **~2 Go de blobs uniques dans `.git`** (pack ≈ 200 Mo compressés, mais l'objectif `.git` 65 Mo post-cleanup ne sera pas retrouvé sans purge d'historique) | XML de scraping, déjà hors HEAD, seulement dans l'historique — **nécessite `git filter-repo` + coordination VPS (force-push + re-clone), PAS une action de ce plan** |
| `data/panels/ftmo_{close,open,low,high}.csv` | 4,1 Mo | Tracké malgré un pattern gitignore existant non-rétroactif — `git rm --cached` + confirmer que c'est bien un cache régénérable avant de couper |
| `_automation/feasibility/data/cache/` (1 fichier) | 288 Ko | Cache tracké par erreur, pattern gitignore manquant pour ce sous-dossier alors que `data/ftmo_portfolio/cache/` l'a |
| `ftmo_live/mt5/build_*.log` (7 fichiers) | quelques dizaines de Ko | Logs de compilation historiques, sans valeur de re-génération ni de décision — candidat à déplacer en documentaire plutôt qu'à garder au niveau racine du dossier live |

**Ce qui est déjà correct et ne demande AUCUNE action** : `data/deep_history_utc/`, `data/panels/` (hors les 4 CSV ci-dessus), `data/deep_history_m1/`, `ftmo_live/runtime/cache_live/` — tous gitignorés, non trackés, malgré 16 Go sur disque. **La règle de gouvernance de données tient toujours** ; le seul re-dérive mesuré est le git-history bloat de `_automation` (source différente : scraping, pas recherche).

## 6. Documentaire à conserver mais à ranger

| Cible | Où le ranger | Pourquoi le garder |
|---|---|---|
| `ftmo_live/SEAM_GER40_INVESTIGATION_2026-06-16.md`, `SEAM_GER40_REALIGN_2026-06-19.md`, `WATCHDOG_INCIDENT_2026-06-15.md`, `OPS_G2_EOD_FIX_2026-07-10.md`, `RECONCILE_OPTA_2026-06-19.md` | `ftmo_live/incidents/` (nouveau sous-dossier) | Post-mortems d'incidents réels sur un compte funded, valeur d'audit et de méthode — mais 5 fichiers `.md` au même niveau que `brain.py` nuisent à la lisibilité pour un recruteur qui cherche le code |
| `ftmo_live/RUNBOOK_BURNIN_SWING.md`, `MONDAY_RESTAMP_PREREG.md`, `DOC_SIGNAL_PIPELINE.md` | `ftmo_live/docs/` (nouveau sous-dossier) | Ce sont des runbooks/pré-registrations, pas des incidents — mérite une séparation logique des 5 fichiers ci-dessus |
| `strategies/tsmom_v2_propfirm/{breakout_simulator,challenge_optimizer,challenge_simulator,_breakoutprop_fit,backtest_v2,vol_spike_filter}.py` | `strategies/tsmom_v2_propfirm/research/` | Ont produit la validation citée (Sharpe 1.33/0.566) mais ne tournent jamais en prod — séparer du code d'exécution (`execution/`, `signal.py`, `sizing.py`) clarifierait immédiatement ce qui est live |
| `strategies/delta_neutral/backtest.py` | inchangé, mais commentaire en tête de fichier renvoyant vers CLAUDE.md §Strategy B (« Sharpe 4.10 CADUC ») | Évite qu'un lecteur externe cite le chiffre caduc en lisant seulement le code |
| `_automation/alpha_hunt/promising/*.md` (554 fiches) | Statu quo ou compaction en un seul index si jamais retraité | Note déjà écrite dans MEMORY.md : « largement inexploitables ». Pas un cas de suppression (perte d'info potentielle si un retraitement futur les vise) mais candidat à ne PAS montrer à un recruteur tel quel — 554 fichiers .md non filtrés donnent une impression de désordre disproportionnée à leur valeur |

---

## Priorisation — par où commencer

1. **Rapatrier les 2 commits non mergés** (`macro-context`, `macro-deepdive`) — 5 minutes, évite une perte de travail de recherche. *Prérequis à tout le reste.*
2. **`git worktree remove` sur les 11 worktrees** une fois (1) fait — 1,6 Go de disque libérés immédiatement, aucun risque (gitignorés, aucun impact `.git`/VPS).
3. **Trancher la divergence `tsmom_live.py` vs `strategies/tsmom_v2_propfirm/signal.py`** — c'est le finding le plus embarrassant pour un audit externe (deux implémentations d'un signal en prod, paramètres différents documentés). Gain : crédibilité, pas de Mo.
4. **Réorganisation documentaire de `ftmo_live/`** (5+3 fichiers `.md` → 2 sous-dossiers) — lisibilité immédiate pour un recruteur qui ouvre ce dossier en premier (c'est le compte réel).
5. **`git rm --cached` sur les 4 CSV `data/panels/ftmo_*`** — 4 Mo, gain mineur mais corrige une incohérence avec la doc de gouvernance citée dans CLAUDE.md.
6. **Déplacer `strategies/trend_futures/`** hors de `strategies/` vers `Futures/research/archived/` — clarifie que `strategies/` = code live uniquement.
7. **Purge d'historique `.git` (2 Go de `_raw/` scraping)** — gain le plus spectaculaire en Mo (293→~90 Mo estimé) mais **opération destructive nécessitant force-push + re-sync du VPS** ; à planifier à part, jamais en même temps qu'un déploiement `ftmo_live/` actif, et seulement après confirmation explicite de l'utilisateur.
