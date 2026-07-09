# Corpus audit — faux FAIL_A du pipeline feasibility

**Date**: 2026-07-09  
**Auteur**: audit automatisé (lecture seule — AUCUNE correction appliquée)  
**Périmètre**: `_automation/feasibility/tested/*.md`, verdicts FAIL_A, fenêtre 2026-05-30 → 2026-07-02  
**Bug racine**: le sandbox cloud Anthropic bloque yfinance/Binance (403). `load_strategy_a_universe()` échoue → un échec de **données** est enregistré comme FAIL_A (échec de **stratégie**). Corrigé côté code en Partie A (cache parquet + statut DATA_UNAVAILABLE). Ce rapport identifie le corpus déjà pollué **sans le réécrire**.

## Signature du bug détectée

Un backtest qui n'a jamais tourné laisse une trace nette dans le rapport :
- **GenericHandler** : `Baseline Sharpe (full sample) | n/a` + `n_days | 0`
- **SkipMonth / RegimeFilter** : table de variantes **vide** (aucune ligne), `baseline Sharpe = nan`, aucun `n_days` réel (~3000)
- Aucun entier d'échelle `n_days` (≥100) nulle part dans le rapport

Contrôle de cohérence : avec des données réelles, la baseline crypto TSMOM 28j a un Sharpe ≈ 0.68 (> gate 0.3) → un test crypto réel ressort **PASS** ou **FAIL_B**, jamais FAIL_A. Un FAIL_A sur GenericHandler ⟹ données absentes. C'est pourquoi **0** FAIL_A crypto de la fenêtre présente des chiffres réels.

## Compte par bac

| Bac | Count | Détail |
|-----|------:|--------|
| **LIKELY_FALSE** (faux négatif — à re-tester) | 51 verdicts / 50 slugs uniques | GenericHandler×37, RegimeFilterHandler×13, SkipMonthHandler×1 |
| **LIKELY_REAL** (vrai FAIL_A, chiffres réels) | 0 | — |
| **REQUIRES_HUMAN / autres** (hors scope réseau) | 2 | ExitRuleHandler (NQ, chemin local `load_nq_1min`, pas le loader crypto) |

Total FAIL_A dans la fenêtre : **53** (sur 55 FAIL_A du corpus entier ; 2 SkipMonth réels du 2026-05-24 hors fenêtre, n_days=3064, non touchés).

## Impact estimé sur n_tests (À NE PAS APPLIQUER — décision humaine)

- **51** verdicts FAIL_A sont probablement faux (**50** hypothèses uniques — un `source_md` apparaît 2× dans l'index).
- Dans la mesure où le corpus `tested/` alimente le ledger canonique, **n_tests=321 pourrait être surévalué de ~50** (borne : 50–51).
- Après réconciliation, le corpus `tested/` ne compterait plus que ~2 « vrais » FAIL_A dans la fenêtre (les 2 ExitRule, à trancher manuellement).
- ⚠️ Je n'ai PAS modifié `_state.json`, `_index.json`, ni `n_tests`. La réconciliation (retrait de l'index + décrément) t'appartient.

## Procédure de re-test (une fois le cache parquet généré sur VPS)

1. `python3 _automation/feasibility/data/build_price_cache.py` sur le VPS (réseau OK).
2. Retirer les slugs LIKELY_FALSE ci-dessous de `tested/_index.json` + `_state.json` `processed_promising` (→ ils redeviennent « untested »).
3. Relancer `orchestrator.py` : avec le cache présent ils tournent pour de vrai ; le garde-fou empêche désormais tout nouveau faux FAIL_A (statut DATA_UNAVAILABLE).

## Liste LIKELY_FALSE (50 slugs à re-tester)

