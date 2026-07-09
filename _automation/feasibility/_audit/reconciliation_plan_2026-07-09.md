# Plan de réconciliation n_tests — faux FAIL_A feasibility

**Date**: 2026-07-09  
**Statut**: PROPOSITION — aucune écriture effectuée. À exécuter par Guillaume.  
**Ne modifie PAS encore**: `tested/_index.json`, `_state.json`, `CLAUDE.md`, `n_tests`.

## Pourquoi les chiffres diffèrent du `corpus_audit_2026-07-09.md`

L'audit initial (commit PR #383) a été calculé sur un snapshot de l'index à **170 entrées / 55 FAIL_A** (51 faux). Depuis, `git pull` a rapatrié les runs de la routine **jusqu'au 2026-07-02 inclus** — la routine cloud tournait encore, toujours cassée (sandbox 403), et a ajouté d'autres faux FAIL_A (batches 06-19, 06-20, 07-02). L'index **courant** compte **230 entrées / 81 FAIL_A**, dont **77 faux** (76 hypothèses uniques). Ce plan fait foi ; l'audit reste le snapshot historique.

## Décompte réel (index courant)

| Grandeur | Avant | Après retrait |
|----------|------:|--------------:|
| `tested_hypotheses` (index) | 230 | 153 |
| dont FAIL_A | 81 | 4 |
| clés `processed_promising` (_state) | 228 | 152 |

- Faux FAIL_A à retirer : **77 entrées d'index** couvrant **76 `source_md` uniques** (1 doublon : `quantocracy_sharpe_ratio_of_pure_noise_20260617.md` ×2).
- Présents dans `_state.processed_promising` : **76** clés à supprimer.
- FAIL_A **conservés** (4) : 2× SkipMonth `the_skip_month_mystery` (2026-05-24, n_days=3064, hors panne, vrai FAIL) + 2× ExitRuleHandler (chemin NQ local `load_nq_1min`, root cause distincte — à trancher à la main, hors périmètre du bug réseau).

Par handler parmi les faux : GenericHandler×59, RegimeFilterHandler×17, SkipMonthHandler×1.

## Impact n_tests (à valider par toi)

- Chaque FAIL_A niveau A = **+1 n_test** (cf. README feasibility). 77 faux verdicts ⟹ **n_tests surévalué de 77** (ou 76 si on compte les hypothèses uniques, le doublon ayant consommé 2 n_tests réels).
- **Nouveau n_tests proposé : 321 − 77 = 244** (borne haute 245 = 321 − 76 unique).
- ⚠️ **Caveat de traçabilité** : le lien entre le corpus `tested/` et le ledger global `n_tests=321` (CLAUDE.md) n'est PAS tracé 1:1 dans le repo (321 = ledger global tous asset classes ; le corpus automation n'en est qu'une partie). Le `321 − 77` suppose que ces 77 faux FAIL_A ont bien été comptés dans le 321. À confirmer avant de graver le chiffre.
- Note : `GenericHandler._N_TESTS_GLOBAL=274` (hardcodé) est un autre compteur, non modifié ici.

## Procédure d'exécution

1. **Avoir généré le cache** au préalable (fait : `build_price_cache.py`, parquet local).
2. Lancer le script de retrait ci-dessous (backups horodatés auto).
3. Après retrait, les 76 `.md` `promising/` redeviennent "untested" → la routine (option A ou B, une fois le cache accessible) les re-teste pour de vrai, et le garde-fou empêche tout nouveau faux FAIL_A (statut DATA_UNAVAILABLE).
4. Réconcilier `n_tests` dans CLAUDE.md **manuellement** selon le caveat ci-dessus.

## Bloc à exécuter (prêt à copier)

```bash
cd ~/Desktop/Algo_claude   # ou ~/projects/Algo_claude sur le VPS
/usr/bin/python3 _automation/feasibility/_audit/apply_reconciliation.py --apply
```

Le script `apply_reconciliation.py` (généré ci-dessous, **dry-run par défaut**) :
- re-vérifie que chaque entrée ciblée est bien une panne-données (signature vide/n_days<30) AVANT de retirer — refuse de toucher un FAIL_A avec vraies métriques ;
- écrit `tested/_index.json.bak_<ts>` et `_state.json.bak_<ts>` ;
- retire les entrées de `tested_hypotheses` et les clés de `processed_promising` ;
- n'écrit RIEN sans `--apply` ; ne touche jamais `CLAUDE.md`.

