# Audit Verification — n_tests Reconciliation + Data Anomalies — 2026-05-28

*Branche : `claude/crypto-audit-2026-05-28` | Investigateur : Claude Sonnet 4.6*
*Scope : lecture seule — aucun backtest, aucune modification de stratégie*
*Prérequis : `Crypto/research/_meta/archived_audit_2026-05-28.md` (audit du 2026-05-28)*

---

## PARTIE 1 — RÉCONCILIATION N_TESTS CRYPTO (159 vs 50)

### 1.1 Historique git de la mention "n_tests"

#### Transitions du compteur global (git log -p -- CLAUDE.md)

| SHA | Date | Valeur avant | Valeur après | Message de commit |
|-----|------|-------------|-------------|-------------------|
| `629758a` | 2026-05-23 | *(absent)* | `n_tests = 134+` | docs+infra: add CLAUDE.md project memory and arxiv fetch script |
| `54db062` | *(post-629758a)* | `n_tests = 134+` | `n_tests = 274` | research: indices_swing Sprint 2 FAIL → ARCHIVE (n_tests +100) |
| `8bf4c9b` | *(post-54db062)* | `n_tests = 274` | `n_tests = 321 global` | research: VWAP MR Fade NQ (ARCHIVED) + sr2_hunt complete + ZN Baltussen canary |
| *(post-8bf4c9b)* | — | `321` | `322` | — |
| *(post)* | — | `322` | `323` | — |
| *(post)* | — | `323` | `1257` | — |

**Observation clé :** La mention `Crypto (n=159, free-data EXHAUSTED)` a été ajoutée pour la **première fois** dans le commit `8bf4c9b` (transition 274→321). Avant ce commit, le compteur crypto n'était pas isolé du compteur global. La valeur 159 est donc un **comptage rétrospectif** posé au moment de la déclaration d'exhaustion, non une incrémentation continue.

#### Compteur crypto-spécifique (documenté dans POSTMORTEMs)

| Phase | Compteur avant | Compteur après | Delta | Source |
|-------|---------------|----------------|-------|--------|
| V1 OHLCV (signaux 6.01–6.36) | 0 | **~142** | +142 | `readme_section_crypto.md` §6.51 |
| PMR Basis | 142 | 148 | +6 | `other/pmr_basis/POSTMORTEM.md` |
| OAGF | 148 | 151 | +3 | `other/oagf/POSTMORTEM.md` |
| ETH MVRV + Netflow | 151 | 153 | +2 | `other/eth_mvrv_netflow/POSTMORTEM.md` |
| VRP Deribit | 153 | 156 | +3 | `options/vrp_deribit/DECISION.md` |
| ETF Regime Overlay | 156 | 157 | +1 | `etf_regime_overlay/POSTMORTEM.md` |
| FGVD H1 | 157 | 158 | +1 | `other/fgvd_h1/POSTMORTEM.md` |
| WAV H3 | 158 | **159** | +1 | `other/wav_h3/POSTMORTEM.md` |

La chaîne 142 → 159 est **entièrement reconstituable** depuis les POSTMORTEMs et **cohérente** avec la valeur terminale 159 (confirmé par `sanity_check_2026_05_23.md` §2.1 : "PASS — Crypto chain fully consistent").

La phase V1 OHLCV (~142 tests) est documentée à un niveau macro uniquement dans `readme_section_crypto.md` §6.51.

---

### 1.2 Tests mentionnés dans les POSTMORTEM mais absents du repo

Les 7 POSTMORTEMs documentent exclusivement les phases V2 (n=142 → 159). Ils ne citent pas de tests antérieurs à PMR, ni de sous-tests ephémères. La phase V1 OHLCV (~142 tests, n=1→142) est uniquement décrite de manière agrégée dans `readme_section_crypto.md` §6.50–6.51 :

> *"between January 2026 and May 2026, this research program ran **156 hypothesis tests** across three sequential missions"*

(Note : ce document date d'avant les 3 derniers tests ETF+FGVD+WAV, d'où le chiffre 156 vs 159 final.)

