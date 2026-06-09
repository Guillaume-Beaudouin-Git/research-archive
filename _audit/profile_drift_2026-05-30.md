# Profile Drift Report — 2026-05-30

**Scope** : audit du bloc constitutionnel `CLAUDE.md` (318 lignes) contre l'état réel
du repo `Algo_claude` au commit `599be41`. Le fichier `README.md` (1724 lignes,
"Algo_claude — Research Journal") est traité comme source secondaire ; ses divergences
avec CLAUDE.md sont listées en Phase 7.

**Hiérarchie appliquée** : code/results.json > CLAUDE.md/README.md > profil.
Toute donnée runtime/externe non dérivable du repo est balisée `[À CONFIRMER MANUELLEMENT]`.

Légende colonnes : `champ profil` | `valeur documentée` | `valeur réelle / source` | `action proposée`.

---

## Phase 1 — Lecture CLAUDE.md / README.md (divergences inter-docs)

| Champ | CLAUDE.md | README.md | Action |
|---|---|---|---|
| n_tests global | 322 (l.199) ET 321 (l.208 commentaire HTML) | 321 (l.4 header) | **Choisir une valeur unique**. Le commentaire interne de CLAUDE.md dit lui-même "321 final" → corriger l'en-tête à 321 (cohérent avec README). |
| Sharpe Strategy A (OOS) | 1.33 (l.31) | 1.13 (l.4 header) ET 1.38 portfolio (§5 tableau l.245) | README header (1.13) est obsolète vs `signal.py:13` qui documente "OOS Sharpe 1.33". Garder 1.33 (CLAUDE.md). |
| Strategy A vol target | VOL_TARGET_LIVE=0.18 (l.32) | 15% vol target (§5 l.231) | `config.py:46` = 0.18 → CLAUDE.md correct, README périmé. |
| Strategy A signal forme | continuous tanh(t_stat) (l.28) | binary +1/−1 (§5 l.226-227) | `signal.py:69` = tanh → CLAUDE.md correct, README pré-C1. |
| Strategy A universe | "BTC, ETH, SOL" (l.30) | "10-asset universe in v2" (§5 l.399) | `config.py:20-35` = 14 tickers (UNIVERSE), mainnet volume filter peut réduire à 3 à l'exécution. Préciser "BTC, ETH, SOL en pratique post-filtre liquidité ; pool de candidats = 14". |
| Strategy A guardrails | MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5% (l.32) | "6% total drawdown … 3% daily" (§4 l.162-164) | `execution/__init__.py:46-47` = 0.028/0.055 → CLAUDE.md correct (valeurs runtime). README documente la limite Propr brute, pas le buffer. |
| Strategy A status | "PAUSED — Propr account breached" (l.27) | "LIVE on Propr testnet" (§6.12 l.397) | CLAUDE.md à jour, README obsolète (Strategy A breached, attendant nouvelle propfirm). |
| Strategy C status | "paper NOT started" (l.45) ; "Tradeify $25K" | "Strategy C Tradeify paper trade in progress" (l.4 header) | `_meta/current_focus.md:8-15` confirme paper non démarré (deux BLOCKERS). CLAUDE.md correct, README header périmé. |
| Strategy B testnet date | "LIVE since 2026-05-17" (l.37) | non daté | Cohérent avec `_meta/current_focus.md:21`. **Pas vérifiable localement** → [À CONFIRMER MANUELLEMENT via logs/delta_neutral.log VPS]. |
| README §8 numéroté deux fois | n/a | "## 8. Key Lessons" l.1242 doublonne "## 8. Multi-Asset TSMOM" l.1151 | Bug de numérotation README (8 → 9 → 8 → 10 → 11). Hors scope CLAUDE.md mais à noter. |

---

## Phase 2 — Walk repo vs `## Repo layout` (CLAUDE.md l.66-77)

### Dossiers documentés mais imprécis / incomplets

| Champ profil | Valeur documentée | Valeur réelle | Action |
|---|---|---|---|
| Live crypto | `strategies/{tsmom_v2_propfirm, delta_neutral}` (l.67) | + `strategies/tsmom_v3/` (signal.py + backtest.py, 4 fichiers, MAJ 16 mai) | Ajouter `tsmom_v3/` (variante de recherche dérivée de v2) OU déplacer hors `strategies/` si non-live. |
| NQ live | `Futures/live/strategy_c_live/` (l.68) | + `Futures/live/strategy_c_paper/` (log_trade.py + paper_trade_log.csv) — déjà flaggé en l.316-317 de CLAUDE.md mais pas dans Repo layout | Mentionner le paper/ dans Repo layout, pas seulement dans la note "Parallel session coordination". |
| Asset classes | `<AssetClass>/research/active/` (l.69) | Classes existantes : Crypto, Futures, Forex, Commodities, Equities, Multi_Asset, ETF_Vol, Options_Vol (8 au total) | Lister explicitement les 8 classes ; ETF_Vol et Options_Vol absents du profil. |

### Dossiers/fichiers présents non documentés dans `## Repo layout`