| # | handler | tested_date | source_md |
|--:|---------|-------------|-----------|
| 1 | GenericHandler | 2026-05-30 | `arxiv_econ_em_a_comparative_multi_hazard_risk_assessment_of_the__20260527.md` |
| 2 | GenericHandler | 2026-05-30 | `arxiv_econ_em_algorithm_or_creative_a_three_arm_experimental_des_20260527.md` |
| 3 | GenericHandler | 2026-05-30 | `arxiv_econ_em_auditing_and_fixing_economic_validity_in_tabular_f_20260527.md` |
| 4 | GenericHandler | 2026-05-30 | `arxiv_econ_em_dynamic_consumer_demand_at_large_scale_20260527.md` |
| 5 | GenericHandler | 2026-05-30 | `arxiv_econ_em_learning_nonlinear_factor_models_with_unknown_mono_20260527.md` |
| 6 | GenericHandler | 2026-05-30 | `hn_algotrading_show_hn_i_built_a_toy_tpu_that_can_do_inference_an_20260527.md` |
| 7 | GenericHandler | 2026-05-30 | `quantocracy_a_faster_monotone_implied_volatility_solver_chase_20260527.md` |
| 8 | GenericHandler | 2026-05-30 | `quantocracy_when_everyone_trades_the_same_factor_playbook_alph_20260527.md` |
| 9 | GenericHandler | 2026-05-30 | `quantpedia_building_an_ai_powered_quant_research_assistant_w_20260530.md` |
| 10 | GenericHandler | 2026-05-30 | `quantpedia_quantpedia_premium_update_may_27th_20260530.md` |
| 11 | GenericHandler | 2026-05-31 | `quantocracy_how_to_build_a_reliable_algo_trading_infrastr_20260531.md` |
| 12 | GenericHandler | 2026-05-31 | `quantocracy_the_sharpe_stability_ratio_of_trading_strateg_20260531.md` |
| 13 | GenericHandler | 2026-05-31 | `quantpedia_quantpedia_days_2026_bring_again_11_special_offe_20260530.md` |
| 14 | GenericHandler | 2026-06-02 | `arxiv_econ_em_higher_order_debiased_estimators_for_general_treat_20260602.md` |
| 15 | GenericHandler | 2026-06-02 | `quantocracy_ai_overfitting_in_trading_systems_wisdom_trading_20260602.md` |
| 16 | GenericHandler | 2026-06-02 | `quantocracy_institutions_return_expectations_across_assets_and_20260602.md` |
| 17 | GenericHandler | 2026-06-02 | `quantocracy_market_effect_research_holiday_seasonality_part_2__20260602.md` |
| 18 | GenericHandler | 2026-06-04 | `arxiv_econ_em_resga_a_large_tail_risk_model_for_learning_value_a_20260604.md` |
| 19 | GenericHandler | 2026-06-04 | `arxiv_econ_em_scale_ordered_contagion_a_spectral_theory_of_heter_20260604.md` |
| 20 | GenericHandler | 2026-06-05 | `arxiv_econ_em_forecasting_of_volatility_and_risk_premia_in_elect_20260605.md` |
| 21 | GenericHandler | 2026-06-05 | `quantocracy_new_feature_return_contribution_analysis_allocate_20260605.md` |
| 22 | GenericHandler | 2026-06-05 | `quantocracy_trend_following_2_4_sector_by_sector_replication_b_20260605.md` |
| 23 | GenericHandler | 2026-06-10 | `quantocracy_ufc_ultimate_fitting_championships_investment_idio_20260610.md` |
| 24 | GenericHandler | 2026-06-10 | `quantpedia_quantpedia_premium_update_june_10th_20260610.md` |
| 25 | GenericHandler | 2026-06-11 | `quantpedia_quantpedia_in_may_2026_20260611.md` |
| 26 | GenericHandler | 2026-06-15 | `arxiv_econ_em_forecasting_with_bayesian_panel_vector_autoregr_20260615.md` |
| 27 | GenericHandler | 2026-06-15 | `arxiv_econ_em_granular_instrumental_variables_estimation_and_20260615.md` |
| 28 | GenericHandler | 2026-06-17 | `quantocracy_automating_volatility_strategy_python_ib_20260617.md` |
| 29 | GenericHandler | 2026-06-17 | `quantocracy_common_sense_guide_to_volatility_trading_20260617.md` |
| 30 | GenericHandler | 2026-06-17 | `quantocracy_dividend_timing_global_dividend_premium_20260617.md` |
| 31 | GenericHandler | 2026-06-17 | `quantocracy_dual_vs_single_momentum_commodities_20260617.md` |
| 32 | GenericHandler | 2026-06-17 | `quantocracy_factor_zoo_hundreds_animals_handful_species_20260617.md` |
| 33 | GenericHandler | 2026-06-17 | `quantocracy_feature_selection_filter_based_methods_20260617.md` |
| 34 | GenericHandler | 2026-06-17 | `quantocracy_fifa_portfolio_optimisation_competition_real_returns_20260617.md` |
| 35 | GenericHandler | 2026-06-17 | `quantocracy_hidden_trade_around_spacex_ipo_20260617.md` |
| 36 | GenericHandler | 2026-06-18 | `quantocracy_honey_i_shrunk_the_weights_instead_of_the_inputs_20260618.md` |
| 37 | GenericHandler | 2026-06-18 | `quantocracy_value_at_risk_estimation_improved_estimates_with_20260618.md` |
| 38 | RegimeFilterHandler | 2026-05-31 | `quantocracy_trend_following_filters_part_10_alpha_architect_20260531.md` |
| 39 | RegimeFilterHandler | 2026-06-01 | `arxiv_econ_em_modeling_covariate_transition_for_efficient_estima_20260601.md` |
| 40 | RegimeFilterHandler | 2026-06-02 | `arxiv_econ_em_information_and_voting_evidence_from_peru_s_2026_p_20260602.md` |
| 41 | RegimeFilterHandler | 2026-06-07 | `quantocracy_the_crossword_puzzle_of_fitting_why_across_and_the_20260607.md` |
| 42 | RegimeFilterHandler | 2026-06-09 | `arxiv_econ_em_ai_assisted_variance_reduction_in_randomized_expe_20260609.md` |
| 43 | RegimeFilterHandler | 2026-06-09 | `arxiv_econ_em_evaluating_ai_investment_strategies_20260609.md` |
| 44 | RegimeFilterHandler | 2026-06-10 | `quantocracy_forecasting_statistical_estimates_when_data_gets_r_20260610.md` |
| 45 | RegimeFilterHandler | 2026-06-10 | `quantocracy_what_trend_following_actually_adds_to_risk_premia_20260610.md` |
| 46 | RegimeFilterHandler | 2026-06-13 | `quantocracy_the_right_way_to_use_ai_in_trading_this_week_algori_20260613.md` |
| 47 | RegimeFilterHandler | 2026-06-15 | `quantpedia_dual_vs_single_momentum_in_commodities_enhanci_20260615.md` |
| 48 | RegimeFilterHandler | 2026-06-17 | `quantocracy_sharpe_ratio_of_pure_noise_20260617.md` |
| 49 | RegimeFilterHandler | 2026-06-18 | `arxiv_econ_em_causal_forecasting_in_panel_data_a_two_way_synthe_20260618.md` |
| 50 | SkipMonthHandler | 2026-06-18 | `quantocracy_testing_an_ai_assisted_research_workflow_for_mult_20260618.md` |

## REQUIRES_HUMAN / autres (hors scope réseau — inchangés)

| handler | tested_date | source_md | note |
|---------|-------------|-----------|------|
| ExitRuleHandler | 2026-06-07 | `quantocracy_the_non_linear_costs_of_trading_concretum_group_20260607.md` | ExitRuleHandler: no-data/parse-empty but NOT crypto-loader (NQ local path) — out of network-bug scope |
| ExitRuleHandler | 2026-06-09 | `arxiv_econ_em_a_structural_matrix_autoregressive_model_for_the_20260609.md` | ExitRuleHandler: no-data/parse-empty but NOT crypto-loader (NQ local path) — out of network-bug scope |

> Ces 2 cas (ExitRuleHandler, Stratégie C / NQ) montrent des métriques NaN mais n'utilisent PAS `load_strategy_a_universe` (ils lisent le parquet NQ local via `load_nq_1min`, + parse de modifications vide `{}`). Root cause distincte du bug réseau → laissés en l'état pour revue humaine, hors du décompte n_tests ci-dessus.

---
*Généré en lecture seule le 2026-07-09. Aucun fichier d'état modifié.*