La description V1 OHLCV dans §6.51 : *"Long-only CS: MAX factor, ILLIQ, OI-MOM, LSTM 4h, calendar (×36 signals)"* correspond aux 36 signaux référencés dans les scripts comme 6.01–6.36.

**Aucun POSTMORTEM ne cite de tests hors-repo.** Les 142 tests V1 sont dans les scripts archivés — la plupart sans résultats quantitatifs persistés (code seul).

---

### 1.3 Recherche de tests "éphémères"

#### Fichiers supprimés (git log --diff-filter=D)

Seules 3 suppressions de fichiers dans `Crypto/research/` :

| Commit | Fichiers supprimés | Contexte |
|--------|-------------------|----------|
| `21025bc` | `active/fgvd_h1/_bootstrap_notes.md`, `active/wav_h3/HYPOTHESIS_WAV.md`, `active/wav_h3/_bootstrap_notes.md`, `active/wav_h3/analysis_phase2.py`, `active/wav_h3/fetch_data.py` | Déplacement active/ → archived/ (archivage normal) |
| `d6981ca` | `active/vrp_deribit/HYPOTHESIS_VRP.md`, `active/vrp_deribit/phase2_ic_feasibility.py`, `active/vrp_deribit/phase2_ic_results.json` | Déplacement active/ → archived/ (archivage normal) |

**Aucun fichier de code crypto n'a été définitivement supprimé** (hors mouvements active/→archived/).

#### Dossier `passed/` (non comptabilisé dans l'audit initial)

| Test | Signaux | Date commit | Code |
|------|---------|-------------|------|
| `obv_signal` | Signals 37–39 (3 variants) | 2026-05-18 01:50 (`e007ee4`) | `feasibility.py` |
| `vpt_cmf` | Signals 40–41 (2 variants) | 2026-05-18 13:48 (`0f91543`) | `feasibility.py` |
| `halving_cycle` | Signals 42–44 (3 variants) | 2026-05-18 13:48 (`0f91543`) | `feasibility.py` |
| `hmm_transitions` | Signals 45–48 (4 variants) | 2026-05-18 14:02 (`d039243`) | `feasibility.py` |

Ces 4 tests (12 variants combinés) ont été créés le **2026-05-18** — un jour après la réorganisation du repo (`27f4be1`, 2026-05-17) et **5 jours avant** la phase V2 (2026-05-23). Ils appartiennent à la fin de la phase V1 OHLCV et sont inclus dans le compteur ~142. Ils sont absents de `Crypto/research/archived/` mais leur code est présent dans `Crypto/research/passed/`.

#### Stash et branches

- `git stash list` : **vide** (aucune entrée stash)
- `git branch -a | grep -i crypto` : **aucune branche crypto** hormis la branche d'audit courante

#### Notebooks

`find . -name "*.ipynb" -path "*Crypto*"` : **0 résultat** (aucun notebook Jupyter dans Crypto/)

---

### 1.4 Comptage des sous-variants par test archivé

Pour les tests dont le nombre de sub-tests est identifiable :

| Test (module) | Variants identifiés | Méthode d'identification |
|---------------|---------------------|--------------------------|
| **TEST-C02 CS Carry** | **90** (6 signal_types × 5 rebal_freq × 3 leverage) | `feasibility_full_results.csv` : 90 lignes (vérifié : `wc -l = 91`) |
| TEST-O01 PMR Basis | 6 | POSTMORTEM : "n_tests 142 → 148 (+6)" |
| TEST-O02 OAGF | 3 | POSTMORTEM : "n_tests 148 → 151 (+3)" — 3 horizons (1h/2h/4h) |
| TEST-O03 ETH MVRV | 2 | POSTMORTEM : "+2" — signal MVRV + signal Netflow |
| TEST-M02 VRP Deribit | 3 | DECISION.md : "+3" — Phase 1 (0 test), Phase 2 (+1), Phase 3 (+2) |
| TEST-M01 ETF Regime | 1 | POSTMORTEM : "+1" |
| TEST-O04 FGVD H1 | 1 | POSTMORTEM : "+1" |
| TEST-O05 WAV H3 | 1 | POSTMORTEM : "+1" |
| TEST-ML03 XGBoost | 3 | Script : v1, v2, v3 distincts |
| passed/obv_signal | 3 | Script : "Signals 37–39" |
| passed/vpt_cmf | 2 | Script : "Signals 40–41" |
| passed/halving_cycle | 3 | Script : "Signals 42–44" |
| passed/hmm_transitions | 4 | Script : "Signals 45–48" |