| Chemin | Type | Action |
|---|---|---|
| `CLAUDE.md.vps` (root) | copie partielle stale de CLAUDE.md (62 l., gitignored cf. `.gitignore:38`) | Documenter comme artefact local OU supprimer. |
| `Claude Vault/` (root) | dossier Obsidian | Documenter ou exclure explicitement. |
| `Dataset_NQ_1min_2022_2025.csv` (72 MB, gitignored cf. `.gitignore:51`) | Mentionné §Data sources (l.191) mais pas Repo layout | OK (signalé ailleurs). |
| `hyperliquid_client.py`, `monitor.py`, `notifier.py`, `dsr.py` (root) | scripts legacy MLP | README §2 les liste comme "deprecated" mais CLAUDE.md silencieux. À mentionner. |
| `graphify-out/` | sortie skill /graphify (gitignored) | OK. |
| `__pycache__/` (root + tous niveaux) | bytecode | OK. |
| `PropFirms/` (apex/, mffu/, phidias/, topstep/, tradeify/) | référencé en l.52 (`PropFirms/tradeify/rules.md`) mais structure complète absente | Ajouter une entrée Repo layout pour `PropFirms/`. |
| `_meta/{current_focus.md, open_questions.md}` | mentionné l.310 (current_focus) mais pas open_questions.md | Ajouter `_meta/open_questions.md`. |
| `_automation/{code_health, methodology, research_weekly, revisits, arxiv (sous-dirs)}` | Profil mentionne alpha_hunt, feasibility, arxiv, synthesis seulement | Ajouter `revisits/` (state existe) et noter `code_health, methodology, research_weekly` comme **EMPTY/PLANNED** (dirs vides confirmés). |
| `Portfolio/{integration, reporting, risk, state, validation}` | l.71 ne mentionne que `Portfolio/state/portfolio_state.py` | Compléter avec `Portfolio/risk/trailing_dd_simulator.py` (déjà cité en l.52) et `Portfolio/validation/`. |
| `data/panels/` (équipement de panels CSV) — 16 nouveaux .csv non-trackés visibles dans `git status` | non documenté | Mentionner `data/panels/` comme cache de panels alpha-hunt. |
| `challenge_state.db` (root, 20 KB, tracké) | non documenté | Documenter (state SQLite Strategy A). |
| `outputs/`, `model_store/`, `logs/` (root) | non documentés | À documenter ou exclure. |

---

## Phase 3 — Vérification stratégies A, B, C

### Strategy A — TSMOM v2/v3 propfirm

| Champ profil | CLAUDE.md | Code réel | Action |
|---|---|---|---|
| Signal | `tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0), long-only` (l.28) | `signal.py:69`: `signal = np.tanh(t_stat).clip(lower=0.0)` avec `t_stat = cum_return / (vol_L + 1e-8)` et `vol_L = std.shift(1) * sqrt(lookback)` | ✓ MATCH |
| Vol formule | "log returns, 28-bar window, sqrt(365) annualization" (l.29) | `signal.py:67`: `std × sqrt(lookback)` — **PAS √365** dans `compute_signal` directement | ⚠ Drift : le `× √365` (annualisation) n'apparaît pas dans `signal.py`. La formule t-stat utilise `× √lookback` (= √28). Vérifier où l'annualisation √365 est appliquée (backtest_v2.py probablement). Préciser "vol intra-fenêtre × √28 pour le t-stat ; annualisation √365 ailleurs". |
| Assets | "BTC, ETH, SOL" (l.30) | `config.py:20-35`: UNIVERSE = 14 tickers (BTC, ETH, SOL, AVAX, LINK, DOGE, ADA, DOT, UNI, LTC, BCH, MATIC, OP, ARB) ; filtre liquidité runtime peut réduire à 3 | Préciser "Pool candidats: 14 ; filtré à BTC/ETH/SOL en pratique (mainnet liquidity)". |
| Rebalance | "Monday 00:05 UTC" (l.30) | `config.py:40`: REBALANCE_WEEKDAY=0 (Monday) ; cron `run_tsmom.sh:6`: `5 0 * * *` (= 00:05 daily) | ⚠ Le script wrapper est `daily`, pas weekly. La logique weekly est portée par `signal.py:97-105` (filtre dayofweek). Cohérent à condition que le cron VPS effectif soit `25 0 * * 1` comme CLAUDE.md l.86. **[À CONFIRMER VIA SSH]**. |
| Sharpe OOS | 1.33 (l.31) | `signal.py:13`: "OOS Sharpe 1.33 vs 1.22" | ✓ MATCH (en commentaire). Le results.json formel n'est pas trouvable pour A : **[INTROUVABLE]** — cherché dans `strategies/tsmom_v2_propfirm/` et `tsmom_v3/`, aucun `results.json`. |
| MaxDD OOS | -6.9% (l.31) | `signal.py:13`: "MaxDD −6.9% vs −12.7%" | ✓ MATCH (en commentaire seulement). |
| WF folds | non précisé pour A | `signal.py:13`: "3/4 WF folds" | Ajouter "WF 3/4" (75%) à la ligne A pour cohérence avec la fiche Strategy C. |
| VOL_TARGET_LIVE | 0.18 (l.32) | `config.py:46`: 0.18 | ✓ MATCH |
| MAX_DAILY_DD | 2.8% (l.32) | `execution/__init__.py:46`: 0.028 ; `equity_monitor.py:34` docstring confirme "Propr limit 3%, buffer 0.2%" | ✓ MATCH **côté execution**. Mais `config.py:55` définit aussi `MAX_DAILY_DRAWDOWN=0.045` (4.5%, HyroTrader/Breakout) — duplication des constantes. Action : harmoniser ou commenter explicitement laquelle est canonique. |
| MAX_TOTAL_DD | 5.5% (l.32) | `execution/__init__.py:47`: 0.055 ; `config.py:56`: MAX_TOTAL_DRAWDOWN=0.09 (9%) | Idem ci-dessus : doublon (Propr vs HyroTrader). |
| Status | "PAUSED — Propr account breached. VPS crons active (state tracking only)" (l.27, l.33) | Non vérifiable localement | **[À CONFIRMER VIA SSH]** : crontab VPS et état réel du compte Propr. |
| Apex alternative | "see PropFirms/comparison.md" (l.35) | `PropFirms/comparison.md` existe ✓ | ✓ MATCH (référence valide). |

