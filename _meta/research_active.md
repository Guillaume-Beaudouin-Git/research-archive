# Active research — inventaire détaillé (vérifié 2026-05-30 ; tronc Multi_Asset indexé 2026-08-24)

Sorti de `CLAUDE.md` §Research history (2026-07-30) pour tenir sous la limite de chars Claude Code.
Contenu intégral, aucune info perdue. `CLAUDE.md` conserve la LISTE des chantiers ; le détail est
ici. État courant / blockers : `_meta/current_focus.md`. Familles fermées : `research_history.md` (racine).

⚠ **Les entrées ci-dessous (hors §Multi_Asset) datent de 2026-05-30 et n'ont pas été retouchées.**
Le corps de recherche le plus actif du dépôt depuis 2026-07 est `Multi_Asset/research/active/`
(48 dossiers datés 2026-07/2026-08, source des leçons L51-L60) — voir §Tronc Multi_Asset ci-dessous.

## Tronc Multi_Asset (`Multi_Asset/research/active/`) — inventaire 2026-08-24

48 dossiers datés `<sujet>_2026-07` / `_2026-08`, cycle pré-registration → résultats → verdict
(`docs/RESEARCH_METHOD.md`). Vue d'ensemble narrative (moins exhaustive, plus de contexte) :
`Multi_Asset/README.md`. Verdicts lus directement dans chaque dossier (pas recopiés d'un résumé) :

| Dossier | Verdict en une ligne |
|---|---|
| `ath_regime_review_2026-08/` | REJECTED — ATH = état le plus sûr, mais échoue au contrôle d'orthogonalité (bug config Phase-2 trouvé au passage). Reproduit L54. |
| `audit_entree_109_2026-08/` | Correction du biais d'entrée intra-barre sur le corpus 109 stratégies, 4 gates constitutionnels réels : 2 verdicts DISCARD→KEEP (S037, S061 ORB canonique), 6 restent DISCARD. |
| `audit_micro_orb_2026-08/` | Pas de dominance statistique p(pass)/durée entre variantes micro-ORB — tous les CI95 se chevauchent. |
| `audit_moteur_bracket_2026-08/` | Audit du biais de départage intra-barre : 1 exposition confirmée (`intraday_mr_ftmo`, verdict inchangé — biais 100-1000× trop petit) ; corpus 109 quasiment immunisé (brackets 6×ATR) mais porte une ambiguïté d'ENTRÉE distincte non quantifiée ici. 0 verdict de stratégie ne bascule sur ce biais. |
| `audit_sleeve_gold_2026-08/` | Dead-zone gold : EXACTE au niveau mécanique, FAUSSE au niveau économique — les états filtrés ne rapportent rien (+0.004 bps, t 0.00, N=1421). |
| `audit_sleeve_j1_2026-08/` | J1 n'est pas une sleeve : long USDJPY vol-targeté allumé 65 % du temps (R²=65.6 %, α +0.29 %/an, t_HAC +0.22). Le filtre 12-1 ne sépare rien. |
| `carto_reouverture_2026-08/` | Cartographie des familles archivées rouvrables (politique 2026-07-30) : 2 candidats méritent réouverture (1 net), 1 troisième retiré après vérification du fichier source. |
| `close_continuation_gold_subwindows_2026-08/` | Mécanisme CONFIRMÉ sur US100 (pression de clôture continue), EDGE REJECTED à l'exécution — demi-vie ≈1 min, rien ne reste après 2 min de retard. |
| `close_momentum_dose_2026-08/` | REJECTED, kill mécanique — courbe de dose plate, contrôle négatif XAUUSD (sans écosystème LETF) seul monotone : ordre attendu inversé. |
| `cohort_clustering_2026-08/` | Aucun cluster au-delà du chevauchement — le réel clusterise MOINS que le placebo (24/24). Le claim « lancer avril/octobre » d'une session antérieure est retiré. |
| `cost_denominator_2026-07/` | Audit N0 (0 essai consommé) : établit le coût RT réel par instrument FTMO — dénominateur du gate gross/coût. Source de `COST_AUDIT.md`. |
| `cross_conditioning_2026-08/` | VERDICT : gradient plat sur les six états testés — aucun conditionnement ne concentre les deux edges sous-puissants étudiés. Résultat NET, pas nul. |
| `decorrelated_sleeves_2026-07/` | 3 pistes (stat-arb, range, MR-indices) FALSIFIED comme sleeves FTMO, vérifiées indépendamment. |
| `edge_inventory_2026-07/` | N0 (0 essai) : inventaire-lecture de tous les edges déjà mesurés dans le repo (118 entrées, `INVENTORY.csv`) — aucun nouveau backtest. |
| `exogenous_predictors_2026-08/` | N0 screening, aucun PASS revendiqué ; une candidate instruite (XAUUSD veille de CPI, t=3.86). |
| `forced_flow_cooccurrence_2026-08/` | REJECTED — courbe de dose plate une fois les deux confondants retirés. |
| `funded_1y_mono_2026-08/` | Étude du book funded mono-sleeve déployé : campagne P1+P2 passée en 23 jours (0 intervention) ; carte des leviers d'EV du book (`CARTE_EV_2026-08-20.md`). |
| `gap_pattern_rehab_2026-07/` | ❌ REJECTED (2026-07-31), contribution `n_tests` +6. Source des leçons L59 (delay+1 n'atteste que l'entrée) et L60 (barres à fourchette nulle). |
| `gold_cpi_eve_2026-08/` | Test confirmatoire pré-enregistré : REJETÉ (règle R4). Exemple travaillé dans `docs/RESEARCH_METHOD.md`. |
| `gross_surface_map_2026-08/` | N0 screening non-déflateur, aucun PASS revendiqué — carte de 8 695 cellules, shortlist vide malgré une vraie queue de t élevés. |
| `growth_engine_2026-07/` | Verdicts par tâche : reproduction/look-ahead/growth-math CONFIRMED, mais le chiffre "headline" NOT-CONFIRMED. |
| `literature_review_2026-08/` | N0 (0 essai) : audit des verdicts MR/L43 existants + revue de littérature orientée mécanisme. |
| `literature_sweep_2026-08/` | N0 (0 essai) : revue de mécanismes exploitables hors pairs/statarb/mur temporel, filtrée FTMO 2-step. |
| `marginal_admission_2026-08/` | Outil de critère d'admission marginal : une persistance de 10 jours achète Δp(pass) = +14.95 pts contre son propre placebo décalé. |
| `month_end_vehicle_2026-07/` | L'effet month-end ZN est capturable à 93 % sur un véhicule futures propfirm — mais le véhicule réel dominant est le compte perso IBKR. Source de L51-L53. |
| `mr_grille_suite_2026-08/` | Verdict en une page — suite de la grille MR intraday (famille close, voir `mr_univers_complet_2026-08/`). |
| `mr_intraday_grille_2026-08/` | Verdict en une page — grille MR intraday, contribue à la fermeture de la famille (~1 454-1 526 cellules, 0 survivant). |
| `mr_stress_conditional_2026-08/` | Verdict en une page — MR intraday sous conditionnement de stress. |
| `mr_timezone_repair_2026-08/` | Réparation de fuseau horaire pour la grille MR + premier test de la fenêtre de clôture des indices. Verdicts en une page. |
| `mr_univers_complet_2026-08/` | Verdict en une page — univers complet MR intraday ; ferme la famille (0 survivant sur ~1 454-1 526 cellules testées à travers ce sous-tronc). |
| `orb_cost_funded_2026-08/` | Verdict `ORB_KILL` (amendement §1, 2026-08-21) — tient malgré la correction ultérieure du biais moteur (`audit_moteur_bracket_2026-08/`). Source de `AUDIT_PR429_2026-08-18.md` et `DEPLOY_spread_logger.md`. |
| `overnight_futures_2026-07/` | Verdict en un paragraphe — corrections d'horloge de session pour le drift overnight or/argent/WTI. Source de L56, L57. |
| `overnight_sleeve_reopen_2026-08/` | Réouverture instruite (politique 2026-07-30) : le kill de juin 2026 était de nature GÉOMÉTRIE+VÉHICULE, donc rouvrable — angle neuf : mur 91j auto-imposé + coût or sur-facturé 1.9×. |
| `overnight_vs_intraday_2026-08/` | Table de contrôles + verdicts comparant les familles overnight vs intraday. |
| `pairs_cointegration_2026-08/` | REJECTED sur le VÉHICULE — 0/171 paires ont une demi-vie compatible avec la barrière de séance FTMO (min 1588 min vs porte 480). |
| `phase2_sizing_2026-08/` | Code + tables uniquement (`tables/*.csv`), pas de verdict écrit dans ce dossier — alimente les chiffres de sizing phase-2 cités par `funded_1y_mono_2026-08/` et `wall_economics_2026-08/`. |
| `prefomc_drift_2026-07/` | Verdict : REJECTED — pas sur une statistique, sur le split de régime (L31). |
| `reaudit_vehicule_2026-08/` | VERDICT (5 lignes) sur les sleeves XAU/JPY re-testées côté véhicule : l'une plausible à 3-6 mois, l'autre improbable à 12 mois comme sleeve vivante. |
| `regime_overlay_ftmo_2026-07/` | REJECTED — un overlay constant qui porte le même signal que le book de base n'ajoute rien de net. Source de la correction L54. |
| `regold_funnel_2026-08/` | Mesures de funnel (coûts, contrôles) ; toute revendication devra être pré-enregistrée en N2 avec sa kill rule écrite avant. |
| `rollover_dodge_2026-08/` | KILL — esquiver le rollover de swap en décalant l'entrée ne fonctionne pas ; aucune cotation dans la fenêtre de rollover CFD (kill mécanique). |
| `statarb_multivariate_2026-08/` | Verdict en une page — N=17 instruments exige un IC de 0.101 quand la littérature en donne 0.02-0.05 ; rejeté sur le véhicule. |
| `strategy_taxonomy_2026-08/` | N0 (0 backtest) : taxonomie d'hypothèses par forme de distribution attendue face à la barrière journalière FTMO. |
| `swapkilled_futures_2026-07/` | Verdict : SR ~2.0 atteint honnêtement et confirmé OOS (cible "2+" tenue) ; 2.5 n'est PAS honnêtement atteignable. |
| `treasury_auction_2026-07/` | VERDICT : REJECTED — COST-DEAD & UNDERPOWERED. Source de L58 (placebo apparié biaisé par une baseline non-inconditionnelle). |
| `two_sided_axis_2026-08/` | Verdict : l'axe du signe (long+short) est FERMÉ pour une raison structurelle, pas empirique — le short remplace un flat gratuit. |
| `wall_decision_2026-08/` | Rend le "mur temporel" décidable en fermant deux trous de mesure ; compagnon de `wall_economics_2026-08/`. |
| `wall_economics_2026-08/` | Révise l'économie du mur temporel funded : le harness comptait des gagnants comme des morts (88 % des "timeouts" ≥ cible) ; break-even révisé lui aussi, le signe ne bascule plus. |

Dossiers non listés ci-dessus (`__init__.py`) : fichier d'infra Python, pas un dossier d'étude.
`Multi_Asset/research/archived/` (hors périmètre de ce tableau) : `mtf_a1_tsmom`, `network_momentum`,
`oxfordstrat_109_audit` — voir `Multi_Asset/README.md`.

---

- **Strategy D — D3+D5 portfolio** (Futures, propfirm-targeted, decorrelated to C) : D3 (Opening
  range mid-fade 09:45-11:00, n_test=156, corr_C=-0.21) + D5 (Afternoon BB squeeze breakout
  14:00-15:30, n_test=158, corr_C=-0.05). Both failed individually (Sharpe=-1.08/-1.32) ; portfolio
  combination + regime filter under study. Pré-reg :
  `Futures/research/active/strategy_d/hypotheses_preregistered.md`. Signals canoniques :
  `Futures/research/active/nq_intraday/analysis/`. Infra paper fusionnée (P2 2026-06-10) :
  `Futures/research/active/strategy_d/infra/` (ex strategy_d_nq). Budget 3 mods, 0 consumed.
- **Commodities XS — Basis + TSMOM** (n≤279) : S_TSMOM (Moskowitz 2012) + S_BASIS (Erb-Harvey 2006),
  24 continuous contracts, monthly CS IC scan. Phase A (data fetch + roll validation) not complete.
  `Commodities/research/active/xs_basis_tsmom/`
- **Voie B FTMO (Strategy A pivot)** — full study EA mq5 + slip_analysis + reconciliation.md.
  `Futures/research/active/voie_b_ftmo/` (26 fichiers, dernière modif 2026-05-29 ;
  results/slip_report.csv dans git status, à commiter ou ignorer). [À CONFIRMER MANUELLEMENT]
  sous-jacent ciblé (mq5 = quel symbole ?).
- **sector_hothand_propfirm (Equities)** — phase 1 baseline + Monte Carlo.
  `Equities/research/active/sector_hothand_propfirm/` (12 fichiers). t_HAC alpha=10.38, SR_net=2.05,
  DSR=2.01, WF 5/5, MDD -13.3%. ⚠ t-stat 10 = drapeau rouge → audit obligatoire avant promotion
  (`_audit/sector_hothand_audit_2026-05-30.md`). MDD -13% > limite FTMO 10% → en l'état BREACH.
- **CIP-EOQ (FX)** — **ARCHIVÉ** : `Forex/research/archived/cip_eoq/` (POSTMORTEM). Copie
  `active/cip_eoq` = doublon exact, supprimée au cleanup 2026-06-10.
- **FX intraday deepdive (sub-60min FX/XAU/BTC)** — `Forex/research/active/fx_intraday_deepdive/`
  (déplacé en P2 depuis research/, cache intact, chemins relatifs ✓). Suite de l'axe laissé ouvert
  par le decision memo FTMO 2026-06-08
  (`PropFirms/ftmo/program_2026-06/PROGRAM_DECISION_MEMO.md` : do-not-fund sur free price data /
  16 instruments / N≈100).
- **ZN Baltussen (Futures)** — last-30-min momentum en ZN, Baltussen-Da-Lammers-Martens 2021 JFE.
  `Futures/research/active/zn_baltussen/` (prespec.md, feasibility.py, data_setup.py, analysis/,
  tests/ — remonté 2026-08-24, absent de main depuis le nettoyage de branches ; canary 1h yfinance
  Sharpe HAC -11.7, full backtest 1-min jamais lancé faute des données payantes FirstRateData).
  Statut réel : FEASIBILITY, pas de résultat exploitable pour l'instant.
- **NQ intraday VWAP (Strategy D iter_01)** — **ARCHIVÉ en P2** :
  `Futures/research/archived/nq_intraday_vwap/` (verdict « FAIL — INSUFFICIENT SAMPLE, N=19 over
  3 years », n_tests=130).
- **Token unlocks (Crypto)** — bootstrap seul, vide.
  `Crypto/research/active/token_unlocks/_bootstrap_notes.md`.
- **VRP short gamma (Crypto)** — bootstrap seul, vide.
  `Crypto/research/active/vrp_short_gamma/_bootstrap_vrp_notes.md`.

## Strategy C — détails opérationnels archivés (projet propfirm ANNULÉ 2026-06-10)
- Signal : direction of 09:30-09:45 ORB, entry at 09:46 ET. Filters : VWAP confirmation + gap < 1.2%
  + opening range ≥ 30pts + $400 SL cap. TP 1.5R | SL min(0.5R, 20pts) | Time stop 12:30 ET.
- Backtest HISTORIQUE (Kaggle 2022-2025, $19 RT) : Sharpe 1.52, MaxDD -13.4%, WF 78% (7/9), N=346 —
  PÉRIMÉ.
- Infra conservée (réutilisable) : `Futures/live/strategy_c_live/` (Tradovate client, signal_engine,
  guardrails), sizing_policy.md, PropFirms/tradeify/rules.md. Piste FTMO CFD distincte :
  `Futures/live/orb_floor_ftmo/` (voir DEPLOYMENT.md).
- [OBSOLÈTE 2026-06-10] Tradeify constants : eval_DD=$1,000 funded_DD=$1,000 lock=$26,100
  floor=$25,100 (confirmé 2026-05-25).
- [OBSOLÈTE] VPS cron paper `25 13/14 * * 1-5` — jamais installée (vérifié 2026-05-30) ; aucune cron
  NQ paper `25 13 * * 1-5` / `25 14 * * 1-5` n'existe → Strategy C n'est pas automatisée (cohérent
  avec « execution not started »).