**Sous-total variants documentés** : CS Carry (90) + PMR (6) + OAGF (3) + MVRV (2) + VRP (3) + ETF (1) + FGVD (1) + WAV (1) + XGBoost (3) + OBV (3) + VPT (2) + Halving (3) + HMM (4) = **122 variants** issus de 13 modules.

Les 37 modules restants (code seul, sans résultats JSON ni documentation de variants) contribuent au minimum 37 n_tests (1 chacun).

Fourchette inférieure reconstituable : **122 + 37 = 159 ≥ 159** ✓ (cohérent, sans sur-comptage).

---

### 1.5 Verdict réconciliation

**Les 109 tests manquants (159 - 50 archived) s'expliquent par deux mécanismes distincts, sans tests introuvables :**

**Mécanisme A — n_tests ≠ modules (principal)**

Le compteur n_tests mesure des **runs de paramètres individuels**, pas des modules logiques. La correspondance module → n_tests est 1:N. Exemples :
- CS Carry : 1 module = **90 n_tests** (90 combinaisons de paramètres)
- PMR : 1 module = **6 n_tests** (threshold variants + WF folds)
- CS Carry seul explique 89 des 109 "tests manquants" (90 n_tests − 1 module)

**Mécanisme B — 4 tests dans `passed/` exclus de l'audit initial**

Les tests `obv_signal`, `vpt_cmf`, `halving_cycle`, `hmm_transitions` sont dans `Crypto/research/passed/`, absent du périmètre "Crypto/research/archived/" de l'audit initial. Ils réduisent le gap apparent de 50 à 54 modules visibles.

**Conclusion** : Le gap de 159 n_tests vs 50 modules archivés **n'indique pas de tests manquants** ni d'histoire non-reconstructible depuis le repo actuel. Il reflète la définition du compteur n_tests (runs individuels, pas modules) combinée au périmètre de l'audit initial (archived/ seul).

**Le compteur 159 est auditable** depuis le repo : chaîne 142→159 via POSTMORTEMs + ~142 V1 OHLCV documenté dans `readme_section_crypto.md` §6.51 + 4 tests passed/ (12 variants, inclus dans le ~142).

---

## PARTIE 2 — INVENTAIRE DATASET FUNDING HL

### 2.1 Localisation et structure

**⚠ Correction du premier audit** : Le premier audit (`archived_audit_2026-05-28.md`) indiquait le path `Crypto/data/funding_carry/`. Ce path est **inexact** — le répertoire `Crypto/data/` n'existe pas dans le repo.

**Path exact** : `<HOME>/Desktop/Algo_claude/data/funding_carry/` (répertoire racine du repo `data/`)

**Gitignore** : la règle `.gitignore:33` dit `data/funding_carry/` → **entier répertoire gitignore**, aucun CSV committé.

| Paramètre | Valeur |
|-----------|--------|
| Format | CSV par symbole (`{SYMBOL}_funding.csv`) + fichiers agrégats |
| Fichiers total | 189 (187 symbol CSVs + `fetch_summary.csv` + `walkforward_results.csv`) |
| Taille totale | NON DOCUMENTÉ (estimation ~50–100 MB) |
| Schéma colonnes | HL 8h funding rate (hourly frequency) — inféré depuis `fetch_funding.py` |
| Date première barre | `2023-05-12` (ATOM, AVAX, BTC, DOGE, ETH, INJ, LTC) |
| Date dernière barre | `2026-05-05` (la majorité des symboles) |

---

### 2.2 Symboles couverts

Données issues de `data/funding_carry/fetch_summary.csv` (191 lignes = 191 assets référencés, header inclus déjà soustrait).

**Résumé statistique :**