### Strategy B — Delta-neutral carry

| Champ profil | CLAUDE.md | Code réel | Action |
|---|---|---|---|
| Active pairs | "TST + MEGA" (l.38) | `data/delta_neutral/live_state/` est VIDE (ls = 0 fichiers) ; `state.json` non trouvé | **[À CONFIRMER VIA LOGS VPS]** — les pairs actuelles ne sont pas dérivables du repo local. |
| Rebalance | "every 8h (00:10, 08:10, 16:10 UTC)" (l.38) | `run_delta_neutral.sh:6`: `10 0,8,16 * * *` ✓ ; docstring `live_trader.py:10` dit "00:10, 08:05, 16:05" — **typo interne** | ✓ MATCH cron. Corriger la docstring `live_trader.py:10` (08:05/16:05 erronés). |
| Backtest Sharpe | 4.10 (l.39) | `Crypto/research/archived/carry/funding_carry/` existe, mais pas de `results.json` ; chiffre **[INTROUVABLE]** dans le repo | Localiser le results.json source ou marquer comme "documenté mais source perdue". |
| MaxDD backtest | -0.52% (l.39) | idem **[INTROUVABLE]** | idem |
| Mainnet proxy Sharpe | 2.0 (l.39, "per L14") | L14 énoncé l.127 cohérent (testnet Sharpe inadmissible, proxy 2.0) | ✓ MATCH (lesson interne). |
| VIABLE_ASSETS | "TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR" (l.40) | `live_trader.py:88`: identique | ✓ MATCH |
| MIN_VOL_USD | 1_000_000 (l.41) | `live_trader.py:79`: 1_000_000 | ✓ MATCH |
| CARRY_FLOOR_8H | 0.0034/(30×3) (l.41) | `live_trader.py:73`: identique | ✓ MATCH |
| NOTIONAL_USD | 50 (l.41) | `live_trader.py:76`: 50.0 | ✓ MATCH |
| Kill switch | "checks STOP file on each run" (l.42) | Fichier `STOP` absent du repo (normal — kill flag) ; `live_trader.py` (lignes non lues) référence STOP_PATH `live_trader.py:90` ✓ | ✓ MATCH (présence du chemin). |
| Status | "EXECUTION-VALIDATED, mainnet pending (~60-day live required, ~2026-07-17)" (l.43) | Non vérifiable localement | **[À CONFIRMER VIA LOGS VPS]** (compteur de jours live testnet). |

### Strategy C — NQ Opening Momentum iter_10

