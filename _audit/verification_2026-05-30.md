# Verification Report — 2026-05-30

**Scope** : vérifier chaque conclusion du `profile_drift_2026-05-30.md` contre la
réalité du repo + VPS (SSH disponible). Lecture seule. Aucune écriture, aucun commit.

**SSH status** : ✓ disponible (`algo@<VPS_IP>`, hostname `algo-claude-prod`,
date VPS `Sat May 30 11:15:36 AM UTC 2026`).

**Redaction sécurité** : ce rapport NE PRINT AUCUNE valeur de secret, **même partielle**.
Quand une preuve provient de la crontab ou d'un log contenant des valeurs en clair,
je cite la ligne / le fichier mais redacte les valeurs (`<REDACTED:KIND>`).

Verdicts : **[CONFIRMÉ]** / **[INFIRMÉ]** / **[PARTIEL]** / **[NON-RÉSOLU]**.

---

## V1. `run_tsmom.sh` — placement d'ordres vs state-tracking

| Item | Verdict | Preuve | Action recommandée |
|---|---|---|---|
| Le wrapper `run_tsmom.sh` exécute `tsmom_live.py` | **[CONFIRMÉ]** | `run_tsmom.sh:13` : `python tsmom_live.py "$@"` | — |
| `tsmom_live.py` PLACE des ordres (n'est pas state-only) | **[CONFIRMÉ]** | `tsmom_live.py:6` "Rebalance: daily at 00:05 UTC — signal from T-1 close, order at T open" ; `tsmom_live.py:299` "elif action != 'HOLD'" + branches CLOSE l.324 et OPEN. Logs VPS `~/logs/tsmom.log` montrent fills réels (cf. `~/projects/Algo_claude/logs/fills.csv` last lines : `2026-05-28 SOL-USD sell 0.670` etc.) | — |
| Deux jobs distincts à `5 0 * * 1` (Monday 00:05 collision) | **[CONFIRMÉ — collision réelle]** | VPS `crontab -l` ligne 1 : `5 0 * * * /home/algo/run_tsmom.sh --live …` (daily, HL TESTNET, calls tsmom_live.py) ; VPS `crontab -l` ligne 3 : `5 0 * * 1 cd ~/projects/Algo_claude && … python -m strategies.tsmom_v2_propfirm.execution.run_rebalance …` (Monday only, **Propr LIVE** : `PROPR_API_KEY=pk_live_<REDACTED>`). Les deux démarrent à la même minute le lundi. | **CRITIQUE** : risque de contention de ressources / double-lecture state. Décaler le job Monday Propr (ex. `15 0 * * 1`) OU consolider les deux pipelines. Vérifier que les `tsmom_state_*.json` ne sont pas écrits par les deux jobs. |
| CLAUDE.md:86 dit "TSMOM state (25 0 * * 1)" | **[INFIRMÉ]** | Réel sur VPS : daily `5 0 * * *` (tsmom_live.py, HL testnet, places fills) **+** weekly `5 0 * * 1` (run_rebalance, Propr live). Aucune cron "25 0" trouvée. CLAUDE.md a la **mauvaise minute** ET sous-représente le système (omet le job daily). | Réécrire la ligne `## VPS` de CLAUDE.md avec les deux jobs réels. |
| "VPS crons active (state tracking only)" (CLAUDE.md:33) | **[INFIRMÉ — PARTIELLEMENT]** | Le daily HL testnet PLACE encore des fills (cf. `tsmom_trades.csv` ligne du 2026-05-30, `fills.csv` 2026-05-28 SOL sell). Le Monday Propr est gelé depuis `2026-05-11 16:44` (dernière ligne de `tsmom_v2_cron.log`, file size 15012 bytes inchangé). La phrase "state tracking only" est trompeuse : seul Propr est effectivement gelé ; le testnet trade. | Reformuler en : "Propr live cron configuré mais sans exécution depuis 2026-05-11 ; HL testnet daily continue de placer des fills." |

---

## V2. Crontab VPS réelle (lecture brute redactée)

Source : `ssh algo@<VPS_IP> 'crontab -l'` (intégrale relue, secrets redactés).

| # | Cron line (redactée) | Présent dans CLAUDE.md ? | Verdict |
|---|---|---|---|
| 1 | `5 0 * * * /home/algo/run_tsmom.sh --live --private-key <REDACTED:HL_PRIVKEY> >> /home/algo/logs/tsmom.log 2>&1` | NON | **[INFIRMÉ – absent]** + **secret en clair** dans crontab |
| 2 | `30 0 * * * /home/algo/run_monitor.sh >> /home/algo/logs/monitor.log 2>&1` | NON | **[INFIRMÉ – absent]** |
| 3 | `5 0 * * 1 cd ~/projects/Algo_claude && source ~/venv/bin/activate && PROPR_API_KEY=<REDACTED:PROPR_LIVE> python -m strategies.tsmom_v2_propfirm.execution.run_rebalance >> logs/tsmom_v2_cron.log 2>&1` | OUI mais **minute incorrecte** (CLAUDE.md dit `25`, réel `5`) | **[INFIRMÉ – mauvaise minute]** + **secret en clair** |
| 4 | `30 8 * * * cd ~/projects/Algo_claude && … PROPR_API_KEY=<REDACTED> TELEGRAM_BOT_TOKEN=<REDACTED> TELEGRAM_CHAT_ID=<REDACTED> python -m strategies.tsmom_v2_propfirm.execution.daily_summary …` | NON | **[INFIRMÉ – absent]** + **3 secrets en clair** |
| 5 | `10 0,8,16 * * * cd ~/projects/Algo_claude && /bin/bash -c 'source ~/venv/bin/activate && source .env && /home/algo/run_delta_neutral.sh --live --bn-key $BINANCE_TESTNET_API_KEY --bn-secret $BINANCE_TESTNET_SECRET_KEY --hl-key $HYPERLIQUID_TESTNET_KEY' >> ~/logs/delta_neutral.log 2>&1` | OUI (`10 0,8,16 * * *`) | **[CONFIRMÉ]** ; secrets passés via `.env` source — propre. |
| 6 | `*/2 13-17 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh >> /tmp/watchdog_check.log 2>&1` | NON | **[INFIRMÉ – absent]** ; logs `/tmp/watchdog_check.log` montrent "WATCHDOG: Telegram not configured" en boucle |
| 7 | `*/2 13-17 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/Futures/live/strategy_c_live/watchdog_check.sh` | NON | **[INFIRMÉ – DOUBLON]** : ligne 6 répétée sans redirection. Bug : deux watchdogs simultanés. |
| 8 | `30 6 * * 1-5 /bin/bash /home/algo/projects/Algo_claude/scripts/fetch_arxiv.sh` | NON | **[INFIRMÉ – absent]** |
| 9 | `*/30 * * * * /bin/bash /home/algo/projects/Algo_claude/scripts/fetch_alpha_sources.sh` | NON | **[INFIRMÉ – absent]** ; cohérent avec commits "alpha hunt raw fetch" toutes les 30 min |
| 10 | `@reboot sleep 30 && /usr/bin/screen -dmS mt5 /home/algo/start_mt5.sh` | NON | **[INFIRMÉ – absent]** |
| **MANQUANT** | **AUCUNE cron `25 13 * * 1-5` OU `25 14 * * 1-5` pour Strategy C NQ paper** | OUI dans CLAUDE.md:87 | **[INFIRMÉ – inexistant]** : la "NQ paper" annoncée par CLAUDE.md **n'existe pas dans crontab**. Seul `watchdog_check.sh` tourne dans la fenêtre 13-17 UTC. Le trading C n'est PAS automatisé. |
| **MANQUANT** | aucune cron Tradovate/MT5 NQ trading | — | Cohérent avec CLAUDE.md:57 "execution not started" pour Strategy C |

**Synthèse V2** : sur 10 crons réelles, **2 confirmées** (5 = delta-neutral, 3 partiellement = run_rebalance mais minute fausse), **8 absentes de CLAUDE.md** dont une ligne dupliquée et plusieurs contenant des secrets en clair.

---

## V3. `passed/` — verdict réel des stratégies

Recensé tous les dirs `*/research/passed/` (8 asset classes inspectées).

| Dossier | Verdict réel (results.json / metrics) | RESEARCH_PASS gates ? | Verdict audit |
|---|---|---|---|
| `Crypto/research/passed/halving_cycle/` | Pas de `results.json` (uniquement feasibility.py + .png) | **[INDÉTERMINÉ]** | **[NON-RÉSOLU]** — manque metrics export |
| `Crypto/research/passed/hmm_transitions/` | Idem ci-dessus | **[INDÉTERMINÉ]** | **[NON-RÉSOLU]** |
| `Crypto/research/passed/obv_signal/` | Idem | **[INDÉTERMINÉ]** | **[NON-RÉSOLU]** |
| `Crypto/research/passed/tsmom_v3/` | **DIR VIDE** (`ls -la` confirme) | n/a | **[NON-RÉSOLU]** — dossier squelette ; les vrais artefacts tsmom_v3 vivent dans `strategies/tsmom_v3/` (signal.py, backtest.py, .png). Probable convention de réservation de slot. |
| `Crypto/research/passed/vpt_cmf/` | Idem halving_cycle (pas de json) | **[INDÉTERMINÉ]** | **[NON-RÉSOLU]** |
| `Equities/research/passed/jt_momentum_cs/` | `results.json` : `sharpe=-0.026, max_dd=-0.583, ic_tstat=-0.49, ic_n=244` | **FAIL** (SR≤0, MDD<-25%) | **[CONFIRMÉ — failed mal classé]** |
| `Forex/research/passed/fx_carry_trend/` | `results.json` : `sharpe_hac=-0.154, max_dd=-0.526, amtp_p=0.894` (raw_carry baseline) | **FAIL** (SR<0, MDD≈-53%) | **[CONFIRMÉ — failed mal classé]** |
| `Commodities/research/passed/` | Vide (seul `__init__.py`) | n/a | OK |
| `ETF_Vol/research/passed/` | Vide | n/a | OK |
| `Futures/research/passed/` | Vide | n/a | OK |

**Synthèse V3** :
- Items #4 (audit) confirmé pour `jt_momentum_cs` et `fx_carry_trend` : tous deux Sharpe ≤ 0, sous gate RESEARCH_PASS — **mal classés**.
- 4 dossiers Crypto/passed/ n'ont pas de `results.json` exportable → impossibilité de juger automatiquement. **Audit en partiel** (ne pas déplacer sans inspection humaine, peuvent être passés à juste titre selon feasibility.py).

---

## V4. Doublons F2 + Network Momentum

| Item | Verdict | Preuve |
|---|---|---|
| F2 présent à la fois en active/ ET archived/ | **[CONFIRMÉ]** | `ls Forex/research/{active,archived}/strategy_f2_asian_breakout/` — deux dirs existent |
| Les deux dirs sont-ils identiques ? | **[PARTIEL — partage results.json, divergent sur le reste]** | `diff` des `results.json` = 0 ligne (identiques, 67 lignes chaque). Mais : `active/` contient `feasibility.py` (25 l.) + `news_events_2020_2025.csv` (35 KB) qui ne sont PAS dans archived/. `archived/` contient `POSTMORTEM.md` qui n'est PAS dans active/. → ce n'est pas un doublon complet, ce sont deux "vues" partielles. |
| Action de l'audit "supprimer la copie active/" | **[PARTIEL]** | Supprimer brutalement active/ **perdrait** `feasibility.py` et `news_events_2020_2025.csv` qui ne sont pas dans archived/. Action correcte : déplacer `feasibility.py` + le CSV vers `archived/strategy_f2_asian_breakout/` puis supprimer le `active/`. |
| `Multi_Asset/research/active/network_momentum/` existe avec contenu | **[CONFIRMÉ]** | `feasibility_summary.md:1` : "Network Momentum (GMOM) Feasibility — Strategy E … Generated: 2026-05-21 … n_tests after: 134 … **FAIL** — best variant E3 (Sharpe=0.293)" ; 7 fichiers (universe.py, graph_learning.py, feasibility.py, etc.). CLAUDE.md:279 le liste dans ARCHIVED → drift confirmé. |

---

## V5. `research/active/` — inventaire complet

Tous les dossiers `*/research/active/` réels, avec preuve d'état et confrontation à CLAUDE.md `## Active research` (l.219-229).

| Dossier | Fichiers (hors __pycache__) | Dernière modif | État réel | Documenté CLAUDE.md ? |
|---|---|---|---|---|
| `Crypto/research/active/_preflight/` | 119 | 2026-05-23 | **[infra méthodo]** — pas une stratégie, scripts pre-flight | NON (mais OK, infra) |
| `Crypto/research/active/h31_cs_fs_dn/` | 8 | 2026-05-27 | **[recherche en cours avec résultats]** — `results/metrics_validation.json` : `sharpe_raw=-0.8044, wf_pct=25%, gates: all FAIL` ; mais aussi `metrics_raw.json` : `total_return=-0.5694`. Verdict : **FAIL DÉJÀ MESURÉ**, à archiver. | NON — mentionné seulement comme [NON-RÉSOLU] dans rapport drift |
| `Crypto/research/active/token_unlocks/` | 1 (`_bootstrap_notes.md`) | 2026-05-23 | **[WIP vide]** | NON (mais OK : noté "Untested" dans CLAUDE.md:295) |
| `Crypto/research/active/vrp_short_gamma/` | 1 (`_bootstrap_vrp_notes.md`) | 2026-05-23 | **[WIP vide]** | NON |
| `Futures/research/active/nq_intraday/` | 31 | 2026-05-28 | **[recherche en cours]** — c'est l'arbre canonique iter_1..11 + D1..D5 (cf. results.json l.1-1257) | OUI (via Strategy D path) |
| `Futures/research/active/nq_intraday_vwap/` | 3 | 2026-05-21 | **[FAIL avec résultats]** — `iter_01_summary.md:7` "FAIL — INSUFFICIENT SAMPLE (automated gates show RESEARCH_PASS but N=19 over 3 years is statistically meaningless)" ; n_tests=130 | NON |
| `Futures/research/active/strategy_d/` | 1 (`hypotheses_preregistered.md`) | 2026-05-25 | **[pré-registration seule]** | NON (CLAUDE.md pointe vers nq_intraday/analysis/) |
| `Futures/research/active/strategy_d_nq/infra/` | 3 (sh + plist + README) | 2026-05-29 | **[infra non rangée]** — flaggé dans `_meta/open_questions.md:1-26` | NON |
| `Futures/research/active/voie_b_ftmo/` | 26 | 2026-05-29 | **[recherche en cours, full study]** — 5 résultats CSV : `slip_report.csv` (vient d'apparaître dans git status), `ftmo_voie_b_returns.csv`, `voieb_test.csv`, `weekly_realtape.csv` + EA mq5 + reconciliation.md | NON |
| `Futures/research/active/zn_baltussen/` | 0 visibles (tout dans `sigma_estimation/`, `tests/`, `__pycache__/`) | — | **[recherche en cours, structure mais peu de contenu visible]** | NON |
| `Forex/research/active/cip_eoq/` | 14 | 2026-05-27 | **[recherche en cours]** — `sigma_estimation_findings.md`, `figures/`, `validate_basis.py`, `validation_log.md` | NON |
| `Forex/research/active/strategy_f2_asian_breakout/` | 6 | 2026-05-27 | **[DUPLICATE archivée]** (cf. V4) | NON ; dans drift Phase 5 |
| `Commodities/research/active/xs_basis_tsmom/` | 19 | 2026-05-23 | **[recherche en cours]** — `results/basis_coverage.csv`, `roll_plots/*.png`, `phase_a_report.txt` | OUI (CLAUDE.md:226-229) |
| `Equities/research/active/sector_hothand_propfirm/` | 12 | 2026-05-29 | **[RECHERCHE PASSANTE avec résultats]** — `results/phase1_baseline.json` : `sharpe_gross=2.52, sharpe_net=2.05, sharpe_deflated_DSR=2.01, max_drawdown=-13.3%, t_stat_alpha_hac=10.38, wf_folds_pass=5/5, wf_sharpe_oos=2.37`. **Au-dessus de PROPFIRM_PASS sur tous les gates.** | NON — **omission critique** : stratégie potentiellement passante non listée |
| `Multi_Asset/research/active/network_momentum/` | 7 | 2026-05-21 | **[FAIL mal placé]** (cf. V4) | Listée comme ARCHIVED dans CLAUDE.md:279 → drift |
| `ETF_Vol/research/active/` | — | — | DIR n'existe pas (seul `archived/`) | OK |
| `Options_Vol/research/active/` | — | — | DIR n'existe pas (seul `archived/`) | OK |

**Synthèse V5** :
- **[CONFIRMÉ]** dans l'audit drift : 7 dirs actifs non documentés (voie_b_ftmo, sector_hothand_propfirm, h31_cs_fs_dn, vrp_short_gamma, zn_baltussen, cip_eoq, nq_intraday_vwap), + strategy_d, strategy_d_nq.
- **NOUVEAU** : `sector_hothand_propfirm` montre SR_net 2.05 / DSR 2.01 / WF 5/5 → **stratégie candidate à promouvoir vers `passed/` ou D'**, jamais mentionnée dans CLAUDE.md.
- **NOUVEAU** : `h31_cs_fs_dn` a déjà des metrics → FAIL net, doit aller vers `archived/`.
- **NOUVEAU** : `nq_intraday_vwap` est en réalité une "Strategy D iter_01" (cf. summary l.1 "Strategy D iter_01") — non un dir séparé. Convention de nommage à clarifier.

---

## V6. Strategy A — source métriques (Sharpe 1.33 / MaxDD -6.9%)

| Item | Verdict | Preuve |
|---|---|---|
| `results.json` formel pour A | **[INTROUVABLE]** | `find <HOME>/Desktop/Algo_claude -name "results.json"` ne retourne aucun fichier dans `strategies/tsmom_v2_propfirm/`, `strategies/tsmom_v3/`, ni `Crypto/research/passed/tsmom_v3/`. Cherché dans : strategies/, Crypto/research/{active,archived,passed}/. |
| Source effective des chiffres "Sharpe 1.33 OOS / MaxDD -6.9%" | **[CONFIRMÉ — source = commentaire de docstring]** | `strategies/tsmom_v2_propfirm/signal.py:13-15` : `"Improvement over binary sign(): OOS Sharpe 1.33 vs 1.22 (+0.11), MaxDD −6.9% vs −12.7%, 3/4 WF folds."` Seule trace dans le repo. |
| .png correspondants | **[PARTIEL]** | `strategies/tsmom_v3/backtest_results.png` (720 KB, MAJ 2026-05-15) et `backtest_results_v2.png` existent — les nombres viennent vraisemblablement du run qui a généré ces .png, mais le JSON/CSV de sortie n'a pas été conservé. |
| Action audit "[INTROUVABLE]" | **[CONFIRMÉ]** | Item #9 du drift est validé. |

---

## V7. Strategy B — source backtest (Sharpe 4.10 / MaxDD -0.52%)

| Item | Verdict | Preuve |
|---|---|---|
| `results.json` dans `Crypto/research/archived/carry/funding_carry/` | **[INTROUVABLE]** | `ls` du dossier ne montre que : `__init__.py, fetch_funding.py, fetch_prices.py, run_feasibility.py, walk_forward.py`. Aucun `results.json` ni `metrics.json` ni `summary.md`. |
| Backtest réel exécuté ailleurs ? | **[PARTIEL]** | `strategies/delta_neutral/backtest.py` existe (31 KB, MAJ 2026-05-06) ; pas de JSON exporté à proximité. `Crypto/research/archived/carry/funding_backtest.py` existe aussi (script orphelin). Aucun de ces scripts n'a déposé de résultats persistés visibles. |
| Action audit "[INTROUVABLE]" | **[CONFIRMÉ]** | Item #9 validé. Probable cause : script lancé localement, output console seulement, jamais commité. |

---

## V8. Strategy C — métriques vs profil

| Champ | CLAUDE.md (l.45-58) | Réel | Verdict |
|---|---|---|---|
| Signal `direction du 09:30-09:45 ORB, entry at 09:46 ET` | l.46 | `Futures/live/strategy_c_live/config.py:69-71` : `ORB_OPEN=09:30, ORB_CLOSE=09:45, ENTRY_TIME=09:46` | **[CONFIRMÉ]** |
| Signal iter_10 logic | "iter_10" | `Futures/research/active/nq_intraday/analysis/iter_10_refined.py:43-46` : `STRATEGY_GAP=0.012, STRATEGY_STOP=400.0, RNG_MIN=30.0` | **[CONFIRMÉ]** |
| VWAP confirmation | l.47 | `signal_engine.py:152-158` (filtre) | **[CONFIRMÉ]** |
| gap < 1.2% | l.47 | `config.py:80` : `GAP_FILTER = 0.012` ; `iter_10_refined.py:43` : `STRATEGY_GAP=0.012` | **[CONFIRMÉ]** |
| Opening range ≥ 30 pts | l.47 | `config.py:81` : `RANGE_MIN_PTS = 30` ; `iter_10_refined.py:45` : `RNG_MIN=30.0` | **[CONFIRMÉ]** |
| $400 SL cap | l.47 | `config.py:77` : `SL_CAP_USD = 400` ; `iter_10_refined.py:44` : `STRATEGY_STOP=400.0` | **[CONFIRMÉ]** |
| TP 1.5R | l.48 | `config.py:75` : `TP_RATIO = 1.5` | **[CONFIRMÉ]** |
| SL min(0.5R, 20 pts) | l.48 | `config.py:76,78` : `SL_RATIO=0.5, SL_CAP_PTS=20.0` ; `signal_engine.py:170` : `sl_pts = min(orb_range * SL_RATIO, SL_CAP_PTS)` | **[CONFIRMÉ]** |
| Time stop 12:30 ET | l.48 | `config.py:72` : `TIME_STOP=12:30` | **[CONFIRMÉ]** |
| Backtest Sharpe 1.52 | l.49 | `nq_intraday/results.json` iter_10 entry : `sharpe_daily_hac=1.5212` | **[CONFIRMÉ]** |
| MaxDD -13.4% | l.49 | iter_10 entry : `max_dd_pct=-0.1342` | **[CONFIRMÉ]** |
| WF 78% (7/9) | l.49 | iter_10 entry : `wf_pct_extended=77.78, wf_n_windows=9` ; `wf_pct_positive=100.0` (raw). 7/9 = 77.78%. | **[CONFIRMÉ — précision : "extended" pas "raw"]** |
| N=346 | l.49 | iter_10 entry : `n_trades=346` ; `n_tests=142` (ID dans ledger) | **[CONFIRMÉ — ambiguïté "N"]** : N=346 = nombre de trades, à renommer `N_trades`. |
| FTMO MC en iter_10 | non documenté | `iter_10_refined.py:55-61` simule "FTMO trailing-DD Monte Carlo" avec `FTMO_INITIAL=100_000, FTMO_TARGET_PCT=0.10, FTMO_DD_PCT=0.10, FTMO_DAYS=30, MC_PATHS=10_000` ; mais L22(c) dit "FTMO does not support CME futures". Donc le MC FTMO est obsolète/non applicable. | **[PARTIEL — incohérence]** : iter_10_refined parle "FTMO MC" alors que CLAUDE.md L22 dit FTMO incompatible. À nettoyer. |

---

## V9. Strategy B — état live réel (VPS)

| Item | Verdict | Preuve VPS |
|---|---|---|
| B tourne réellement | **[CONFIRMÉ]** | `~/logs/delta_neutral.log` dernière entrée `2026-05-30 08:10:24` (3h avant audit) ; entry réussie HMSTR : `2026-05-25 16:10:20 [HMSTR] BN spot buy: 310559.000000 @ 0.0002` |
| Date de démarrage live "depuis 2026-05-17" (CLAUDE.md:37) | **[CONFIRMÉ]** | Première trace de "Active (vol + carry filters): ['MEGA']" suivie d'une `Reconciliation OK` (= ordres effectifs) : `2026-05-17 08:10:16`. Avant ça (du 2026-05-06 au 2026-05-16) le live échouait avec "ERROR \| --hl-key required for --live". |
| Pairs actives "TST + MEGA" (CLAUDE.md:38) | **[INFIRMÉ — outdated]** | `state.json` VPS (`~/projects/Algo_claude/strategies/delta_neutral/state.json`) : `active_pairs: ["HMSTR"]`, `positions.HMSTR.entry_time = 2026-05-25T16:10:23` ; TST `position=flat, cumulative_carry=16.367151` (a tradé puis fermé) ; MEGA `position=flat, cumulative_carry=0.106` (a tradé puis fermé). Au 2026-05-30 08:10, seul HMSTR est ouvert. TST a été tenté à 08:10 et a échoué (`HL SHORT FAILED: Trading is halted`), spot leg rollback OK. |
| Cron fonctionnel | **[CONFIRMÉ]** | crontab `10 0,8,16 * * *` + logs montrent 3 invocations/jour sans erreur depuis 2026-05-17 |
| Réconciliation startup OK | **[CONFIRMÉ]** | `2026-05-30 08:10:08 [HMSTR] startup_reconcile: no change (state=open, exchange=short)` ; toutes autres assets `state=flat, exchange=flat` |
| HMSTR funding accumulé | **[CONFIRMÉ]** | `state.json` : `cumulative_carry: 0.026315` (HMSTR depuis 2026-05-25, ~5 jours) ; TST avait accumulé $16.37 (testnet, taux artificiel cf. L14) |

**Synthèse V9** : B est bien live depuis 2026-05-17, mais CLAUDE.md liste les **mauvaises** pairs actives ("TST + MEGA" → réel "HMSTR" seule au 2026-05-30). À actualiser dynamiquement ou retirer la liste du fichier constitutionnel.

---

## V10. MAX_DAILY_DD — canonicalisation

| Fichier:ligne | Constante | Valeur | Consommée par | Propfirm associée |
|---|---|---|---|---|
| `strategies/tsmom_v2_propfirm/config.py:55` | `MAX_DAILY_DRAWDOWN` | `0.045` (4.5%) | `strategies/tsmom_v2_propfirm/sizing.py:28,127,129` (imports + utilisation dans `check_dd()`) | HyroTrader / Breakout (cf. docstring `config.py:6-11`) |
| `strategies/tsmom_v2_propfirm/config.py:56` | `MAX_TOTAL_DRAWDOWN` | `0.09` (9%) | `sizing.py:29,132,134` | HyroTrader |
| `strategies/tsmom_v2_propfirm/execution/__init__.py:46` | `MAX_DAILY_DD` | `0.028` (2.8%) | `execution/equity_monitor.py:16,44,129,156` (utilisé dans `is_safe()` runtime) | Propr (limit 3%, buffer 0.2% — cf. equity_monitor.py:34 docstring) |
| `strategies/tsmom_v2_propfirm/execution/__init__.py:47` | `MAX_TOTAL_DD` | `0.055` (5.5%) | `execution/equity_monitor.py:16,45,130,156` | Propr (limit 6%, buffer 0.5%) |
| `Futures/live/strategy_c_live/config.py:102` | `TRADEIFY_TRAILING_DD_USD` | `1_000` | `guardrails.py:33`, `tests/test_tradeify_constants.py:21` | Tradeify Select Flex eval |
| `Futures/live/strategy_c_live/config.py:103` | `TRADEIFY_TRAILING_DD` | `1_000` | tests + simulator | Tradeify Select Flex funded |
| `Futures/live/strategy_c_live/config.py:122` | `GUARDRAIL_TRAILING_DD_USD` | `850` | `guardrails.py:29`, `validate_tradovate.py:24,220`, `tests/test_config_sizing_alignment.py:26-27` | Tradeify (buffer $150) |
| `Futures/live/strategy_c_live/config.py:109` | `DAILY_LOSS_LIMIT_FUNDED_FLEX` | `None` | déclaration seule | Tradeify funded (pas de DLL) |
| `Futures/live/strategy_c_live/config.py:128-129` | `GUARDRAIL_DD_PCT=0.08, GUARDRAIL_TRAILING_DD_PCT=None` | legacy FTMO | unused per commentaire l.128 ; `validate_mt5.py:24,244-250` | FTMO legacy |
| **`Futures/research/active/nq_intraday/analysis/propfirm_compat_v2.py:750`** | `TV_TRAILING_DD` | **`2_000`** | importé par 4 scripts d'analyse (`iter_d2_mr.py`, `iter_d_pairs.py`, `iter_11_propfirm.py`) | Tradeify (**ANCIENNE valeur, ≠ live $1,000 confirmé 2026-05-25**) |

**Synthèse V10** :
- **[CONFIRMÉ — coexistence 4.5%/2.8%]** dans `strategies/tsmom_v2_propfirm/` : config.py = HyroTrader (4.5/9, consommé par sizing), execution/__init__.py = Propr (2.8/5.5, consommé par equity_monitor). Les **deux sont actifs simultanément** dans le live (cf. import trace).
- **[CONFIRMÉ runtime]** : la valeur effectivement consommée par le pipeline Propr live est `MAX_DAILY_DD=0.028` via `equity_monitor.py:129` (cf. crontab job #3 qui appelle `run_rebalance` → équipe equity_monitor). Le 4.5% de `config.py` est utilisé par `sizing.py` qui peut être appelé dans d'autres contextes (CHALLENGE_MODE).
- **[NOUVEAU drift]** : `propfirm_compat_v2.py:750` utilise encore **TV_TRAILING_DD=2_000** au lieu des $1,000 confirmés 2026-05-25 → recherche nq_intraday risque de simuler avec une mauvaise DD. À aligner sur live config.

---

## V11. Secrets — sans printer aucune valeur

### .env et .env.example (local)

| Item | Verdict | Preuve |
|---|---|---|
| `.env` présent + gitignored | **[CONFIRMÉ]** | `ls -la .env` → `-rw-r--r-- … 164 bytes 2026-05-22 23:13` ; `.gitignore:2` : `.env` |
| `.env` keys (noms seuls) | **[CONFIRMÉ]** 5 keys | `MT5_SERVER, MT5_LOGIN, MT5_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID` |
| `.env.example` keys | **[CONFIRMÉ]** 3 templates | `TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HYPERLIQUID_PRIVATE_KEY` |
| Désynchronisation `.env.example` vs vars réellement consommées dans le code | **[CONFIRMÉ]** | Variables consommées (`grep os.getenv/os.environ` au repo) : `PROPR_API_KEY` (run_rebalance.py:44, propr_sdk.py:61, daily_summary.py:160, discover_api.py:25), `PROPR_API_URL` (propr_sdk.py:64), `TRADOVATE_{ENV,USERNAME,PASSWORD,CID,SECRET,APP_ID,APP_VERSION,DEVICE_ID}` (config.py:44-51), `BINANCE_TESTNET_API_KEY/SECRET_KEY` (live_trader.py:800-801), `HYPERLIQUID_TESTNET_KEY` (live_trader.py:802), `TELEGRAM_BOT_TOKEN/CHAT_ID` (multiple), `GLASSNODE_API_KEY` (mvrv/feasibility.py:386), `FRED_API_KEY` (data/cache.py:284), `MT5_SERVER/LOGIN/PASSWORD` (mt5_client). **.env.example en couvre 3 sur ~14**. |

### Crontab VPS — fuite de secrets en clair

| Item | Verdict | Preuve (redactée) |
|---|---|---|
| Le `crontab -l` VPS contient des secrets en cleartext | **[CONFIRMÉ — incident sécurité]** | 4 occurrences identifiées dans le `crontab -l` : (a) ligne 1 `run_tsmom.sh --private-key <REDACTED:HL_PRIVKEY>` (clé privée Hyperliquid, ~64 hex chars) ; (b) ligne 3 `PROPR_API_KEY=<REDACTED:PROPR_LIVE_KEY>` (préfixe "pk_live_" indiquant **clé live Propr** — pas testnet) ; (c) ligne 4 mêmes + `TELEGRAM_BOT_TOKEN=<REDACTED>` + `TELEGRAM_CHAT_ID=<REDACTED>` |
| **Fait NOUVEAU** : `tsmom_v2_cron.log:48` contient ÉGALEMENT la cron line avec secret cleartext en log | **[CONFIRMÉ]** | Dernière ligne de `logs/tsmom_v2_cron.log` VPS imprime "Cron line for VPS deployment: 5 0 * * 1 cd … PROPR_API_KEY=pk_live_XXX python …" — l'API key est en clair dans le log applicatif (probablement copie du log avant rotation). |
| Statut "5 secrets compromis, regen pending" | **[PARTIEL — mapping incertain]** | Les "5" du `.env` local (`MT5_*` ×3 + Telegram ×2) ≠ les secrets visibles dans crontab VPS (PROPR + HL_PRIVKEY + Telegram). **Les 5 visés par la mission ne sont pas explicitement définis dans le repo**. Hypothèse plausible : les "5" = PROPR_API_KEY + HYPERLIQUID_PRIVATE_KEY + Telegram pair + 1 autre (BINANCE testnet ?). À **CONFIRMER MANUELLEMENT**. |

### Git history — recherche de fuite

| Item | Verdict | Preuve |
|---|---|---|
| `.env` jamais commité (selon historique) | **[CONFIRMÉ]** | `git log --diff-filter=A --name-only \| grep "^\.env$"` → vide ; `.gitignore` historique exclut `.env`. |
| `git log -S "PROPR_API_KEY"` retourne commits | 4 commits matchent : `4189da3, e079489, 33cd26a, 92bf9dc` | **[PARTIEL]** : ces commits referencent le NOM de la variable (code Python ou docs), pas nécessairement la valeur. **Non-vérifié sans printer le diff** (interdiction de print les valeurs). |
| `git log -S "HYPERLIQUID_PRIVATE_KEY"` retourne 1 commit | `a97dacf "Initial commit: hardened live trader"` | **[PARTIEL]** idem : référence au nom. |
| `git log -S "pk_live"` (préfixe de clé Propr) retourne 3 commits | `4189da3, 33cd26a, 92bf9dc` | **[NON-RÉSOLU — alerte]** : le préfixe `pk_live` est le préfixe officiel des clés live Propr. Trois commits le contiennent. **Doit être vérifié sans printer la valeur** : exécuter `git log -p -S "pk_live" -- '*.py' '*.sh' '*.md'` et vérifier manuellement (idéalement avec un outil de scan type `trufflehog` ou `gitleaks`). |
| Statut rotation faite ou pending | **[NON-RÉSOLU]** | Pas d'horodatage de rotation dans le repo. La clé live Propr est encore dans `crontab -l` au 2026-05-30 11:15 UTC, et le préfixe "pk_live_" reste identique à celui des commits historiques. **Sans connaître l'horodatage de la dernière rotation Propr, je ne peux pas trancher.** |

---

## V12. CI — `.github/workflows/auto-merge.yml`

| Item | Verdict | Preuve |
|---|---|---|
| Workflow existe | **[CONFIRMÉ]** | `.github/workflows/auto-merge.yml` (170 l.) |
| Auto-squash sur PR `claude/*` | **[CONFIRMÉ]** | l.13 `if: startsWith(github.head_ref, 'claude/')` ; l.111-129 squash via `pulls.merge merge_method: 'squash'` avec retry x5 |
| Hard-fail paths exacts | **[CONFIRMÉ]** | l.51-55 : `SENSITIVE=$(echo "$CHANGED" \| grep -E '^(Futures/live/\|Portfolio/\|strategies/\|\.github/)' \|\| true)` + `MQ5_FILES=$(echo "$CHANGED" \| grep -E '\.mq5$' \|\| true)` |
| Restriction `_automation/` only | **[CONFIRMÉ]** | l.66-77 : `OUTSIDE=$(echo "$CHANGED" \| grep -v '^_automation/' \|\| true)` ; si non-vide → `eligible=false` |
| Label `needs-human-review` posé sinon | **[CONFIRMÉ]** | l.86-91 |
| Notification Telegram on failure | **[CONFIRMÉ]** | l.158-170 |

---

## V13. Archives introuvables (CS-FS, FRA, Wikipedia/L18)

| Item | Verdict | Preuve / lieu cherché |
|---|---|---|
| Wikipedia attention (L18) | **[CONFIRMÉ — TROUVÉ]** : audit s'est trompé en disant introuvable | `Crypto/research/archived/other/wav_h3/` existe (HYPOTHESIS_WAV.md, POSTMORTEM.md, data/wiki/{ADA,ALGO,AVAX,...}.parquet 10+ tickers, analysis_phase2.py, fetch_data.py). "wav_h3" = Wikipedia Attention Vector hypothesis 3, mappé à L18. |
| CS-FS (Crypto cross-sectional funding stack) | **[NON-RÉSOLU]** | Cherché : `find -iname "*cs_fs*"` retourne uniquement `Crypto/research/active/h31_cs_fs_dn/` (recherche EN COURS, pas l'archive historique annoncée). `grep -rln "CS-FS\|cs_fs\|carry.stack"` dans archived/ → 1 hit dans `pmr_basis/POSTMORTEM.md` (mention textuelle seulement, pas un dossier). **L'archive originale CS-FS n'a jamais été créée comme dossier dédié** ; CLAUDE.md:236 fait référence à un test que je ne peux pas localiser. |
| FRA (Funding Rate Arb) | **[NON-RÉSOLU]** | Cherché : `find -iname "*FRA*"` / `*funding_rate_arb*` → 0 résultat hors mentions textuelles dans CLAUDE.md, README.md, `_meta/lesson_11_beta_dominance.md`, `_meta/docs/*`. **Pas de dossier dédié**. Hypothèse : archivé sous un autre nom (`Crypto/research/archived/carry/funding_carry/` ? `funding_momentum/` ? `funding_reversal/` ?) — à confirmer. |

---

## V14. Recompte n_tests

**Règle de comptage adoptée** : un "test" = une variante distincte (ID `n_test` dans le ledger), pas un dossier. Les compte ne peuvent être faits proprement qu'à partir d'un `ledger.csv` qui n'existe pas — ce qui rend tout recompte mécanique impossible **sans ouvrir chaque results.json**.

| Item | Verdict | Preuve |
|---|---|---|
| CLAUDE.md:199 dit "n_tests = 322" | — | constat |
| CLAUDE.md:208 commentaire HTML dit "321 final" | — | constat |
| README.md:4 dit "321 signals/variants tested" | — | constat |
| Branche `claude/h31-cs-fs-dn-test-160` ouverte | **[INFO]** | `git branch -a` ligne 6 ; commits `4ed14cf "Pre-spec H31 CS-FS DN — test #160 updated"`, `bed5a88 "Pre-spec H31 CS-FS DN — test #160 pre-registered — STOP: N=20 < 22 threshold"` — h31 = test #160. |
| h31 a déjà tourné (résultats existent) | **[CONFIRMÉ]** | `metrics_validation.json` présent, gates FAIL. Donc le test #160 EST consommé. |
| Recompte mécanique 321 vs 322 | **[NON-RÉSOLU]** | Le repo ne dispose pas d'un index unique des `n_test`. Le `Futures/research/active/nq_intraday/results.json` contient des `n_tests` allant de 86 à 158 (avec lacunes), `nq_intraday_vwap/iter_01_summary.md` dit "n_tests after: 130", `Multi_Asset/.../network_momentum/feasibility_summary.md` dit "n_tests after: 134" — ces numéros sont des **timestamps** ordinaux séquentiels que seul l'auteur peut arbitrer. Sans un index `_meta/n_tests.csv`, je ne peux que constater l'incohérence interne CLAUDE.md (322 vs 321) — sans la trancher mécaniquement. **Le test #160 (h31) suggère que le compteur est >= 160 à ce jour** ; donc ni 321 ni 322 ne sont à jour si h31 vient s'ajouter. |

---

## Synthèse finale

### (a) CONFIRMÉ — prêt à corriger

| Item drift | Verdict | Action |
|---|---|---|
| F2 dupliqué active/+archived/ (drift #2) | CONFIRMÉ partiel (results.json identique, autres fichiers divergent) | déplacer `feasibility.py` + `news_events_2020_2025.csv` de active/ vers archived/, puis supprimer active/ |
| Network Momentum mal placé (drift #3) | CONFIRMÉ | `git mv Multi_Asset/research/active/network_momentum/ Multi_Asset/research/archived/` |
| `passed/` contient stratégies failed (drift #4) | CONFIRMÉ pour jt_momentum_cs et fx_carry_trend | `git mv` vers archived/ |
| `.env.example` désynchronisé (drift #5) | CONFIRMÉ — 3 templates pour ~14 vars consommées | régénérer `.env.example` avec : TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HYPERLIQUID_PRIVATE_KEY, HYPERLIQUID_TESTNET_KEY, BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_SECRET_KEY, PROPR_API_KEY, PROPR_API_URL, TRADOVATE_USERNAME, TRADOVATE_PASSWORD, TRADOVATE_CID, TRADOVATE_SECRET, TRADOVATE_ENV, TRADOVATE_DEVICE_ID, TRADOVATE_APP_ID, TRADOVATE_APP_VERSION, MT5_SERVER, MT5_LOGIN, MT5_PASSWORD, GLASSNODE_API_KEY, FRED_API_KEY |
| Strategy A signal.py ✓, params ✓, guardrails 2.8%/5.5% canoniques (V10) | CONFIRMÉ | aligner config.py:55-56 (clarifier qu'ils ne sont PAS canoniques pour Propr) |
| Strategy C tous params ✓ (V8) | CONFIRMÉ | nettoyer `iter_10_refined.py:55-61` mention "FTMO MC" obsolète |
| Strategy B live since 2026-05-17 (V9) | CONFIRMÉ | — |
| Strategy B "TST + MEGA" outdated (drift Phase 3) | CONFIRMÉ — pair active réelle = **HMSTR** au 2026-05-30 | retirer la liste des pairs de CLAUDE.md (volatile) OU mettre "TST/MEGA historiques, HMSTR au 2026-05-30" |
| Voie B FTMO, sector_hothand_propfirm, cip_eoq, h31, nq_intraday_vwap, zn_baltussen non documentés (drift #6) | CONFIRMÉ | ajouter à `## Active research` ; sector_hothand_propfirm = candidat **promotion** (SR_net 2.05 / DSR 2.01) |
| CI auto-merge non documenté (drift #10) | CONFIRMÉ | ajouter section "CI" à CLAUDE.md |
| Crontab VPS divergent (V2) | CONFIRMÉ — minute fausse + 8 jobs absents du profil | mettre à jour CLAUDE.md:86-87 avec les 10 lignes réelles (sans secrets) |
| Crontab VPS contient secrets en cleartext (V11) | **CONFIRMÉ — incident sécurité majeur** | **migrer tous les secrets vers `.env` source dans la cron** (pattern déjà utilisé pour delta-neutral ligne 5) ; rotater **immédiatement** PROPR_API_KEY (pk_live) et HYPERLIQUID_PRIVATE_KEY si pas déjà fait |
| Watchdog cron dupliqué (V2 #6+#7) | CONFIRMÉ | supprimer une des deux lignes |
| `tsmom_v2_cron.log` contient PROPR_API_KEY en clair (V11) | CONFIRMÉ | purger le log + ne pas imprimer la cron line dans les logs applicatifs |
| iter_10 mentionne FTMO MC alors que FTMO ≠ CME (V8) | CONFIRMÉ | nettoyer `iter_10_refined.py` |
| `propfirm_compat_v2.py:750` TV_TRAILING_DD=2_000 (V10) | **CONFIRMÉ — nouvel écart** | aligner sur live config $1,000 |

### (b) INFIRMÉ — l'audit s'est trompé

| Item drift | Vérité corrigée |
|---|---|
| "Wikipedia attention introuvable" (drift Phase 5) | **TROUVÉ** dans `Crypto/research/archived/other/wav_h3/` (POSTMORTEM.md + data/wiki/*.parquet). L'audit n'a pas reconnu l'acronyme "wav_h3" = Wikipedia Attention Vector h3. |
| "CLAUDE.md:86 TSMOM state `25 0 * * 1`" (drift Phase 4) | Plus grave que documenté : (1) la minute correcte est `5` pas `25` ; (2) il existe en PLUS un job daily `5 0 * * *` qui place des fills HL testnet ; (3) au lundi 00:05 il y a collision de deux jobs. |
| "VPS crons state-tracking only" (drift Phase 4) | INFIRMÉ : daily HL testnet place des fills (cf. fills.csv 2026-05-28). Seul Propr est gelé (dernière entrée v2_cron.log = 2026-05-11). |
| "NQ paper cron `25 13 * * 1-5`" (CLAUDE.md:54,87) | INFIRMÉ : cette cron n'existe pas. Seul watchdog_check.sh tourne dans cette fenêtre. Strategy C n'est pas automatisée. |
| Strategy A "PAUSED" entière (CLAUDE.md:27) | INFIRMÉ partiel : Propr Monday paused ✓ (cohérent), mais HL testnet daily continue de trader (placements de fills observés 2026-05-27/28). |

### (c) NON-RÉSOLU — pourquoi + commande exacte à lancer

| Item | Pourquoi NON-RÉSOLU | Commande à lancer pour trancher |
|---|---|---|
| 4 dossiers `Crypto/research/passed/{halving_cycle, hmm_transitions, obv_signal, vpt_cmf}` sans `results.json` | Verdict pass/fail non extractible automatiquement | Lancer chaque `feasibility.py` ou ajouter un export JSON : `cd ~/Desktop/Algo_claude && for d in halving_cycle hmm_transitions obv_signal vpt_cmf; do /usr/bin/python3 Crypto/research/passed/$d/feasibility.py 2>&1 \| tee Crypto/research/passed/$d/results.txt ; done` |
| CS-FS archive originale | Cherché exhaustivement, pas trouvé comme dossier dédié | `git log --all --diff-filter=D --name-only \| grep -i "cs.fs"` (recherche d'un dossier supprimé) — si rien, alors **CS-FS n'a jamais existé comme dossier**, c'est une mention textuelle dans la prose CLAUDE.md (à corriger ou à formaliser) |
| FRA archive originale | Idem | `git log --all --diff-filter=D --name-only \| grep -iE "fra\|funding_rate_arb"` + inspecter `Crypto/research/archived/carry/funding_{momentum,reversal}/feasibility.py` qui pourraient être les vrais artefacts de la "FRA" |
| Status rotation 5 secrets | Pas d'horodatage de rotation dans le repo. Clé `pk_live_*` toujours dans crontab au 2026-05-30 11:15 UTC, préfixe inchangé depuis les commits historiques. | À toi : confirmer dans le portail Propr/Hyperliquid si la dernière rotation est postérieure aux commits référençant ces préfixes. Sinon : **rotater maintenant** ; commande SSH pour purger crontab des valeurs : `ssh algo@VPS 'crontab -l > /tmp/crontab.bak && nano /tmp/crontab.bak'` (édition manuelle, puis `crontab /tmp/crontab.bak`). |
| `git log -S "pk_live"` 3 commits | Vérifier si les commits contiennent la VALEUR (pas juste le préfixe en doc/exemple) sans printer la valeur | Lance toi-même : `git log -p -S "pk_live" -- '*.py' '*.sh' '*.md' \| grep -c "pk_live_[A-Za-z0-9]"` — si compte > 0, fuite confirmée. Ou utiliser `trufflehog filesystem .` / `gitleaks detect` pour un scan structuré. |
| n_tests 321 vs 322 | Pas d'index ledger global | Créer `_meta/n_tests_ledger.csv` (1 ligne par test, colonnes : id, dossier, date, verdict). Compter ensuite. h31_cs_fs_dn (test #160) suggère que le vrai compteur courant est `~ 160 + tests post-h31`, donc largement < 321/322 si on compte par dossier, ou > si on compte les variantes (iter_1a, 1b, ...). À standardiser. |
| Status réel de la clé live Propr "pk_live_…" présente dans crontab | Je n'ai pas vérifié si elle ouvre une session valide (lecture seule autorise SSH mais pas API call Propr) | Vérification : `ssh algo@VPS 'cd ~/projects/Algo_claude && source ~/venv/bin/activate && source <(crontab -l \| grep PROPR_API_KEY \| head -1 \| awk "{for(i=1;i<=NF;i++)if(\$i~/^PROPR_API_KEY=/)print \"export \"\$i}") && python -c "from strategies.tsmom_v2_propfirm.execution.propr_sdk import ProprClient; print(ProprClient().get_equity())"'` — si OK = clé toujours active = pas encore rotatée. |

---

**Fin du rapport.** Aucun fichier modifié hors `_audit/verification_2026-05-30.md`. Aucun commit. Aucun appel d'écriture VPS.