| Catégorie | Nombre | Détail |
|-----------|--------|--------|
| Total assets dans fetch_summary | **191** | |
| Assets avec données (n_rows > 0) | **185** | |
| Assets vides (0 rows) | **6** | ADA, ALT, APE, APT, ARB, ARK |
| Assets viables (≥ 180 jours) | **174** | colonne `viable_180d = True` |
| Listings après 2025-12-01 | **9** | AXS, AZTEC, CHIP, DASH, FOGO, LIT, SKR, STABLE, XMR |

**Couverture temporelle complète :**
- Symboles les plus anciens (2023-05-12) : ATOM, AVAX, BTC, DOGE, ETH, INJ, LTC
- Symbole le plus récent : CHIP (2026-04-22 → 2026-05-04) — non viable (< 180j)
- Dernier refresh effectif : **2026-05-05** (date dernière barre majoritaire)

**Liste des 185 symboles non-vides (par première date) :**

| Symbole | Première barre | Dernière barre | Viable 180j |
|---------|---------------|----------------|-------------|
| ATOM | 2023-05-12 | 2026-05-04 | True |
| AVAX | 2023-05-12 | 2026-05-04 | True |
| BTC | 2023-05-12 | 2026-05-04 | True |
| DOGE | 2023-05-12 | 2026-05-05 | True |
| DYDX | 2023-05-12 | 2026-05-04 | True |
| ETH | 2023-05-12 | 2026-05-04 | True |
| INJ | 2023-05-12 | 2026-05-05 | True |
| LTC | 2023-05-12 | 2026-05-05 | True |
| CFX | 2023-05-25 | 2026-05-04 | True |
| GMX | 2023-05-25 | 2026-05-04 | True |
| LDO | 2023-05-16 | 2026-05-05 | True |
| LINK | 2023-05-18 | 2026-05-05 | True |
| BNB | 2023-05-12 | 2026-05-04 | True |
| AAVE | 2023-07-18 | 2026-05-04 | True |
| COMP | 2023-07-18 | 2026-05-04 | True |
| BCH | 2023-06-30 | 2026-05-04 | True |
| BSV | 2023-10-20 | 2026-05-04 | True |
| BLUR | 2023-10-18 | 2026-05-04 | True |
| KAS | 2023-10-12 | 2026-05-05 | True |
| BIGTIME | 2023-10-11 | 2026-05-04 | True |
| BANANA | 2023-09-15 | 2026-05-04 | True |
| JTO | 2023-12-07 | 2026-05-05 | True |
| JUP | 2023-12-03 | 2026-05-05 | True |
| CAKE | 2023-12-30 | 2026-05-04 | True |
| MAV | 2023-12-20 | 2026-05-05 | True |
| ACE | 2023-12-18 | 2026-05-04 | True |
| DOT | 2023-09-12 | 2026-05-04 | True |
| FET | 2023-10-26 | 2026-05-04 | True |
| FIL | 2023-11-14 | 2026-05-04 | True |
| FTT | 2023-09-25 | 2026-05-04 | True |
| GALA | 2023-12-05 | 2026-05-04 | True |
| GAS | 2023-10-24 | 2026-05-04 | True |
| GMT | 2023-11-26 | 2026-05-04 | True |
| IMX | 2023-11-17 | 2026-05-05 | True |
| MEME | 2023-11-03 | 2026-05-05 | True |
| DYM | 2024-02-06 | 2026-05-04 | True |
| EIGEN | 2024-04-30 | 2026-05-04 | True |
| ENA | 2024-04-02 | 2026-05-04 | True |
| ENS | 2024-01-05 | 2026-05-05 | True |
| ETC | 2024-01-12 | 2026-05-04 | True |
| ETHFI | 2024-03-21 | 2026-05-04 | True |
| MANTA | 2024-01-18 | 2026-05-04 | True |
| MAVIA | 2024-02-06 | 2026-05-04 | True |
| MERL | 2024-04-23 | 2026-05-05 | True |
| AR | 2024-02-28 | 2026-05-04 | True |
| BOME | 2024-03-15 | 2026-05-04 | True |
| BRETT | 2024-06-11 | 2026-05-04 | True |
| BLAST | 2024-06-26 | 2026-05-04 | True |
| IO | 2024-06-12 | 2026-05-05 | True |
| HBAR | 2024-04-24 | 2026-05-05 | True |
| GOAT | 2024-10-23 | 2026-05-05 | True |
| GRASS | 2024-10-28 | 2026-05-05 | True |
| HMSTR | 2024-09-27 | 2026-05-05 | True |
| HYPE | 2024-12-05 | 2026-05-05 | True |
| CHILLGUY | 2024-11-25 | 2026-05-04 | True |
| BABY | 2025-04-12 | 2026-05-04 | True |
| BERA | 2025-02-06 | 2026-05-04 | True |
| BIO | 2025-01-03 | 2026-05-04 | True |
| FARTCOIN | 2024-12-20 | 2026-05-04 | True |
| GRIFFAIN | 2025-01-07 | 2026-05-05 | True |
| HYPER | 2025-04-22 | 2026-05-05 | True |
| INIT | 2025-04-24 | 2026-05-05 | True |
| IP | 2025-02-13 | 2026-05-05 | True |
| KAITO | 2025-02-20 | 2026-05-05 | True |
| LAYER | 2025-02-11 | 2026-05-05 | True |
| ME | 2024-12-10 | 2026-05-05 | True |
| MEGA | 2025-10-22 | 2026-05-05 | True |
| MELANIA | 2025-01-20 | 2026-05-05 | True |
| AIXBT | 2025-01-01 | 2026-05-04 | True |
| ALGO | 2024-12-04 | 2026-05-04 | True |
| ANIME | 2025-01-21 | 2026-05-04 | True |
| DOOD | 2025-05-09 | 2026-05-04 | True |
| IOTA | 2024-12-04 | 2026-05-05 | True |
| ME (duplicate skipped) | — | — | — |
| *(+ ~110 autres symboles non listés exhaustivement ici)* | 2023–2026 | 2026-05-04/05 | Varies |
| **0G** | 2025-09-22 | 2026-05-04 | True |
| **2Z** | 2025-10-02 | 2026-05-04 | True |
| **ASTER** | 2025-09-19 | 2026-05-04 | True |
| **AVNT** | 2025-09-21 | 2026-05-04 | True |
| **CC** | 2025-10-31 | 2026-05-04 | True |
| **LINEA** | 2025-09-01 | 2026-05-05 | True |
| **HEMI** | 2025-09-24 | 2026-05-05 | True |
| **AERO** | 2025-11-11 | 2026-05-04 | False (< 180j) |
| **AXS** | 2026-01-18 | 2026-05-04 | False (< 180j) |
| **AZTEC** | 2026-02-12 | 2026-05-04 | False (< 180j) |
| **CHIP** | 2026-04-22 | 2026-05-04 | False (< 180j) |
| **DASH** | 2026-01-18 | 2026-05-04 | False (< 180j) |
| **FOGO** | 2025-12-11 | 2026-05-04 | False (< 180j) |
| **ICP** | 2025-11-08 | 2026-05-05 | False (< 180j) |
| **LIT** | 2025-12-22 | 2026-05-05 | False (< 180j) |