| Champ profil | CLAUDE.md | Code réel | Action |
|---|---|---|---|
| Signal | "direction du 09:30-09:45 ORB, entry at 09:46 ET" (l.46) | `signal_engine.py:115-135`, `config.py:69-71`: ORB_OPEN=09:30, ORB_CLOSE=09:45, ENTRY_TIME=09:46 ✓ | ✓ MATCH |
| VWAP confirmation | "VWAP confirmation" (l.47) | `signal_engine.py:152-158`: filtre BUY→close>VWAP, SELL→close<VWAP ✓ | ✓ MATCH |
| Gap filter | "gap < 1.2%" (l.47) | `config.py:80`: GAP_FILTER=0.012 ✓ | ✓ MATCH |
| Opening range min | "≥ 30 pts" (l.47) | `config.py:81`: RANGE_MIN_PTS=30 ✓ | ✓ MATCH |
| SL cap | "$400 SL cap" (l.47) | `config.py:77`: SL_CAP_USD=400 ✓ | ✓ MATCH |
| TP | "1.5R" (l.48) | `config.py:75`: TP_RATIO=1.5 ✓ | ✓ MATCH |
| SL | "min(0.5R, 20pts)" (l.48) | `config.py:76,78`: SL_RATIO=0.5, SL_CAP_PTS=20.0 ; `signal_engine.py:170`: `sl_pts = min(orb_range * SL_RATIO, SL_CAP_PTS)` ✓ | ✓ MATCH |
| Time stop | "12:30 ET" (l.48) | `config.py:72`: TIME_STOP=12:30 ✓ | ✓ MATCH |
| Backtest Sharpe | 1.52 (l.49) | `nq_intraday/results.json` iter_10 (l.975): `sharpe_daily_hac=1.5212` ✓ | ✓ MATCH |
| MaxDD | -13.4% (l.49) | iter_10 (l.976): `max_dd_pct=-0.1342` ✓ | ✓ MATCH (arrondi). |
| WF | "78% (7/9)" (l.49) | iter_10 (l.984): `wf_pct_extended=77.78`, `wf_n_windows=9` → 7/9 = 77.78% ✓ ; `wf_pct_positive=100` (raw) | ✓ MATCH (extended). Préciser "WF extended 78% (7/9), raw 100% (9/9)". |
| N | 346 (l.49) | iter_10 (l.969): `n_trades=346` ✓ ; `n_tests=142` (ID dans le ledger NQ) | ✓ MATCH si N=nombre de trades. Renommer en "N_trades=346" pour lever l'ambiguïté avec `n_tests`. |
| Sizing | "see Futures/live/strategy_c_live/sizing_policy.md" (l.50) | Fichier existe (3611 bytes, MAJ 25 mai) ✓ | ✓ MATCH |
| Broker | "Tradeify Select Flex $25K via Tradovate REST API" (l.51) | `config.py:5-11,41`: BROKER='tradovate' ; Tradeify Select Flex $25K confirmé | ✓ MATCH (références legacy MT5/IBKR conservées en commentaires). |
| Sizing actuel | "Sizing: risk-managed — see sizing_policy.md" (l.50) | `config.py:58-63,12-17`: PHASE_CONTRACTS = 2/2/2 MNQ (sizing_policy 2026-05-24). CLAUDE.md ne donne pas le nombre exact | Ajouter "2 MNQ toutes phases" pour cohérence avec L22 et `sizing_policy.md`. |
| Tradeify constants | eval_DD=$1,000 funded_DD=$1,000 lock=$26,100 floor=$25,100 (l.53) | `config.py:101-107`: TRADEIFY_TRAILING_DD_USD=1_000, TRADEIFY_TRAILING_DD=1_000, TRADEIFY_LOCK_BALANCE=26_100, TRADEIFY_LOCKED_FLOOR=25_100 ✓ | ✓ MATCH (constantes confirmées 2026-05-25). |
| GUARDRAIL_TRAILING_DD_USD | "see sizing_policy.md and PropFirms/tradeify/rules.md" (l.55) | `config.py:122`: 850 ($150 buffer) ; `rules.md:112` confirme | ✓ référence valide ; ajouter "GUARDRAIL_TRAILING_DD_USD=850" en clair dans CLAUDE.md pour visibilité immédiate. |
| Cron été UTC+2 | "25 13 * * 1-5" (l.54) | `config.py:22-24` docstring: idem ✓ ; **pas de crontab local** (cron VPS) | ✓ MATCH (référence). **[À CONFIRMER VIA SSH]** que la cron est effectivement installée. |
| Cron hiver UTC+1 | "25 14 * * 1-5" (l.54) | `config.py:26` docstring: idem ✓ | ✓ MATCH (référence). |
| KNOWN GAP VWAP | "verify VWAP 1-min granularity in Tradovate client" (l.56) | `_meta/current_focus.md:11-13` confirme BLOCKER 1 ouvert ; `signal_engine.py:32-46` `compute_vwap` agnostique au type de bar (caller doit fournir 1-min) | ✓ MATCH ; gap réel. |
| Status | "BACKTEST-VALIDATED, Tradovate infra built, execution not started" (l.57) | `_meta/current_focus.md:8-15` confirme (Tradovate client built, 2 blockers ouverts) | ✓ MATCH |

### Strategy D — Pre-registration (l.220-225 CLAUDE.md)

| Champ profil | CLAUDE.md | Code réel | Action |
|---|---|---|---|
| Composition | "D3+D5 portfolio" (l.220) | results.json iter_10 fichier contient D1..D5 individuels (l.1175-1257). D3 (ORM-fade) et D5 (BB squeeze) confirmés | ✓ MATCH |
| D3 Sharpe individuel | -1.08 (l.223) | results.json D3 (l.1209): sharpe=-1.0761 ✓ | ✓ MATCH |
| D5 Sharpe individuel | -1.32 (l.223) | results.json D5 (l.1244): sharpe=-1.3171 ✓ | ✓ MATCH |
| D3 corr_C | -0.21 (l.221) | results.json D3 (l.1217): corr_c=-0.2096 ✓ | ✓ MATCH |
| D5 corr_C | -0.05 (l.222) | results.json D5 (l.1252): corr_c=-0.0482 ✓ | ✓ MATCH (-0.048 → -0.05). |
| D3 n_test | 156 (l.221) | results.json D3 (l.1219): n_test=156 ✓ | ✓ MATCH |
| D5 n_test | 158 (l.222) | results.json D5 (l.1254): n_test=158 ✓ | ✓ MATCH |
| Dir Strategy D | "Futures/research/active/nq_intraday/analysis/" (l.225) | Existe ✓ ; mais aussi `Futures/research/active/strategy_d/` (avec `hypotheses_preregistered.md`) ET `Futures/research/active/strategy_d_nq/infra/` (run_manual_signal.sh + plist) | ⚠ **Trois dirs Strategy D** non documentés. Préciser laquelle est canonique pour signaux (`nq_intraday/analysis/`) vs pré-registration (`strategy_d/`) vs infra paper (`strategy_d_nq/infra/`). Voir `_meta/open_questions.md` qui flagge déjà l'infra. |