## Liste exacte des 76 `source_md` à retirer

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
| 13 | RegimeFilterHandler | 2026-05-31 | `quantocracy_trend_following_filters_part_10_alpha_architect_20260531.md` |
| 14 | GenericHandler | 2026-05-31 | `quantpedia_quantpedia_days_2026_bring_again_11_special_offe_20260530.md` |
| 15 | RegimeFilterHandler | 2026-06-01 | `arxiv_econ_em_modeling_covariate_transition_for_efficient_estima_20260601.md` |
| 16 | GenericHandler | 2026-06-02 | `arxiv_econ_em_higher_order_debiased_estimators_for_general_treat_20260602.md` |
| 17 | RegimeFilterHandler | 2026-06-02 | `arxiv_econ_em_information_and_voting_evidence_from_peru_s_2026_p_20260602.md` |
| 18 | GenericHandler | 2026-06-02 | `quantocracy_ai_overfitting_in_trading_systems_wisdom_trading_20260602.md` |
| 19 | GenericHandler | 2026-06-02 | `quantocracy_institutions_return_expectations_across_assets_and_20260602.md` |
| 20 | GenericHandler | 2026-06-02 | `quantocracy_market_effect_research_holiday_seasonality_part_2__20260602.md` |
| 21 | GenericHandler | 2026-06-04 | `arxiv_econ_em_resga_a_large_tail_risk_model_for_learning_value_a_20260604.md` |
| 22 | GenericHandler | 2026-06-04 | `arxiv_econ_em_scale_ordered_contagion_a_spectral_theory_of_heter_20260604.md` |
| 23 | GenericHandler | 2026-06-05 | `arxiv_econ_em_forecasting_of_volatility_and_risk_premia_in_elect_20260605.md` |
| 24 | GenericHandler | 2026-06-05 | `quantocracy_new_feature_return_contribution_analysis_allocate_20260605.md` |
| 25 | GenericHandler | 2026-06-05 | `quantocracy_trend_following_2_4_sector_by_sector_replication_b_20260605.md` |
| 26 | RegimeFilterHandler | 2026-06-07 | `quantocracy_the_crossword_puzzle_of_fitting_why_across_and_the_20260607.md` |
| 27 | RegimeFilterHandler | 2026-06-09 | `arxiv_econ_em_ai_assisted_variance_reduction_in_randomized_expe_20260609.md` |
| 28 | RegimeFilterHandler | 2026-06-09 | `arxiv_econ_em_evaluating_ai_investment_strategies_20260609.md` |
| 29 | RegimeFilterHandler | 2026-06-10 | `quantocracy_forecasting_statistical_estimates_when_data_gets_r_20260610.md` |
| 30 | GenericHandler | 2026-06-10 | `quantocracy_ufc_ultimate_fitting_championships_investment_idio_20260610.md` |
| 31 | RegimeFilterHandler | 2026-06-10 | `quantocracy_what_trend_following_actually_adds_to_risk_premia_20260610.md` |
| 32 | GenericHandler | 2026-06-10 | `quantpedia_quantpedia_premium_update_june_10th_20260610.md` |
| 33 | GenericHandler | 2026-06-11 | `quantpedia_quantpedia_in_may_2026_20260611.md` |
| 34 | RegimeFilterHandler | 2026-06-13 | `quantocracy_the_right_way_to_use_ai_in_trading_this_week_algori_20260613.md` |
| 35 | GenericHandler | 2026-06-15 | `arxiv_econ_em_forecasting_with_bayesian_panel_vector_autoregr_20260615.md` |
| 36 | GenericHandler | 2026-06-15 | `arxiv_econ_em_granular_instrumental_variables_estimation_and_20260615.md` |
| 37 | RegimeFilterHandler | 2026-06-15 | `quantpedia_dual_vs_single_momentum_in_commodities_enhanci_20260615.md` |
| 38 | GenericHandler | 2026-06-17 | `quantocracy_automating_volatility_strategy_python_ib_20260617.md` |
| 39 | GenericHandler | 2026-06-17 | `quantocracy_common_sense_guide_to_volatility_trading_20260617.md` |
| 40 | GenericHandler | 2026-06-17 | `quantocracy_dividend_timing_global_dividend_premium_20260617.md` |
| 41 | GenericHandler | 2026-06-17 | `quantocracy_dual_vs_single_momentum_commodities_20260617.md` |
| 42 | GenericHandler | 2026-06-17 | `quantocracy_factor_zoo_hundreds_animals_handful_species_20260617.md` |
| 43 | GenericHandler | 2026-06-17 | `quantocracy_feature_selection_filter_based_methods_20260617.md` |
| 44 | GenericHandler | 2026-06-17 | `quantocracy_fifa_portfolio_optimisation_competition_real_returns_20260617.md` |
| 45 | GenericHandler | 2026-06-17 | `quantocracy_hidden_trade_around_spacex_ipo_20260617.md` |
| 46 | RegimeFilterHandler | 2026-06-17 | `quantocracy_sharpe_ratio_of_pure_noise_20260617.md` |
| 47 | RegimeFilterHandler | 2026-06-18 | `arxiv_econ_em_causal_forecasting_in_panel_data_a_two_way_synthe_20260618.md` |
| 48 | GenericHandler | 2026-06-18 | `quantocracy_honey_i_shrunk_the_weights_instead_of_the_inputs_20260618.md` |
| 49 | SkipMonthHandler | 2026-06-18 | `quantocracy_testing_an_ai_assisted_research_workflow_for_mult_20260618.md` |
| 50 | GenericHandler | 2026-06-18 | `quantocracy_value_at_risk_estimation_improved_estimates_with_20260618.md` |
| 51 | GenericHandler | 2026-06-19 | `arxiv_econ_em_ramping_procurement_and_bid_cost_recovery_in_real_20260619.md` |
| 52 | GenericHandler | 2026-06-19 | `arxiv_econ_em_statistical_foundations_of_llm_based_a_b_testing_a_20260619.md` |
| 53 | GenericHandler | 2026-06-20 | `arxiv_econ_em_beyond_agent_architecture_execution_llm_trading_20260620.md` |
| 54 | RegimeFilterHandler | 2026-06-20 | `arxiv_econ_em_beyond_the_smile_a_hybrid_convolutional_vae_for_cr_20260620.md` |
| 55 | GenericHandler | 2026-06-20 | `arxiv_econ_em_continuous_cash_overlay_filters_growth_defensive_20260620.md` |
| 56 | GenericHandler | 2026-06-20 | `arxiv_econ_em_crashing_together_rallying_apart_dynamic_condition_20260620.md` |
| 57 | GenericHandler | 2026-06-20 | `arxiv_econ_em_do_prediction_markets_match_option_prices_bitcoin__20260620.md` |
| 58 | RegimeFilterHandler | 2026-06-20 | `arxiv_econ_em_macro_economists_machine_llm_commodity_etf_20260620.md` |
| 59 | GenericHandler | 2026-06-20 | `arxiv_econ_em_realtime_price_impact_detection_20260620.md` |
| 60 | GenericHandler | 2026-06-20 | `arxiv_econ_em_resolution_aware_perpetual_futures_polymarket_20260620.md` |
| 61 | GenericHandler | 2026-06-20 | `arxiv_econ_em_trading_in_the_sunshine_or_in_the_shade_market_imp_20260620.md` |
| 62 | RegimeFilterHandler | 2026-06-20 | `arxiv_econ_em_trends_volatility_correlations_and_critical_phenom_20260620.md` |
| 63 | RegimeFilterHandler | 2026-07-02 | `arxiv_econ_em_addressing_market_regime_changes_and_heavy_tailed__20260621.md` |
| 64 | GenericHandler | 2026-07-02 | `arxiv_econ_em_axiomatic_market_making_bid_ask_quoting_rule_20260621.md` |
| 65 | GenericHandler | 2026-07-02 | `arxiv_econ_em_bayesian_dynamic_modeling_realized_volatility_20260621.md` |
| 66 | GenericHandler | 2026-07-02 | `arxiv_econ_em_dexposure_claw_agentic_defi_risk_supervision_20260621.md` |
| 67 | GenericHandler | 2026-07-02 | `arxiv_econ_em_entropy_regularized_certainty_equivalent_bellman_pol_20260621.md` |
| 68 | GenericHandler | 2026-07-02 | `arxiv_econ_em_explicit_signal_adaptive_sequential_optimal_execut_20260620.md` |
| 69 | GenericHandler | 2026-07-02 | `arxiv_econ_em_fitting_accumulated_stock_returns_with_tempered_sk_20260620.md` |
| 70 | GenericHandler | 2026-07-02 | `arxiv_econ_em_forward_looking_stress_testing_under_macro_scenari_20260620.md` |
| 71 | GenericHandler | 2026-07-02 | `arxiv_econ_em_game_theoretic_modeling_of_heterogeneous_investor__20260620.md` |
| 72 | GenericHandler | 2026-07-02 | `arxiv_econ_em_hour_aware_adaptive_risk_management_for_autonomous_20260621.md` |
| 73 | GenericHandler | 2026-07-02 | `arxiv_econ_em_how_to_spot_outliers_an_ensemble_anomaly_detection_fr_20260621.md` |
| 74 | GenericHandler | 2026-07-02 | `arxiv_econ_em_incremental_svd_for_large_scale_dynamic_matrices_a_20260620.md` |
| 75 | GenericHandler | 2026-07-02 | `arxiv_econ_em_multiplicative_langevin_volatility_produces_observ_20260620.md` |
| 76 | GenericHandler | 2026-07-02 | `arxiv_econ_em_zero_copy_semantic_contagion_in_memory_streaming_f_20260620.md` |

*(doublon index : `quantocracy_sharpe_ratio_of_pure_noise_20260617.md` apparaît 2× → 77 entrées d'index pour 76 slugs.)*

---
*Plan généré le 2026-07-09. Aucun état modifié.*