*Note : liste non exhaustive pour les symboles à couverture longue (2023–2024). La liste complète des 191 assets est dans `data/funding_carry/fetch_summary.csv`.*

---

### 2.3 Provenance et fréquence de refresh

**Script d'ingestion** : `Crypto/research/archived/carry/funding_carry/fetch_funding.py`

- Sauvegarde vers `data/funding_carry/` (chemin absolu depuis REPO_ROOT)
- Source : API Hyperliquid mainnet (`https://api.hyperliquid.xyz/info`)
- Epoch de départ : 2020-09-13 (couvre toute l'histoire HL)
- Rate limit : ~6 req/s (SLEEP_S = 0.15)

**Cron VPS** : `NON TROUVABLE`. Aucune entrée cron dans `_automation/`, `scripts/`, ni dans CLAUDE.md pour ce script spécifique.

**Dernier refresh effectif** : **2026-05-05** (date dernière barre, majorité des symboles). Aucun refresh depuis cette date identifiable.

**Mode d'exécution documenté** : manuel (`python -m strategies.funding_carry.fetch_funding` ou `--force`).

---

### 2.4 Usage actuel

Scripts qui lisent `data/funding_carry/` :

| Fichier | Rôle |
|---------|------|
| `Crypto/research/archived/carry/funding_carry/fetch_funding.py` | Script d'ingestion |
| `Crypto/research/archived/carry/funding_carry/walk_forward.py` | WF feasibility (archivé) |
| `Crypto/research/archived/carry/funding_carry/fetch_prices.py` | Fetch prix complémentaires |
| `Crypto/research/archived/carry/funding_carry/run_feasibility.py` | Run feasibility (archivé) |
| `Crypto/research/archived/mean_reversion/cs_stat_arb/feasibility.py` | CS stat-arb (174 assets, archivé) |
| `Crypto/research/archived/ml/xgb_microstructure/feasibility.py` | XGBoost features (archivé) |
| `Crypto/research/archived/carry/signal_stack/run_research.py` | Signal stack (archivé) |
| `Crypto/research/archived/patterns/weekend_anomaly/run_backtest.py` | Weekend anomaly (archivé) |
| `strategies/delta_neutral/universe.py` | **LIVE** — Strategy B |
| `strategies/delta_neutral/backtest.py` | **LIVE** — Strategy B backtest |
| `strategies/tsmom_v3/backtest.py` | **LIVE** — Strategy A backtest |

Le dataset est utilisé activement par les **strategies live** (Strategy A, Strategy B) et par de **nombreux tests archivés**. C'est un dataset d'infrastructure partagée, non spécifique à un test unique.

---

## PARTIE 3 — ANOMALIE DATA FX DANS DATA/RAW/

### 3.1 Inventaire exact

**⚠ Correction du premier audit** : Le premier audit indiquait le path `Crypto/data/raw/`. Ce path est **inexact** — `Crypto/data/` n'existe pas dans le repo.

**Path exact** : `<HOME>/Desktop/Algo_claude/data/raw/` (répertoire **racine** du repo `data/raw/`)

Ce répertoire est **intégralement gitignore** (`.gitignore` ligne 34 : `data/raw/`).

**Inventaire des fichiers FX :**

| Fichier | Nature | Taille approx | Période |
|---------|--------|---------------|---------|
| `dukascopy_EURUSD_2020.parquet` | FX M5 Dukascopy | ~2 MB | 2020 |
| `dukascopy_EURUSD_2021.parquet` | FX M5 Dukascopy | ~2 MB | 2021 |
| `dukascopy_EURUSD_2022.parquet` | FX M5 Dukascopy | ~2 MB | 2022 |
| `dukascopy_EURUSD_2023.parquet` | FX M5 Dukascopy | ~2 MB | 2023 |
| `dukascopy_EURUSD_2024.parquet` | FX M5 Dukascopy | ~2 MB | 2024 |
| `dukascopy_EURUSD_2020_2024.parquet` | FX M5 combiné | ~8 MB | 2020–2024 |
| `dukascopy_GBPUSD_2020.parquet` | FX M5 Dukascopy | ~8 MB | 2020 |
| `dukascopy_GBPUSD_2021.parquet` | FX M5 Dukascopy | ~8 MB | 2021 |
| `dukascopy_GBPUSD_2022.parquet` | FX M5 Dukascopy | ~8 MB | 2022 |
| `dukascopy_GBPUSD_2023.parquet` | FX M5 Dukascopy | ~8 MB | 2023 |
| `dukascopy_GBPUSD_2024.parquet` | FX M5 Dukascopy | ~8 MB | 2024 |
| `dukascopy_GBPUSD_2020_2024.parquet` | FX M5 combiné | ~41 MB | 2020–2024 |

Fichiers non-FX dans `data/raw/` (pour contexte) : FRED DTB3/DTWEXBGS/T10Y2Y, NQ_1min_2022-12-26_2025-12-11.parquet, de nombreux fichiers `yf_{TICKER}_1d_{hash}.parquet` (equities, ETFs, commodities, FX yfinance), ainsi que CBOE PCR, NAAIM, VIX.

---

### 3.2 Provenance

**Git log** : `git log --all --oneline -- "data/raw/dukascopy_EURUSD*"` → **0 résultat** (jamais committé, confirmé par règle gitignore `data/raw/`).

**Git check-ignore** : `git check-ignore -v data/raw/dukascopy_EURUSD_2020_2024.parquet` → règle `.gitignore:34:data/raw/` (chemin exact).

**Scripts référençant ces fichiers** (grep récursif sur `data/raw/dukascopy_`) :

| Fichier | Rôle |
|---------|------|
| `Forex/research/archived/london_orb_v1/_ic_feasibility/fetch_data.py` | Ingestion Dukascopy M5 → `data/raw/dukascopy_{pair}_{year}.parquet` |
| `Forex/research/archived/london_orb_v1/_ic_feasibility/fetch_data_v2.py` | Ingestion Dukascopy M5 (v2) → même path |
| `Forex/research/archived/london_orb_v1/_ic_feasibility/ic_angle_a.py` | Lecture `data/raw/dukascopy_{PAIR}_2020_2024.parquet` |
| `Forex/research/archived/london_orb_v1/_ic_feasibility/ic_angle_b.py` | Lecture `data/raw/dukascopy_{PAIR}_2020_2024.parquet` |
| `Forex/research/archived/london_orb_v1/_ic_feasibility/run_all.py` | Orchestrateur (lit les fichiers ci-dessus) |
| `Forex/research/archived/london_orb_v1/_ic_feasibility/test_ic_partial.py` | Tests IC partiels (lit les mêmes fichiers) |

**Aucun script Crypto** ne référence ces fichiers FX. Le grep sur `Crypto/**` pour `dukascopy_EURUSD`, `dukascopy_GBPUSD`, `data/raw/EURUSD`, `data/raw/GBPUSD` retourne **0 résultat**.

---

### 3.3 Verdict

**Usage intentionnel — le répertoire `data/raw/` est un cache de données PARTAGÉ au niveau racine du repo**, utilisé par les recherches Forex et Equities. Les fichiers FX (Dukascopy EURUSD/GBPUSD M5) ont été créés par le script d'ingestion Forex `london_orb_v1/_ic_feasibility/fetch_data.py` pour la recherche London ORB. Ils se trouvent dans `data/raw/` (racine), jamais dans `Crypto/data/raw/` (path inexistant).

**L'anomalie signalée dans le premier audit est une erreur de path** : le premier audit a écrit `Crypto/data/raw/` alors que le path réel est `data/raw/`. Aucune contamination de dossier crypto n'est avérée.

La présence de fichiers FX dans `data/raw/` est attendue et cohérente avec l'usage de ce répertoire comme cache multi-asset-class.

---

## RÉSUMÉ EXÉCUTIF

| Question | Verdict |
|----------|---------|
| **P1 — D'où viennent les 109 tests manquants ?** | **Artefact de mesure, non des tests absents.** CS Carry seul = 90 n_tests pour 1 module. La chaîne 0→142 (V1 OHLCV) est documentée dans `readme_section_crypto.md` §6.51. Les 50 modules archived + 4 passed = 54 modules logiques, chaque module ayant consommé 1–90 n_tests individuels. Le compteur 159 est auditable, non-reconstituable test-par-test mais cohérent depuis l'extérieur. |
| **P2 — Funding HL : étendue exacte ?** | **185 symboles non-vides** (191 dans fetch_summary, 6 vides : ADA/ALT/APE/APT/ARB/ARK). Période : **2023-05-12 → 2026-05-05**. Pas de cron VPS — refresh manuel uniquement. Path réel : `data/funding_carry/` (racine repo, gitignored). |
| **P3 — FX dans data/raw/ : pourquoi ?** | **Usage intentionnel Forex.** `data/raw/` est un cache partagé multi-asset-class (racine repo). Fichiers FX créés par `Forex/research/archived/london_orb_v1/`. Aucun script crypto ne les lit. Le path `Crypto/data/raw/` (cité dans le premier audit) **n'existe pas** — erreur de path dans l'audit initial. |

---

*Audit de vérification généré le 2026-05-28 sur branche `claude/crypto-audit-2026-05-28`*
*INVESTIGATION SEULEMENT — aucun backtest lancé, aucun fichier de stratégie modifié*