---

## Phase 4 — Crons & routines

### Crons VPS (CLAUDE.md l.86-87)

| Cron annoncé | Fichier wrapper | Cohérence | Action |
|---|---|---|---|
| TSMOM state `25 0 * * 1` (Monday 00:25) | `run_tsmom.sh:6` annonce `5 0 * * *` (00:05 daily) | ❌ Divergence wrapper/profil. Le wrapper appelle `tsmom_live.py` qui est listé "deprecated" dans README §2 (l.55) | **[À CONFIRMER VIA SSH]** : `crontab -l` sur <VPS_IP>. Si VPS = `25 0 * * 1` → corriger `run_tsmom.sh:6`. |
| Delta-neutral `10 0,8,16 * * *` | `run_delta_neutral.sh:6` annonce idem ✓ | ✓ | **[À CONFIRMER VIA SSH]** présence effective. |
| NQ paper été `25 13 * * 1-5` | `Futures/live/strategy_c_live/config.py:22-24` docstring ✓ | ✓ documentation, **pas de script wrapper** dans le repo | **[À CONFIRMER VIA SSH]** ; créer `run_strategy_c.sh` wrapper. |
| NQ paper hiver `25 14 * * 1-5` | idem `config.py:26` ✓ | ✓ documentation | **[À CONFIRMER VIA SSH]**. |

### CLAUDE.AI / Anthropic cloud routines (CLAUDE.md l.300-307)

| Routine | État réel | Action |
|---|---|---|
| `_automation/alpha_hunt/` | ✓ scraper opérationnel (commits récents `data: alpha hunt raw fetch ...` toutes les 30 min) ; pipeline `_raw/ → _seen.json.migrated → _staging/ → promising/` ✓ ; `promising/` contient 10+ items (arxiv_econ_em_*) | ✓ MATCH |
| `_automation/feasibility/` | ✓ orchestrator.py + 4 handlers (skip_month_handler.py 548 l., generic_handler.py 498 l., regime_filter_handler.py 119 l., exit_rule_handler.py 111 l.) | ✓ MATCH ; mais `current_focus.md:33-35` flagge ExitRule/RegimeFilter comme stubs `REQUIRES_HUMAN` — vérifier. |
| `_automation/arxiv/` | ✓ `2026-05-25_analysis.md` + `2026-05-25.md` ; dernier scan il y a 5 jours | ✓ MATCH ; rafraîchissement quotidien à confirmer. |
| `_automation/synthesis/` | ✓ `2026-W21.md` + state.json ; hebdo cross-paper | ✓ MATCH |
| `_automation/code_health/` | DIR VIDE | ⚠ Non mentionné dans CLAUDE.md. Documenter comme PLANNED ou supprimer. |
| `_automation/methodology/` | DIR VIDE | idem |
| `_automation/research_weekly/` | DIR VIDE | idem |
| `_automation/revisits/` | seul `_state.json` ; pas d'implémentation | idem |

### CI / GitHub workflows

| Workflow | État | Action |
|---|---|---|
| `.github/workflows/auto-merge.yml` | ✓ existe ; squash-merge automatique pour `claude/*` PR ; **garde dure** sur chemins sensibles (`Futures/live/`, `Portfolio/`, `strategies/`, `.github/`, `*.mq5`) + restriction `_automation/`-only | Non mentionné dans CLAUDE.md. **Ajouter section "CI/auto-merge"** pour expliquer le risque et la garde (info critique pour PRs futures). |

---

## Phase 5 — Ledger de recherche (n_tests)

### Compte CLAUDE.md vs dossiers réels

**CLAUDE.md déclare** : "n_tests = 322 global" (l.199) **MAIS** son propre commentaire HTML (l.208) dit "321 final". README l.4 dit "321 signals/variants tested". **Trois valeurs incohérentes au sein des sources d'autorité.**

| Sous-total annoncé | Source CLAUDE.md | Vérification | Action |
|---|---|---|---|
| Crypto n=159 | l.233 | Sous-arbres `Crypto/research/archived/` : carry/ (7 sous-dirs), etf_regime_overlay, mean_reversion (6+ items), ml (3), momentum (15+ scripts), options/vrp_deribit, other (~10 items), patterns (6 items), regime (3), sentiment (3) — total >50 *items* mais chaque item ≠ 1 n_test (un dossier = plusieurs tests). Non recomptable mécaniquement. | Pas de drift quantifiable. Conserver 159 comme documenté ; ajouter pointer vers un fichier `ledger.csv` (manquant) pour traçabilité. |
| FX n=181 | l.242 | Forex archived a 11 sous-dirs (cip_eoq, fx_carry_em, fx_carry_fred, fx_momentum_monthly, g1_carry_conditional, london_orb_v1, round_number_cascade, strategy_d_modified_carry, strategy_d_modified_carry_v2, strategy_e_fix_flow, strategy_f2_asian_breakout) ; nombre de tests par dir non-extractible sans parse exhaustif | Idem ; FX = 181 plausible. |
| Equities/ETF n=83 | implicite (commentaire l.211) | Equities archived : 5 sous-dirs (indices_swing, multi_asset_tsmom, pairs_cointegration, pairs_distance_gatev, sector_reversal_cs) ; ETF_Vol archived : vix_term_carry ; Options_Vol : vrp_spx_angle_c ; Futures archived : orb_ivb_nq | Plausible. |

