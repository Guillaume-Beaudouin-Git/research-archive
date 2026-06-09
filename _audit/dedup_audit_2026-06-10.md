# Audit doublons & réorganisation — 2026-06-10

**Méthode** : scan complet hors `.git` (10 206 fichiers, ~18 Go avec `.git`) — (1) hash taille+MD5 pour doublons exacts, (2) extraction symbole/fréquence/plage temporelle sur 2 362 CSV/parquet pour détecter les sous-ensembles, (3) grep des références code avant toute proposition de suppression.
**Annexe machine-readable** : `_audit/dedup_audit_2026-06-10_files.csv` · **Script** : `scripts/cleanup_dedup_2026-06-10.sh` (DRY_RUN par défaut, rien n'a été supprimé).

---

## 1. Synthèse

| Pathologie | Volume | Récupérable |
|---|---|---|
| A. Scraper alpha_hunt committe ses XML bruts dans git (2 481 fichiers, des centaines identiques) | 990 Mo + ~1,9 Go de `.git` | 990 Mo (P1) + .git (P3 opt.) |
| B. Données FX M1 : ancien export MT5 (EET) ⊂ nouveau dataset true-UTC | 1,7 Go | 1,7 Go (P2, après migration chemins) |
| C. Caches Dukascopy ×3 emplacements (M1 par année, M5 par année, parquets agrégés) | 2,2 Go + 255 Mo + 86 Mo | 86 Mo (P1) ; 2,2 Go archive externe ; 255 Mo (P2) |
| D. Sprawl programme FTMO juin : 6 emplacements pour 1 programme clos | ~260 Mo | ~40 Mo de caches + consolidation |
| E. Projets éparpillés à la racine (mtf, audit ×3, docs stales, readme legacy) | ~30 Mo | consolidation |
| F. Hygiène (\_\_pycache\_\_ ×74, .DS_Store ×34, *.bak, node_modules) | ~30 Mo | 30 Mo (P0) |

**Total récupérable : ~3,1 Go immédiat (P0+P1), +2,0 Go en P2, +2,2 Go si archive externe du cache Dukascopy M1, +~1,9 Go de `.git` en P3 (optionnel).** Soit 18 Go → ~9-11 Go.

---

## 2. Doublons de données (détail)

### 2.1 CONFIRMÉ — sous-ensembles purs (même série, plage plus courte)

| Fichier redondant | Canonique (superset) | Taille | Action |
|---|---|---|---|
| `data/raw/dukascopy_{EURUSD,GBPUSD}_2020..2024.parquet` (10 fichiers annuels) | `data/raw/dukascopy_*_2020_2024.parquet` (agrégés) | 86 Mo | **Supprimer P1.** Seuls consommateurs : `london_orb_v1` (archivé) |
| `data/raw/yf_AUDUSD=X_1d_*.parquet` et autres `yf_*` daily | `research/ftmo_candidate_funnel/cache/*_daily.parquet` (2007→2026) | ~5 Mo | Supprimer P1 |
| `data/oxfordstrat_109/ohlc/*.parquet` (2018→2025) | mêmes paires dans funnel cache (2007→2026) | ~10 Mo | Conserver tel quel (dossier autonome avec son audit), déplacer le dossier entier — voir §3.9 |
| `research/s076_replication/daily/*_EET.parquet` | `*_UTC.parquet` même dossier (version corrigée tz) | ~4 Mo | Supprimer les `_EET` P1 (gate tz déjà validée) |
| `Futures/research/active/nq_intraday/{engine.py,results.json}.bak_2026-06-07` | git HEAD (version pré-audit committée) | <1 Mo | Commiter la version courante puis supprimer P0 |
| `data/panels/process_raw_filter.py.bak` | version actuelle | <1 Mo | Supprimer P0 |

### 2.2 CONFIRMÉ — ancien panel MT5 ⊂ deep_history_utc (le gros morceau)

`data/panels/m5_indices/*_M1.csv` (14 instruments FX/indices, 2022→2025, **1,7 Go**) est strictement inclus dans `data/deep_history_utc/*_M1.csv` (2007→2026, **schéma identique**, MANIFEST : « existing MT5 range stays authoritative »).

⚠️ **Deux différences sémantiques** qui interdisent un simple `rm` aujourd'hui :
1. **Timezone** : `m5_indices` = EET broker mislabelé UTC ; `deep_history_utc` = vrai UTC. Tout code migré doit retirer son éventuel décalage tz maison.
2. **Références actives** (grep) : `Crypto/research/active/pairs_btceth_D/`, `Crypto/research/active/ftmo_twoSided_makeOrBreak/`, `Forex/research/active/fix_reversal/`, `strategies/tsmom_v2_propfirm/_breakoutprop_fit.py`, `research/ftmo_portfolio_audit/` lisent encore `m5_indices`.

→ **Action P2** : migrer ces 5 consommateurs vers `deep_history_utc` (test de non-régression : re-run d'un backtest de référence, tolérance tz), puis supprimer les `*_M1.csv` FX/indices de `m5_indices`. Les panels dérivés `m1_close.csv` (109 Mo) + `m5_{open,high,low,close}.csv` sont régénérables → même lot.
**Ne pas toucher** : `data/panels/m5_indices/binance/*_M1.csv` (~2,5 Go) — **pas un doublon**, seule copie du M1 crypto, consommée par du code actif. (Option : déplacer vers `data/cache/binance_m1/` pour la clarté.)

### 2.3 Caches Dukascopy — 3 générations au même contenu

| Cache | Contenu | Statut |
|---|---|---|
| `data/deep_history_m1/_cache_duka/` (2,2 Go) | parquets M1 par année/instrument 2007→2026 = **source brute** du build deep_history | Données sources re-téléchargeables mais ~110k requêtes rate-limitées (~jours). **Archiver sur disque externe**, pas supprimer. Aucune référence code hors pipeline de build. |
| `Forex/data/cache/dukascopy_m5/` (255 Mo) | M5 2018→2026, sans spread | Dérivable du M1 (qui a en plus le spread). Consommateurs : uniquement stratégies **archivées** (strategy_e, f2) + programmes juin clos. **Supprimer P2** (ou garder si tu veux re-runner les postmortems à l'identique). |
| `data/raw/dukascopy_*_20XX.parquet` | cf. §2.1 | Supprimer P1 |

### 2.4 NQ — FAUX doublon, à conserver

`data/raw/NQ_1min_2022-12-26_2025-12-11.parquet` (24 Mo, source **Kaggle**, colonnes vwap_rth/vwap_eth) ⊂ plage de `NQ_1min_databento_2010-2026.parquet` (81 Mo, source **Databento officielle**) — mais **sources différentes, valeurs non identiques**. La Strategy C (iter_10, Sharpe 1.52) a été validée sur le fichier Kaggle : c'est sa **provenance**. **Garder les deux** + le `.dbn.zst` brut (103 Mo, source of record). Documenter dans `data/metadata/README.md`. Item de fond : re-valider C sur Databento un jour, puis déprécier le Kaggle.

### 2.5 Doublons exacts (hash MD5)

174 groupes, 47 Mo — dont **~530 fichiers** = pulls RSS identiques dans `_automation/alpha_hunt/_raw/` (le scraper sauvegarde le flux toutes les 30 min même inchangé). Le reste : figures cip_eoq dupliquées active/archived (cf. §3.1). Liste complète en annexe CSV.

### 2.6 `_automation/alpha_hunt/_raw/` — la vraie source du .git de 2 Go

2 481 XML, 990 Mo, **tous trackés git**, commités en continu par la cron VPS. La dédup logique existe déjà (`_seen.json`).
→ **P1** : `git rm -r --cached`, ajouter à `.gitignore`, purger les fichiers >7 jours, patcher le scraper pour ne plus commiter `_raw` (ne committer que `promising/` + `_seen.json`). **P3 optionnel** : `git filter-repo --path _automation/alpha_hunt/_raw --invert-paths` pour dégonfler `.git` 2 Go → ~100 Mo (réécrit l'historique : coordonner avec le VPS et les PR ouvertes avant).

---

## 3. Stratégies / code en double

1. **`Forex/research/active/cip_eoq/` = copie exacte de `archived/cip_eoq/`** (diff : seul `POSTMORTEM.md` manque en active — projet donc CLOS). → `git rm -r` la version active (P1). Corriger CLAUDE.md qui la liste encore en recherche active.
2. **`Futures/research/active/nq_intraday_vwap/`** : verdict écrit « FAIL — INSUFFICIENT SAMPLE (N=19) » → déplacer vers `Futures/research/archived/` (P2). Idem pour `analysis/` D1/D4 marqués ARCHIVED dans CLAUDE.md mais physiquement en active.
3. **`strategy_d/` vs `strategy_d_nq/`** : 1 fichier de pré-registration d'un côté, 4 fichiers d'infra de l'autre — fusionner en `Futures/research/active/strategy_d/{hypotheses_preregistered.md, infra/}` (P2), supprimer `strategy_d_nq`.
4. **Signal TSMOM ×4 implémentations** : `tsmom_live.py` (racine, autonome, live HL), `strategies/tsmom_v3/signal.py`, `strategies/tsmom_v2_propfirm/signal.py` (MD5 différents), copie `_frozen` (intentionnelle, garder). Hard rule CLAUDE.md : « Vol 28-bar MUST match backtest » — 3 implémentations divergentes = risque de drift silencieux. → P3 : une seule source (`strategies/tsmom_v3/signal.py`) importée par le live ; test d'égalité backtest/live dans `tests/`.
5. **Sprawl FTMO juin** (programme **clos** par `research/PROGRAM_DECISION_MEMO.md` : « do-not-fund on free price data ») éparpillé sur 6 racines : `research/` (153 Mo, 14 sous-dossiers), `PropFirms/ftmo*` ×4 nouveaux, `data/ftmo_research/` (96 Mo — de la recherche dans data/ !), `data/ftmo_universe/` (4,4 Mo), `Futures/research/active/ftmo_3strats_audit_2026-06/`, `Crypto/research/active/ftmo_twoSided_makeOrBreak/`. → **Un seul home** : `PropFirms/ftmo/program_2026-06/` (memo à la racine du programme, sous-dossiers = lignes d'enquête). Pruner les caches régénérables des programmes clos (`ftmo_candidate_funnel{,_v2}/cache`, `paper_triage/cache` ≈ 37 Mo). **Exception** : `research/fx_intraday_deepdive/` (modifié hier — c'est la suite ACTIVE de l'axe « sub-60min FX » laissé ouvert par le memo) → le déplacer vers `Forex/research/active/fx_intraday_deepdive/` avec son cache (101 Mo) intact.
6. **Projet mtf éclaté en 3 racines** (`code/mtf/`, `data/mtf_survey/`, `outputs/mtf/`) : étude A1 falsification terminée → regrouper sous `Multi_Asset/research/archived/mtf_a1_tsmom/` (P2), mettre à jour les chemins relatifs dans le rapport md.
7. **3 dossiers d'audit** : `_audit/` (canonique), `audit/` (instrument table juin), `audit-fetch-B/` (manifests commodities) → fusionner les deux derniers dans `_audit/2026-06_instrument_schema/` (P2).
8. **`docs/`** : 7 fiches stratégie d'avril (lettres B/C/D ≠ nomenclature actuelle) → `docs/archive/2026-04/` (P2). **`readme`** (racine, doc crypto legacy) → supprimer ou déplacer dans `docs/archive/` (README.md 138 Ko = canonique).
9. **`data/oxfordstrat_109/`** : dépôt avec son **propre `.git` imbriqué** dans `data/` (+ `index.lock.bak`) → déplacer vers `Multi_Asset/research/archived/oxfordstrat_109_audit/`, retirer le `.git` interne (P2).
10. **`graphify-out/`** : artefact généré (graph.html + cache) → supprimer P1 (régénérable) ou zipper dans `_audit/`.
11. **`Claude Vault/`** : vault Obsidian personnel — rien à faire dans un repo de trading → déplacer hors du repo (P2, manuel).
12. **Racine = déploiement live Strategy A** (`tsmom_live.py`, `monitor.py`, `hyperliquid_client.py`, `notifier.py`, `run_*.sh`, `state_BTC_USD.json`, `challenge_state.db`, `model_store/`, `logs/`) : **NE PAS TOUCHER en P0-P2** — les crons VPS (`5 0 * * *` etc.) pointent sur ces chemins. P3 coordonnée : déplacer vers `strategies/tsmom_v3/live/`, mettre à jour les crons + redeployer, geler `challenge_state.db`+`state_BTC_USD.json` (compte Propr breaché = audit trail) dans `_frozen/`.
13. **Code live non commité** : `Futures/live/orb_floor_ftmo/` (4 fichiers, untracked !) + 5 dossiers PropFirms untracked + `Forex/research/active/fix_reversal/` → décider commit/abandon **avant** toute réorg (P0). Du code live hors git = risque de perte sèche.

---

## 4. Cible d'arborescence & règles de gouvernance données

```
Algo_claude/
├── CLAUDE.md, README.md, STRATEGY_RESEARCH_LOG.md, requirements.txt
├── strategies/            # live crypto (A, B) — y c. leur code d'exécution
├── Futures/live/           # live futures (C, orb_floor_ftmo)
├── <AssetClass>/research/{active,archived}/   # SEULS homes de recherche
├── PropFirms/<firm>/        # rules.md + programmes d'étude par firme
├── Portfolio/  _automation/  scripts/
├── _audit/                  # audits (un seul dossier)
├── _meta/                   # current_focus, open_questions
├── docs/archive/
└── data/
    ├── raw/        # sources immuables + manifest/checksum (dbn.zst, Kaggle NQ, …)
    ├── cache/      # dérivés régénérables, gitignorés, prunables (binance_m1, dukascopy_m5, …)
    ├── deep_history_utc/   # panel M1 canonique (NE PAS dupliquer — référencer)
    └── metadata/
```

Règles (à ajouter dans CLAUDE.md une fois validées) :
- **R1** : une série = un fichier canonique. Les dossiers de recherche **référencent** `data/`, ne copient jamais. Un cache local de recherche doit être sous `<projet>/cache/` gitignoré et meurt avec l'archivage du projet (sauf programme actif).
- **R2** : `data/raw/` = immuable avec manifest ; `data/cache/` = régénérable, supprimable à tout moment sans perte.
- **R3** : jamais de blobs data dans git (le `.git` de 2 Go vient de `alpha_hunt/_raw`).
- **R4** : un subset (plage plus courte) d'une série existante est supprimé dès que ses consommateurs sont migrés — sauf s'il est la **provenance d'une stratégie validée** (cas NQ Kaggle).
- **R5** : `archived/` = avec POSTMORTEM ; rien ne reste en `active/` après verdict FAIL.

---

## 5. Plan d'exécution par phases

| Phase | Contenu | Gain | Risque | Pré-requis |
|---|---|---|---|---|
| **P0** (10 min) | Commit du code live untracked (§3.13) ; hygiène : `__pycache__`, `.DS_Store`, `.pytest_cache`, `*.bak` (après commit engine.py), node_modules `_tool` | ~30 Mo | Nul | git status propre après |
| **P1** (1 h) | §2.1 subsets, §2.5/2.6 alpha_hunt `_raw` (git rm --cached + gitignore + purge + patch scraper), cip_eoq active, graphify-out, `_EET` s076 | ~1,1 Go | Faible | Tag git `pre-cleanup-2026-06-10` |
| **P2** (½ journée) | Consolidation FTMO (§3.5), mtf (§3.6), audits (§3.7), docs/readme (§3.8), oxfordstrat (§3.9), archivage nq_intraday_vwap + D1/D4 (§3.2-3.3) ; migration des 5 consommateurs `m5_indices`→`deep_history_utc` puis suppression des M1 FX dupliqués + panels dérivés ; dukascopy_m5 ; archive externe `_cache_duka` (2,2 Go) | ~4,2 Go | Moyen (tz EET→UTC : test de non-régression obligatoire) | Backtest de référence re-run identique |
| **P3** (session dédiée) | Racine → `strategies/tsmom_v3/live/` + crons VPS ; unification signal TSMOM + test live==backtest ; optionnel `git filter-repo` sur `_raw` (.git 2 Go→~100 Mo, force-push coordonné) | ~1,9 Go .git | Élevé (live) | Fenêtre sans rebalance (éviter lundi 00:05 UTC), backup VPS state.json |

Chaque phase : tag git avant, exécution via le script (DRY_RUN=0), re-run du scan de doublons après, `pytest` sur `strategies/` + `Portfolio/`.

---

## 6. Garde-fous — ce qu'on ne supprime PAS

`data/deep_history_utc/` (canonique) · `data/panels/m5_indices/binance/` (seule copie M1 crypto) · `data/GLBX-*/dbn.zst` + NQ Kaggle parquet (sources/provenance) · `Crypto/research/archived/_frozen/` (copie intentionnelle) · `challenge_state.db`, `state_*.json`, `logs/`, `model_store/` (état live/audit trail — P3 = déplacement, jamais suppression) · `research/fx_intraday_deepdive/` + son cache (programme actif) · tout `Futures/live/`, `strategies/`, `Portfolio/` (hard-fail paths CI) · `.env` (non tracké ✓ — ne jamais commiter).

## 7. Mises à jour CLAUDE.md après exécution

cip_eoq → archived · fx_intraday_deepdive → nouvelle entrée active (Forex) · programme FTMO 2026-06 → entrée « Research history » avec verdict do-not-fund + n_tests à incrémenter (~97 trials du funnel) · règles R1-R5 → section data · repo layout → §4.