### Liste ARCHIVED — entrées présentes mais sans dossier OU dossier sans entrée

| Entrée CLAUDE.md | Dossier réel | Cohérence |
|---|---|---|
| Crypto: PMR basis (L12) | `Crypto/research/archived/other/pmr_basis/` ✓ | ✓ |
| Crypto: OAGF | `Crypto/research/archived/other/oagf/` ✓ | ✓ |
| Crypto: CS-FS | non trouvé | **[INTROUVABLE]** : cherché dans `Crypto/research/archived/{carry,other}/`. **MAIS** `Crypto/research/active/h31_cs_fs_dn/` existe — peut-être l'objet est encore en cours. À clarifier. |
| Crypto: FRA | non trouvé | **[INTROUVABLE]** ; recherche dans archives crypto sans résultat. |
| Crypto: MVRV | `Crypto/research/archived/sentiment/mvrv/` ✓ + `Crypto/research/archived/other/eth_mvrv_netflow/` ✓ | ✓ |
| Crypto: ETH netflow (L12b) | `Crypto/research/archived/other/eth_mvrv_netflow/` ✓ | ✓ |
| Crypto: VRP Deribit (L13) | `Crypto/research/archived/options/vrp_deribit/` ✓ | ✓ MAIS `Crypto/research/active/vrp_short_gamma/` existe aussi (variante short gamma) — pas mentionné dans active du profil. |
| Crypto: FGVD H1 (L17) | `Crypto/research/archived/other/fgvd_h1/` ✓ | ✓ |
| Crypto: Wikipedia attention (L18) | non trouvé | **[INTROUVABLE]** : pas de dossier `wikipedia_*` ou `attention_*` dans Crypto/research/archived. |
| Crypto: etf_regime_overlay | `Crypto/research/archived/etf_regime_overlay/` ✓ | ✓ pas mentionné explicitement dans la liste ARCHIVED (sub-sumé par "Macro overlay"?). |
| FX: London ORB v1 | `Forex/research/archived/london_orb_v1/` ✓ | ✓ |
| FX: Round Number Cascade | `Forex/research/archived/round_number_cascade/` ✓ | ✓ |
| FX: Strategy E (E1/E2) | `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md` ✓ | ✓ |
| FX: G1 (Koijen pivot) | `Forex/research/archived/g1_carry_conditional/POSTMORTEM.md` ✓ | ✓ |
| FX: Strategy F2 Asian Breakout | `Forex/research/archived/strategy_f2_asian_breakout/POSTMORTEM.md` ✓ **ET** `Forex/research/active/strategy_f2_asian_breakout/` (data_setup.py, feasibility.py, results.json sans POSTMORTEM) | ⚠ **DUPLICATION** : dir existe à la fois en archived/ et active/. Supprimer la copie active/. |
| Equities/Futures: D1 (ORB fade) | non trouvé en archived | **[INTROUVABLE]** comme dossier dédié ; D1-D5 vivent dans `Futures/research/active/nq_intraday/results.json`. CLAUDE.md "ARCHIVED" en prose mais pas en arbre. À déplacer ou à clarifier que "ARCHIVED" est logique (verdict), pas physique. |
| Equities: indices_swing Sprint 1+2 | `Equities/research/archived/indices_swing/` ✓ | ✓ |
| Equities: pairs cointegration | `Equities/research/archived/pairs_cointegration/` ✓ | ✓ |
| Equities: Gatev distance | `Equities/research/archived/pairs_distance_gatev/` ✓ | ✓ |
| Equities: sector reversal | `Equities/research/archived/sector_reversal_cs/` ✓ | ✓ |
| Equities: Multi-asset TSMOM | `Equities/research/archived/multi_asset_tsmom/results.json` ✓ | ✓ |
| ETF_Vol: VIX term carry | `ETF_Vol/research/archived/vix_term_carry/` ✓ | ✓ (path non mentionné dans profil) |
| Commodity TSMOM ETF | `Commodities/research/archived/commodity_tsmom/` ✓ | ✓ |
| NQ ORB IVB | `Futures/research/archived/orb_ivb_nq/` ✓ | ✓ |
| NQ Pairs ES/NQ | non trouvé en archived | **[INTROUVABLE]** comme dossier ; vit dans `nq_intraday/results.json` iter_D_pairs_es_nq (l.1162). Idem D1-D5. |
| Network Momentum GMOM | `Multi_Asset/research/active/network_momentum/` (PAS archived!) | ⚠ **DRIFT** : CLAUDE.md liste comme ARCHIVED, dossier est en active/. Déplacer le dossier ou requalifier le statut. |
| Options: SPX VRP Angle C | `Options_Vol/research/archived/vrp_spx_angle_c/` ✓ | ✓ |

### Dossiers ACTIVE présents mais absents de "## Active research" (CLAUDE.md l.219-229)

| Dossier | Première trace | Action |
|---|---|---|
| `Crypto/research/active/h31_cs_fs_dn/` | branche `claude/h31-cs-fs-dn-test-160`, **non-tracké** dans git status | Ajouter "Crypto H31 — CS-FS-DN (n_test=160)" comme actif si effectivement en cours. |
| `Crypto/research/active/token_unlocks/` | _bootstrap_notes.md seulement | CLAUDE.md liste "Token unlock cliff shorts" comme "Untested" (l.295). Si dossier = simple staging, OK ; sinon promouvoir à "Active". |
| `Crypto/research/active/vrp_short_gamma/` | _bootstrap_vrp_notes.md | Distinct du VRP Deribit archivé (long carry). Ajouter à "Active" ou expliquer le statut. |
| `Equities/research/active/sector_hothand_propfirm/` | data_audit.py, engine.py, phase1_baseline.py, phase1_2_mc.py, results/ | **DRIFT MAJEUR** : recherche substantielle (branches `claude/sector-hothand-phase*`) **non mentionnée** dans CLAUDE.md. À ajouter aux active. |
| `Forex/research/active/cip_eoq/` | sigma_estimation/ | Pas mentionné. À documenter. |
| `Forex/research/active/strategy_f2_asian_breakout/` | duplicate (voir Phase 5 plus haut) | **À SUPPRIMER** (déjà archivé). |
| `Futures/research/active/voie_b_ftmo/` | full study commit `16eb3be` ; mq5 EA, slip_analysis, weekly_realtape, reconciliation.md | **DRIFT MAJEUR** : Strategy A → FTMO pivot, **non mentionné** dans CLAUDE.md mais flaggé en `current_focus.md:42` (FTMO challenge analysis #1 priority). À promouvoir en "Active research". |
| `Futures/research/active/zn_baltussen/` | tests/, sigma_estimation | Pas mentionné. À documenter (likely "Baltussen ZN momentum"). |
| `Futures/research/active/strategy_d/` | hypotheses_preregistered.md | Doublon de `nq_intraday/analysis/` ? Clarifier. |
| `Futures/research/active/strategy_d_nq/infra/` | manual_signal.sh + plist (cf. `_meta/open_questions.md`) | Statut "trancher" déjà ouvert. À résoudre. |
| `Futures/research/active/nq_intraday_vwap/` | dir séparé de nq_intraday | Non documenté. À clarifier. |

### Dossiers "passed" — incohérence avec verdicts

| Dossier | Verdict réel (results.json) | Action |
|---|---|---|
| `Equities/research/passed/jt_momentum_cs/results.json` | sharpe=-0.026, max_dd=-0.58, ic_tstat=-0.49 — **FAILED** | Dossier mal classé. Déplacer vers `archived/`. |
| `Forex/research/passed/fx_carry_trend/results.json` | sharpe_hac=-0.15, max_dd=-0.53, amtp_p=0.89 — **FAILED** | Idem ; CLAUDE.md liste correctement FX carry comme ARCHIVED. Déplacer le dossier. |

---

## Phase 6 — Sécurité

| Élément | État réel | Risque | Action |
|---|---|---|---|
| `.env` (root) | présent (164 bytes, 5 lignes, tracké NON via `.gitignore:2`) | Contient des credentials runtime | **NE PAS afficher contenu** ✓. Verified gitignored. |
| `.env` keys présentes (noms seulement) | MT5_SERVER, MT5_LOGIN, MT5_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (5 keys) | 5 secrets = correspond à la note "5 secrets compromis, regen pending" mentionnée dans la mission. **[À CONFIRMER MANUELLEMENT]** que ce sont bien les 5 visés et que la rotation est effectuée. | Vérifier état de rotation (MT5 trio + Telegram pair). |
| `.env.example` | présent, tracké, contient `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `HYPERLIQUID_PRIVATE_KEY` (3 templates) | OK | **DRIFT** : `.env.example` ne référence ni `MT5_*`, ni `PROPR_API_KEY`, ni `BINANCE_API_*` (mentionnés dans README §3 l.154) ni `TRADOVATE_*` (référencés dans `Futures/live/strategy_c_live/config.py:44-51`). Synchroniser `.env.example` avec les variables réellement consommées. |
| `.gitignore` | `.env`, `.env.local`, `model_store/`, `logs/`, `data/raw/`, etc. ✓ ; **ignore aussi `CLAUDE.md.vps`** (l.38) | OK | Bon. |
| Historique git | Aucune commit récente ne semble inclure un secret (vérifié par `git log --oneline -30`) | OK probable | Vérification exhaustive : `git log -p -S "BEGIN PRIVATE KEY" -- :^.env.example` recommandé. Non exécuté ici par prudence. |
| Workflow CI | `auto-merge.yml` lit `secrets.TELEGRAM_BOT_TOKEN` / `secrets.TELEGRAM_CHAT_ID` — secrets GitHub Actions, OK | OK | Pas de fuite. |
| Crontab VPS | Non vérifiable localement | Si rotation faite mais cron VPS pointe vers anciens .env → live cron en échec silencieux | **[À CONFIRMER VIA SSH]** : `cat ~/.env` ou variables exportées dans crontab. |

---

## Phase 7 — Cohérence interne du profil

### Contradictions intra-CLAUDE.md

| Contradiction | Lignes | Action |
|---|---|---|
| Strategy A "PAUSED" mais ligne `## Profil` mentionne "Propr/Tradovate API" comme stack en cours | l.6 vs l.27 | Reformuler `## Profil` : "Propr (historique, paused) / Tradovate (paper Strategy C)". |
| Strategy C status "execution not started" mais `## Portfolio context` parle de "A+B+C theoretical: Sharpe 2.24" comme si C contribuait | l.57 vs l.62 | Garder ; "theoretical" est explicite. OK mais à souligner. |
| `## Repo layout` ne mentionne pas FX/Equities/Options/ETF_Vol comme classes vivantes alors que toute la section ARCHIVED s'y réfère | l.66-77 vs l.242-282 | Compléter Repo layout avec les 8 classes. |
| n_tests = 322 vs commentaire HTML "321 final" vs README "321" | l.199 vs l.208 | **À TRANCHER** : 321 ou 322. |
| L11b dit "First case identified: F2 Asian Range Breakout archived 2026-05-26" — F2 est dans `Forex/research/active/` ET `Forex/research/archived/` | l.120 vs Phase 5 | Supprimer le dossier active/. |
| `## Active research` cite Strategy D (Futures) et Commodities XS uniquement — ignore voie_b_ftmo, sector_hothand_propfirm, h31_cs_fs_dn, vrp_short_gamma, zn_baltussen, cip_eoq | l.219-229 | Réécrire en couvrant tous les actifs réels. |
| `## Active research` Strategy D path = `nq_intraday/analysis/` ; mais `_meta/open_questions.md` doute du placement de l'infra | l.225 vs open_questions.md:1-26 | Résoudre la question d'infra avant de figer le path. |
| L22(c) dit "FTMO does not support CME futures" ; mais `current_focus.md` axe #1 = "FTMO challenge analysis (Strat A)" — Strat A est crypto, pas futures → cohérent | OK | Mais `Futures/research/active/voie_b_ftmo/` contient `Voie_B_EA_fixed.mq5` (MT5 = donc FTMO MT5 sur quel sous-jacent ?). Clarifier le sous-jacent ciblé. |
| `## VPS` cron "TSMOM state (25 0 * * 1)" — Monday only, weekly ; mais `run_tsmom.sh:6` annonce daily | l.86 vs script | Aligner script et CLAUDE.md (et VPS réel — [À CONFIRMER]). |
| `## Code style` "No matplotlib in core logic" — mais `strategies/tsmom_v2_propfirm/` contient de gros .png générés et probable code matplotlib (à vérifier dans backtest_v2.py) | l.91 vs .png présents | Vérifier matplotlib séparé du core logic. (mineur) |

### Divergences CLAUDE.md ↔ CLAUDE.md.vps

| Champ | CLAUDE.md | CLAUDE.md.vps | Action |
|---|---|---|---|
| Strategy A status | "PAUSED" | "LIVE on Propr" | CLAUDE.md.vps est stale (gitignored, jamais re-poussé). Supprimer ou regenerer. |
| Costs futures | "~$2.15 RT" | "~0.01%" | idem stale. |
| Lessons | L11–L23 inclus | seulement 1–10 | idem stale. |
| Portfolio context | inclus | absent | idem stale. |

---

## Synthèse

**Drifts critiques** (impact opérationnel direct) :
1. `run_tsmom.sh` daily vs CLAUDE.md weekly Monday → risque de double-déclenchement
2. F2 Asian Breakout dupliqué active/+archived/ → confusion statut
3. Network Momentum GMOM listé archived mais physiquement en active/
4. Passed/ contient deux strats failed (fx_carry_trend, jt_momentum_cs) → mal classés
5. .env.example désynchronisé vs variables réellement consommées (Tradovate, MT5)
6. Trois dirs Strategy D concurrentes sans canonical

**Drifts documentaires** (impact futur de session) :
7. n_tests 321 vs 322 contradictoire dans CLAUDE.md même
8. 7+ dirs research/active non documentés dans `## Active research`
9. `## Repo layout` muet sur 8 asset classes existantes
10. CI auto-merge non documenté → risque de PR auto-mergée par erreur

**À CONFIRMER MANUELLEMENT (runtime/externe)** :
- État réel des crons VPS (`crontab -l` sur <VPS_IP>)
- Pairs Strategy B actives (logs VPS `delta_neutral.log`)
- Date "live since 2026-05-17" pour B (compteur jours testnet)
- Statut "5 secrets compromis, regen pending" — les 5 dans `.env` correspondent (MT5×3 + Telegram×2), confirmer rotation
- Sous-jacent de `voie_b_ftmo` (FX ? indices ?)
- Variables `TRADOVATE_*` source de stockage (pas dans `.env` local)
