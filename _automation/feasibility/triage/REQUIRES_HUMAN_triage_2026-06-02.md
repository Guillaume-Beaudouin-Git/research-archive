# Triage REQUIRES_HUMAN — 2026-06-02

**Mission** : extraire de la file `_automation/feasibility/_state.json` (verdict
REQUIRES_HUMAN) une shortlist priorisée à tester PLUS TARD, sans backtest en masse
maintenant (anti-data-snooping, L2/L10/L20).

**Scope** : 75 items REQUIRES_HUMAN dans `_state.json` (run 2026-05-24 → 2026-06-01).
Categorisation handler GenericHandler/RegimeFilterHandler/ExitRuleHandler.

**Globals au moment du triage** :
- `n_tests = 321` (canonique CLAUDE.md research history)
- Live strategies : A FROZEN (Propr breach 2026-05-11), B HL testnet HMSTR seule, C BACKTEST-VALIDATED Tradeify $25K — paper NOT started, iter_10 invalidé sur 16 ans (memory 2026-06)
- Active research : D D3+D5 pré-registered (0/3 mods), Commodities XS (Phase A pending), Voie B FTMO (audit), CIP-EOQ FX, ZN Baltussen, sector_hothand audit en cours
- Coûts retenus : crypto 0.17% RT, futures MNQ ~$2.15 RT, FX 0.15% RT, commodity futures 0.015% RT

---

## Phase 0 — Inventaire (75 items)

**Verdicts par catégorie handler** (extrait de `_state.json` + reports `tested/*.md`) :

| Catégorie handler | Total |
|---|---|
| NON_TESTABLE (GenericHandler regex meta-framework) | 28 |
| COMPLEX (GenericHandler regex ML/regime infra) | 25 |
| REGIME_FILTER (RegimeFilterHandler hors scope) | 20 |
| EXIT_RULE (ExitRuleHandler hors scope) | 2 |

**Raison REQUIRES_HUMAN** : aucun handler ne sait tester directement → triage humain
obligatoire avant tout backtest (politique pipeline, cf. `handlers/generic_handler.py`
NON_TESTABLE_PATTERNS + COMPLEX_PATTERNS).

### Tableau récap (75 lignes, classé par catégorie / bucket)

| Slug | Catégorie | Bucket | Mécanisme (titre court) | Justif triage |
|---|---|---|---|---|
| `quantinsti_retrospective_simulation_for_trading` | COMPLEX | **BACKLOG** | Retrospective Simulation for Trading: Non-Parametric Brownian Bridge Path G | Brownian bridge generator pour trailing_dd_simulator; utile pour L22 calibration future. |
| `quantocracy_an_index_of_commodity_futures_returns_since_1871_q` | COMPLEX | **BACKLOG** | An Index of Commodity Futures Returns Since 1871 [Quantpedia] | Index commodity futures 1871 — augmenterait recherche XS active (xs_basis_tsmom); paywall Quantpedia. |
| `quantocracy_curve_trades_with_macroeconomic_signals_macrosyner` | COMPLEX | **BACKLOG** | Curve Trades with Macroeconomic Signals [Macrosynergy] | Curve/rates trades; pas d'accès aux futures rates/swap, infra absente. |
| `quantocracy_new_contributor_modeling_asymmetric_volatility_wit` | COMPLEX | **BACKLOG** | Modeling Asymmetric Volatility with EGARCH [Krzysztof Ozimek] | EGARCH vol pour A v4; A FROZEN, mod-1 candidat si dégèle. |
| `quantocracy_volatility_risk_premium_and_clustering_intraday_vs` | COMPLEX | **BACKLOG** | Volatility Risk Premium and Clustering: Intraday vs Overnight Dynamics [Rel | VRP intraday/overnight comme filtre régime Strategy C; L15 sous-seuil pour SR>1.0 mais à reconsidérer post iter_11 si SR baisse. |
| `quantpedia_active_dual_momentum_gtaa_strategy` | COMPLEX | **BACKLOG** | Active Dual Momentum GTAA Strategy | Absolute-momentum filter pour Strategy A v4; A FROZEN, mod-1 candidat si dégèle. |
| `arxiv_econ_em_option_pricing_under_stochastic_volatility_and_jum` | COMPLEX | **REJECT** | Option Pricing under Stochastic Volatility and Jumps: PIDE Framework with S | VRP archivé (L13 + SPX VRP IC neg). Modèle plus précis ne change pas l'économique. |
| `quantinsti_beyond_the_hype_what_independent_events_really_mea` | COMPLEX | **REJECT** | Beyond the Hype: What Statistical Independence Really Means for Trading Str | Background indépendance stat; HAC + AMTP déjà mandate. |
| `quantinsti_building_a_robust_portfolio_with_risk_parity` | COMPLEX | **REJECT** | Building a Robust Portfolio with Risk Parity | Outil ERC sizing; portfolio_state.py existe déjà, pas un signal. |
| `quantinsti_integrating_ai_and_quantitative_trading` | COMPLEX | **REJECT** | Integrating AI and Quantitative Trading — Python, QuantConnect, AWS Workflo | Infrastructure AI workflow; hors scope signal. |
| `quantinsti_statistical_arbitrage_using_cointegrated_stock_pai` | COMPLEX | **REJECT** | Statistical Arbitrage via Cointegrated Pairs — Indian Equity Market 2015-20 | Pairs cointegration equities archivé (0/19 qualif + Gatev SR=-0.44 par CLAUDE.md). |
| `quantocracy_active_dual_momentum_gtaa_strategy_quantpedia` | COMPLEX | **REJECT** | Active Dual Momentum GTAA Strategy (via Quantocracy) | Doublon de quantpedia_active_dual_momentum 2026-05-23 (même article). |
| `quantocracy_an_active_hedge_for_the_eur_investor_beyond_passiv` | COMPLEX | **REJECT** | An Active Hedge for the EUR Investor [Beyond Passive] | EUR hedging overlay; FX carry archivé + base USD. |
| `quantocracy_deep_learning_for_volatility_surface_repair_jonath` | COMPLEX | **REJECT** | Deep Learning for Volatility Surface Repair [Jonathan Kinlay] | Vol surface DL; aucune strat options. |
| `quantocracy_dual_momentum_allocation_between_physical_gold_and` | COMPLEX | **REJECT** | Dual Momentum Allocation Between Physical Gold and Bitcoin [Quantpedia] | GLD+BTC dual momentum: pre-flight L11 FAIL (gross 0.85%/yr < 3×cost 3%/yr crypto). |
| `quantocracy_reinforcement_learning_for_optimal_execution_jonat` | COMPLEX | **REJECT** | Reinforcement Learning for Optimal Execution [Jonathan Kinlay] | RL execution; échelle small-account, slippage négligeable vs signal. |
| `quantocracy_revisiting_beyond_60_40_five_decades_of_risk_weight` | COMPLEX | **REJECT** | Revisiting Beyond 60/40: Five Decades of Risk-Weighted Allocation [Beyond P | Sizing risk-parity; outil portfolio, pas un signal. |
| `quantocracy_selecting_taa_part1_based_on_recent_performance` | COMPLEX | **REJECT** | Selecting TAA Strategies Based on Recent Performance, Part 1 [Allocate Smar | Méta-sélection TAA; sans portefeuille multi-strat propfirm. |
| `quantocracy_selecting_taa_part2_recent_sharpe_ratio` | COMPLEX | **REJECT** | Selecting TAA Strategies Based on Recent Performance, Part 2: Recent Sharpe | Sharpe-based TAA selection; idem Part 1. |
| `quantocracy_selecting_taa_strategies_based_on_recent_performan` | COMPLEX | **REJECT** | Selecting TAA Strategies Based on Recent Performance: Series Overview [Allo | Vue d'ensemble série TAA; pas signal. |
| `quantocracy_the_metamorphosis_robot_wealth` | COMPLEX | **REJECT** | The Metamorphosis: Evolving Beyond Standard Pairs Trading | Pairs trading variant; pairs archivé (0/19 qualif). |
| `quantocracy_where_risk_parity_hurts_a_58_year_audit_of_tails_a` | COMPLEX | **REJECT** | Where Risk Parity Hurts: A 58-Year Audit of Tails and Drawdowns [Beyond Pas | Audit risk-parity; outil portfolio, pas un signal. |
| `quantpedia_dual_momentum_allocation_between_physical_gold_and` | COMPLEX | **REJECT** | Dual Momentum Allocation Between Physical Gold and Bitcoin (Digital Gold) | Doublon quantocracy_dual_momentum_gold_btc; fail L11 même chiffre. |
| `quantpedia_the_attention_factor_the_link_that_connects_crypto` | COMPLEX | **REJECT** | The Attention Factor: The Cross-Asset Link Between Crypto and Public Equity | Facteur attention; explication factorielle, pas signal exécutable. |
| `quantpedia_who_profits_from_prediction_markets` | COMPLEX | **REJECT** | Who Profits from Prediction Markets? | Prediction markets; hors scope strats. |
| `quantocracy_how_to_manage_an_intraday_trend_trade_concretum_gr` | EXIT_RULE | **CANDIDATE** | How to Manage an Intraday Trend Trade [Concretum Group] | Trailing-SL exit modification Strategy C (iter_11); 0 coût additionnel, modifie distribution exit. |
| `quantocracy_overfitting_and_parameter_selection_in_trading_str` | EXIT_RULE | **REJECT** | Overfitting and Parameter Selection in Trading Strategies [Relative Value A | Param sensitivity grid; outil méthodo (sensitivity analysis, pas signal). |
| `arxiv_econ_em_monetary_policy_in_the_media_spotlight_sentiments_` | NON_TESTABLE | **BACKLOG** | Monetary Policy in the Media Spotlight: Sentiments, Signals, and Economic I | Sentiment NLP central bank; pipeline NLP non disponible (closed FGVD L17 + Wiki L18 déjà couvre les low-infra paths). |
| `arxiv_econ_em_tweedie_s_formula_variance_functions_and_score_dri` | NON_TESTABLE | **BACKLOG** | Tweedie's Formula, Variance Functions, and Score-Driven Updating (v1) | GAS-GARCH vol pour Strategy A vol estimator; A FROZEN, à reconsidérer si A unfreeze. |
| `arxiv_econ_em_tweedies_formula_and_score_driven_updating` | NON_TESTABLE | **BACKLOG** | Tweedie's Formula and Score-Driven Updating (v2) | Doublon Tweedie v2 — GAS vol pour A; A FROZEN. |
| `quantocracy_lazy_prices_lazy_investors_and_the_22_alpha_hidden` | NON_TESTABLE | **BACKLOG** | Lazy Prices, Lazy Investors — and the 22% Alpha Hidden in 10-Ks [Quantt] | Edge 10-K NLP equities; nécessite pipeline 10-K + univers actions, hors infra. |
| `arxiv_econ_em_algometrics_forecasting_under_algorithmic_feedback` | NON_TESTABLE | **REJECT** | Algometrics: Forecasting Under Algorithmic Feedback | Méthodo feedback algorithmique; pas un signal directement testable. |
| `arxiv_econ_em_double_descent_and_benign_overfitting_in_macroecon` | NON_TESTABLE | **REJECT** | Double Descent and Benign Overfitting in Macroeconomic Forecasting | Méthodo overfitting; pas un signal — sentence: STRATEGY_RESEARCH_LOG ne le contient pas mais L20 DSR couvre déjà l'angle. |
| `arxiv_econ_em_heavy_tails_and_predictive_ability_testing` | NON_TESTABLE | **REJECT** | Heavy Tails and Predictive Ability Testing | Outil diagnostique HAC alternatif; pas un signal. Pourrait alimenter un audit interne — non prioritaire. |
| `arxiv_econ_em_lgb_a_macroeconomic_forecasting_road_test` | NON_TESTABLE | **REJECT** | LGB+: A Hybrid Linear-Tree Boosting Algorithm for Macroeconomic Forecasting | LGB pour forecasting macro; pas un signal de trading direct. |
| `arxiv_econ_em_quantifying_the_risk_return_tradeoff_in_forecastin` | NON_TESTABLE | **REJECT** | Quantifying the Risk-Return Tradeoff in Forecasting | Forecast eval framework; outil de validation, pas signal. |
| `arxiv_econ_em_rolling_origin_conformal_prediction_under_local_st` | NON_TESTABLE | **REJECT** | Rolling-Origin Conformal Prediction under Local Stationarity and Weak Depen | Calibration prédictive non-stat; outil méthodo, pas signal. |
| `arxiv_econ_em_saga_a_sequence_adaptive_generative_architecture_f` | NON_TESTABLE | **REJECT** | SAGA: Decoder-Only Transformer for Multi-Horizon Probabilistic Forecasting  | Microsimulation labor econ; off-topic complet. |
| `arxiv_econ_em_self_normalized_tests_for_multistep_conditional_pr` | NON_TESTABLE | **REJECT** | Self-Normalized Tests for Multistep Conditional Predictive Ability | Alternative HAC; outil méthodo, pas signal. |
| `hn_algotrading_ask_hn_algorithmic_trading_for_hackers` | NON_TESTABLE | **REJECT** | Ask HN: Resources for Algorithmic Trading (Programmer-Oriented) | Faux-positif scraper (titre HN, pas de contenu signal). |
| `hn_quant_launch_hn_promoted_yc_w21_search_and_feed_ranking_` | NON_TESTABLE | **REJECT** | Launch HN: Promoted (YC W21) — ML-Powered Search and Feed Ranking for Marke | Faux-positif scraper (e-commerce ML, hors scope). |
| `quantocracy_a_century_without_data_reconstructing_emerging_mar` | NON_TESTABLE | **REJECT** | A Century Without Data: Reconstructing Emerging Markets Equity History [Qua | EM equities hors infra; sans accès paywall Quantpedia. |
| `quantocracy_a_day_is_now_what_a_decade_used_to_be_tommi_johnse` | NON_TESTABLE | **REJECT** | A Day Is Now What a Decade Used to Be [Tommi Johnsen] | Méta-commentaire sur l'accélération de l'info, pas de signal. |
| `quantocracy_agentic_workflows_for_alpha_research_jonathan_kinl` | NON_TESTABLE | **REJECT** | Agentic Workflows for Alpha Research [Jonathan Kinlay] | Design de workflow IA; concerne _automation/, pas un signal. |
| `quantocracy_backtests_lie_building_a_stress_test_framework_for` | NON_TESTABLE | **REJECT** | Backtests Lie: Building a Stress-Test Framework for ML Trading Signals | Cadre stress-test; outil méthodo (Portfolio/risk/trailing_dd_simulator.py couvre déjà). |
| `quantocracy_for_the_love_of_the_game_robot_wealth` | NON_TESTABLE | **REJECT** | For The Love of The Game [Robot Wealth] | Philosophique anti-data-mining; aligné avec CLAUDE.md max 3 mods. |
| `quantocracy_how_to_break_a_financial_sentiment_model_without_c` | NON_TESTABLE | **REJECT** | How to Break a Financial Sentiment Model Without Changing What It Means [To | Robustesse adverse sentiment; pas applicable (aucun signal NLP actif). |
| `quantocracy_martyn_tinsley_beyond_the_backtest_algorithmic_adv` | NON_TESTABLE | **REJECT** | Martyn Tinsley – Beyond the BackTest [Algorithmic Advantage Podcast] | Podcast réflexion live vs backtest; pas signal. |
| `quantocracy_quant_mashup_homepage` | NON_TESTABLE | **REJECT** | Quantocracy Quant Mashup (Feed Homepage) | Artéfact RSS homepage. |
| `quantocracy_quantocracy_homepage` | NON_TESTABLE | **REJECT** | Quantocracy Feed Homepage | Artéfact RSS homepage. |
| `quantocracy_research_review_24_april_2026_prediction_markets_c` | NON_TESTABLE | **REJECT** | Research Review \| 24 April 2026: Prediction Markets and BTC/ETH Derivatives | Digest prediction-markets crypto; pas applicable. |
| `quantocracy_sentiment_is_not_one_signal_tommi_johnsen` | NON_TESTABLE | **REJECT** | Sentiment is Not One Signal [Tommi Johnsen] | Désagrégation sentiment; pas de pipeline NLP actif. |
| `quantocracy_the_currency_you_didn_t_choose_beyond_passive` | NON_TESTABLE | **REJECT** | The Currency You Didn't Choose [Beyond Passive] | Risque base-currency (EUR); strats actuelles USD only. |
| `quantocracy_the_effective_number_of_tested_strategies_vertox_q` | NON_TESTABLE | **REJECT** | The Effective Number of Tested Strategies [Vertox Quant] | Effective-N correction AMTP; outil méthodo (L20 DSR déjà mandate). |
| `quantpedia_a_century_without_data_reconstructing_emerging_mar` | NON_TESTABLE | **REJECT** | A Century Without Data: Reconstructing Emerging Markets Equity History | EM equities reconstruction; hors infra, doublon quantocracy_a_century. |
| `quantocracy_identifying_stocks_to_fade_concretum_research` | REGIME_FILTER | **BACKLOG** | Identifying Stocks to Fade | Equities fade univers; hors infra trading (sector_hothand actif mais audit en cours, t_HAC=10.38 red flag). |
| `quantocracy_rethinking_trend_following_optimal_regime_dependen` | REGIME_FILTER | **BACKLOG** | Rethinking Trend Following: Optimal Regime-Dependent Allocation [Alpha Arch | Regime-dependent TSMOM sizing; Strategy A FROZEN, mod candidat si dégèle. |
| `quantocracy_surfing_the_equity_curve_using_trend_following_to_` | REGIME_FILTER | **BACKLOG** | "Surfing the Equity Curve": Using Trend-Following to Switch Strategies On a | Equity curve trend filter pour Strategy A v4; A FROZEN. |
| `quantocracy_unsupervised_learning_for_trading_k_means_pca_pyth` | REGIME_FILTER | **BACKLOG** | Unsupervised Learning for Trading: K-Means, PCA & Python Examples [Quant In | K-Means clustering NQ pré-marché pour Strategy C; L15 sous-seuil (SR_DSR(C) ~1.1), à reconsidérer si C SR baisse. |
| `quantocracy_why_momentum_investing_has_been_struggling_and_wha` | REGIME_FILTER | **BACKLOG** | Why Momentum Investing Has Been Struggling — And What Volatility Has to Do  | Vol-spike filter pour Strategy A v4; A FROZEN. |
| `quantpedia_commodity_portfolio_strategy_for_a_potential_2026_` | REGIME_FILTER | **BACKLOG** | Commodity Portfolio Strategy for a Potential 2026 Inflationary and Supply S | Régime inflationniste 2026 commodities; alimente xs_basis_tsmom phase B (active research). |
| `quantpedia_quantpedia_awards_2026_winners_announcement` | REGIME_FILTER | **BACKLOG** | Quantpedia Awards 2026 — Winners Announcement | Curated list Quantpedia winners 2026; à lire pour scan ad-hoc (méta-tâche, pas signal). |
| `arxiv_econ_em_regime_based_portfolio_allocation_using_hidden_ma` | REGIME_FILTER | **CANDIDATE** | Regime-Based Portfolio Allocation via 3-State HMM and Reinforcement Learnin | 3-state HMM + RL pour Strategy D; L15-aligné. Doublon mécanisme avec quantinsti_market_regime_hmm — converge sur même protocole. |
| `quantinsti_market_regime_using_hidden_markov_model` | REGIME_FILTER | **CANDIDATE** | Market Regime Detection with Hidden Markov Models and Random Forest Signals | HMM 3-state régime filter pour Strategy D D3+D5; L15-aligné (D3 SR=-1.08, D5 SR=-1.32 → SR<0.7 cible idéale). |
| `quantocracy_when_short_sellers_create_overnight_alpha` | REGIME_FILTER | **CANDIDATE** | When Short Sellers Create Overnight Alpha — Concretum Group | FINRA daily short volume → signal NQ overnight (nouveau axis); article complet requis avant pré-registration. |
| `arxiv_econ_em_multi_regime_markov_switching_models_with_time_var` | REGIME_FILTER | **REJECT** | Multi-Regime Markov-Switching Models with Time-Varying Transition Probabili | TVTP Markov-switching yields; R-only + complexité > infra Python actuelle. |
| `arxiv_econ_em_partial_identification_of_causal_effects_that_vary` | REGIME_FILTER | **REJECT** | Partial Identification of Causal Effects That Vary by Setting | Causal inference partial ID; méthodo, pas signal. |
| `arxiv_econ_em_the_harmonic_synthetic_control_method` | REGIME_FILTER | **REJECT** | The Harmonic Synthetic Control Method | Synthetic control method; econometrics policy eval, pas signal trading. |
| `quantinsti_epat_project_dynamic_capital_allocation_using_mark` | REGIME_FILTER | **REJECT** | Dynamic Capital Allocation via Market Breadth and Random Forest Regime Dete | Random Forest + market breadth allocation; complexité > bénéfice attendu pour Strategy D. |
| `quantocracy_ai_forex_backtesting_with_llm_regime_labels_deepse` | REGIME_FILTER | **REJECT** | AI Forex Backtesting with LLM Regime Labels: DeepSeek vs K-Means in Python  | LLM regime labels FX; FX archivé (FX-1 à FX-4 + Strategy E). |
| `quantocracy_bad_month_for_your_strategy_should_you_change_it_a` | REGIME_FILTER | **REJECT** | Bad Month for Your Strategy? Should You Change It? [Alvarez Quant Trading] | Méta-décision modification vs patience; pas signal. |
| `quantocracy_martyn_tinsley_walk_forward_correlation_a_new` | REGIME_FILTER | **REJECT** | Walk Forward Correlation: A New Robustness Metric for Strategy Design — Mar | Metric WFC; outil de validation, pas signal. |
| `quantocracy_most_of_the_insider_trading_alpha_is_gone_by_the` | REGIME_FILTER | **REJECT** | Insider Trading Alpha Decays Before the SEC Filing Is Public — Tommi Johnse | Insider trading alpha post-decay; valide la non-pertinence sans nécessiter test. |
| `quantocracy_volatility_derivatives_and_vix_market_dynamics_rel` | REGIME_FILTER | **REJECT** | Volatility Derivatives and VIX Market Dynamics [Relative Value Arbitrage] | Background VIX; VIX term carry archivé + L15. |
| `quantpedia_an_index_of_commodity_futures_returns_since_1871` | REGIME_FILTER | **REJECT** | An Index of Commodity Futures Returns Since 1871 | Doublon quantocracy_an_index_commodity_futures_1871. |

---

## Phase 1 — Triage en 3 bacs

| Bac | Compte | % | Définition |
|---|---|---|---|
| **REJECT** | 54 | 72% | pas un signal tradable / doublon archivé / outil méthodo / pre-flight fail |
| **BACKLOG** | 17 | 23% | signal plausible mais bloqué (data payante, classe d'actif non infra, ou strat parent FROZEN) |
| **CANDIDATE** | 4 | 5% | testable avec infra existante (NQ engine + crypto loaders + backtest_wf) |

### Croisement catégorie × bucket

| Catégorie | REJECT | BACKLOG | CANDIDATE |
|---|---|---|---|
| NON_TESTABLE | 24 | 4 | 0 |
| COMPLEX      | 19 | 6 | 0 |
| REGIME_FILTER| 10 | 7 | 3 |
| EXIT_RULE    | 1 | 0 | 1 |

### Lecture honnête

- **72% REJECT** — la grande majorité des REQUIRES_HUMAN sont des articles méthodo,
  artefacts RSS, ou doublons d'idées déjà fermées (FX archivé n=181, Crypto archivé
  n=159, Equities ETF GTAA archivé). Résultat attendu et **correct** : le pipeline a
  fait son travail de pré-filtre, mais sa propre régex laisse passer beaucoup de bruit
  méta-méthodologique qu'il faut écarter manuellement.
- **23% BACKLOG** — signaux plausibles bloqués par : (a) data payante (Glassnode,
  Quantpedia history, 10-K NLP) ; (b) classe d'actifs non couverte (EM equities,
  options surfaces, rates futures) ; (c) **strat parent FROZEN** (A → 5 BACKLOG, à
  reconsidérer si A dégèle).
- **5% CANDIDATE** — quatre fiches détaillées Phase 2, dont deux convergent sur la
  même mécanique (HMM Strategy D) → **3 idées distinctes**.

### Note sur les BACKLOG « Strategy A FROZEN »

5 items (`arxiv_tweedie v1/v2`, `quantocracy_egarch`, `quantpedia_active_dual_momentum`,
`quantocracy_rethinking_trend_following`, `quantocracy_surfing_equity_curve`,
`quantocracy_why_momentum_struggling`) sont tous des **mods candidates v4 pour Strategy
A**. Le contrat 3-mod max (L10) impose un classement avant de débloquer A — à faire
DANS un mission Strategy A v4 dédiée, pas dans ce triage.

---

## Phase 2 — Fiches CANDIDATE (analyse, pas de backtest)

> **Méthodologie** : pour chaque candidate, mécanisme + qui-est-de-l'autre-côté,
> orthogonalité estimée, pre-flight L11/L11b/L12, event-count, faisabilité.
> Si une fiche échoue le pre-flight, elle est reclassée REJECT ici.

### Fiche C1 — Strategy C : Trailing-SL exit modification (variant iter_11)

**Source** : `quantocracy_how_to_manage_an_intraday_trend_trade_concretum_gr_20260523.md`
(EXIT_RULE handler, hors scope iter_05 baseline).

**Spec gelée a-priori** :
- Signal d'entrée identique iter_10 (ORB 09:30-09:45, VWAP conf, gap<1.2%, range≥30pts, $400 SL cap)
- Modification exit : trailing SL au lieu de TP fixe à 1.5R
  - Step 1 : SL initial = min(0.5R, 20pts) — identique iter_10
  - Step 2 : si prix atteint +1R, déplacer SL à BE+1tk
  - Step 3 : si prix atteint +1.5R, démarrer trail SL = high − 0.5R (long) / low + 0.5R (short)
  - Step 4 : time stop 12:30 ET inchangé
- Compteur modification : +1 vs iter_10 (= **iter_11**)

**1. Mécanisme économique**
Les exits à TP fixe coupent le runner avant que la queue droite de la distribution ne
se développe. Le mécanisme du *trailing* est que sur les jours où le drift directionnel
post-ORB est fort, le runner peut faire 2-3R avant retournement ; sur les jours où il
stalle à 1R, le BE-move protège le capital. Counter-party : les traders qui paient un
prime de certitude (fixed-TP). Le edge n'est PAS arbitré parce que c'est un choix de
gestion de risque idiosyncratique, pas une information.

**2. Orthogonalité vs A/B/C**
Même signal d'entrée que C iter_10 → **corr(P&L_iter_11, P&L_iter_10) ≈ 0.7** estimée
(même hits, distribution exit différente). vs A/B : ≈ 0 (assets, fréquences disjointes).
**Faible nouveauté de signal** ; gain attendu = path management, pas alpha.

**3. Pre-flight L11/L11b**
- Pas de nouveaux trades : N_trades ≡ N_iter_10 ≈ 87/an (sur 2022-2025, signal_freq~16%/jour)
- Cost drag : inchangé (mêmes RT par trade : $2.15 MNQ)
- **L11b binary TP/SL gate** : E[gross/trade] doit être > 3×cost/trade. iter_10 gross≈$84/trade, cost≈$4.30 → ratio≈19.5 ✓ (déjà passé par iter_10 ; iter_11 ne dégrade pas mécaniquement)
- **Verdict pre-flight** : PASS (trivialement — pas d'augmentation de coût)

**4. Event-count**
N ≈ 87/an (compte cohérent avec iter_10 baseline). Au-dessus du plancher de puissance
stat (50/an). En-dessous du plafond d'overflow de coûts L12. ✓

**5. Faisabilité technique**
- Engine : `Futures/research/active/nq_intraday/engine.py` (NQBacktestEngine) supporte
  déjà TP/SL mult ; trailing logic à ajouter dans `compute_trade_pnl()` (≈30 lignes)
- Data : `data/cache/Dataset_NQ_1min_2022_2025.csv` local, déjà utilisé par iter_10
- Effort : 1 jour (impl + WF 5-fold + DSR n_trials=11)
- **Compteur mods C** : iter_10 → iter_11 = 1 mod consommée

**6. Caveat L20/L24 explicites**
- L20 DSR : Bailey-LdP avec N_trials=11 (iter_01..iter_11), T=756d → SR_DSR ≈ SR × 0.62
  Si iter_11 raw SR ≤ 1.6, DSR < gate 1.0 → FAIL. Marge fine.
- L24 propfirm fit : iter_10 est intrinsèquement « lumpy » (WR 27.75%, win/loss 3.7×)
  → propfirm structurally ceiling 44-54% p(pass). Le trailing-SL ne change pas la
  symétrie de la barrière. **Ne pas espérer un saut de p(pass)** — espérer une
  redistribution de la queue droite.
- Memory `orb_pushpass_2026-06` : K5 (V2+E7+floor_taper+vol_high) atteint p_funded
  100% OOF WF-selected mais DSR per-trade FAILS. Le gain de K5 est gestion-de-chemin,
  pas edge. **iter_11 trailing-SL relève du même mécanisme — risque de retomber sur le
  même piège DSR**.

**Verdict Phase 2** : **CANDIDATE faible-confiance**. Path management déjà exploré
(memory ORB push-pass). Gain attendu marginal, risque DSR-fail réel.

---

### Fiche C2 — Strategy D : HMM 2-state régime filter sur D3+D5 portfolio

**Sources convergentes (mécanique identique)** :
- `quantinsti_market_regime_using_hidden_markov_model_20260523.md` (Python tutorial)
- `arxiv_econ_em_regime_based_portfolio_allocation_using_hidden_ma_20260530.md` (académique)

**Spec gelée a-priori** :
- Base : portefeuille D3 + D5 1/1 pondéré (entry rules pré-registered dans
  `Futures/research/active/strategy_d/hypotheses_preregistered.md`)
- Régime classifier : **HMM 2-state** (trending/mean-reverting) fitté sur NQ daily features
  - Features : (a) 5-day realized vol, (b) 20-day momentum, (c) intraday range / overnight range
  - Fitting : in-fold uniquement (refit chaque fold du WF) — **interdit refit full-sample**
- Mapping régime → strat :
  - Si régime classé « trending » → activer D5 seul (BB squeeze breakout)
  - Si régime classé « mean-reverting » → activer D3 seul (ORB mid-fade)
- Compteur modification : +1 vs D3+D5 baseline (= **D mod 1/3**)

**1. Mécanisme économique**
D3 (mid-fade 09:45-11:00) fonctionne quand le marché se range autour du VWAP ; D5 (BB
squeeze breakout 14:00-15:30) fonctionne quand le marché trend l'après-midi. Les deux
profils sont anti-corrélés en régime → trader les deux unconditionally moyenne les
edges ; trader chacun **conditionnellement** au régime capture l'edge pur.
Counter-party : les traders qui n'observent pas le régime (i.e., qui appliquent la
même stratégie tous les jours). Pourquoi pas arbitré : régime classification n'est
pas commodity — HMM avec choix de features a un edge de modélisation idiosyncratique.

**2. Orthogonalité vs A/B/C**
- D3 corr_C = −0.21, D5 corr_C = −0.05 (CLAUDE.md) → D3+D5 portfolio corr_C ≈ −0.13
- HMM-filtered D3+D5 : corr_C devrait rester < 0.2 (même profil intraday décorrélé)
- corr A/B ≈ 0 (assets, fréquences disjoints)
- **Bonne orthogonalité** confirmée par la pré-registration Strategy D.

**3. Pre-flight L11/L11b**
- Coût : MNQ $2.15 RT, NQ engine déjà calibré
- **L15 explicit check** : « regime overlays useful only for SR<0.7 strategies ».
  D3 SR = −1.08, D5 SR = −1.32, D3+D5 SR à mesurer (espéré dans [0, 0.5] post-combinaison
  via décorrélation). **L15-aligné** : on est exactement dans la zone où le régime filter
  apporte un lift > seuil.
- Cost drag : N_trades réduit par filter (≈ moitié). Gain net = activation ciblée.
- **Verdict pre-flight** : PASS (subject to mesure D3+D5 baseline d'abord).

**4. Event-count**
- D3 base : ~80/an (1 trade par jour signal-éligible)
- D5 base : ~50/an
- D3+D5 unconditional : ~130/an
- HMM-filtered (1 régime actif par jour) : ~65-80/an → **proche plancher 50/an**.
  ⚠ Risque de manque de puissance stat sur folds courts.

**5. Faisabilité technique**
- HMM via `hmmlearn` (déjà installable)
- NQ 1-min data local
- Effort : 3-4 jours (HMM fit per-fold + remap labels + WF + DSR + sanity checks)
- **Risque look-ahead** : si HMM features incluent indicateurs non-stationnaires, le
  refit per-fold peut produire des labels qui « anticipent » les régimes futurs. Doit
  être audité avec shuffle null test.
- Compteur mods D : 1/3 (D budget intouché actuellement)

**6. Caveat L15/L20 explicites**
- L15 : sub-threshold lift sur SR>1.0 strategies (Δ ≈ +0.022%/day = +5.5%/yr). Ici la
  base D3+D5 est probablement SR ∈ [0, 0.5], donc on attend lift de magnitude
  comparable. Gate RESEARCH_PASS (SR>0.7) atteignable si baseline SR > 0.2.
- L20 DSR : N_mod_D=1, T=1000d → correction ≈ 0.92 (faible). Marge OK.
- **Look-ahead test obligatoire** (mécanique HMM remapping per-fold).

**Verdict Phase 2** : **CANDIDATE haute-confiance** — bonne aligned-L15, mécanique
testable, infra présente, orthogonalité forte avec A/B/C/iter_10.

---

### Fiche C3 — NQ overnight signal via FINRA daily short volume

**Source** : `quantocracy_when_short_sellers_create_overnight_alpha_20260531.md`
(Concretum Group, série article 2/2 — body of article NON encore extracted)

**Spec gelée a-priori (sous réserve article complet)** :
- Input data : FINRA Regulation SHO daily short volume (public, gratuit)
  http://regsho.finra.org/regsho-Index.html
- Agrégation : panier QQQ top-N constituents (N=100 typique) → short_volume_concentration_index_t
- Signal candidat (à confirmer par article) :
  - Si short_volume_concentration_t > 90th percentile (rolling 252d) → SHORT NQ overnight close-to-open
  - Si < 10th percentile → LONG NQ overnight
  - Sinon → flat
- Hold : 1 night (close 16:00 → open 09:30 next day)
- Compteur : NEW STRATEGY (Strategy E candidate) — n_tests += 1 niveau A puis += 3 niveau B

**1. Mécanisme économique**
Hypothèse Concretum : concentration intraday de short selling sur composantes QQQ laisse
un short interest élevé fin de journée. Couverture forcée overnight (margin) ou rebalance
indices → direction prévisible. Counter-party : market makers qui ne hedgent pas leur
inventaire short overnight, traders retail qui ne suivent pas les flux institutionnels.
Edge persistance : FINRA short volume a une latence de J+1 ; institutionnels avec
prime broker data ont l'edge t+0, mais l'edge J+1 sur close→open est potentiellement
résiduel.

**2. Orthogonalité vs A/B/C**
- vs A (crypto TSMOM monthly) : ≈ 0
- vs B (HL carry 8h) : ≈ 0
- vs C (NQ intraday 09:46-12:30) : ≈ 0.05-0.20 (zones temporelles disjointes ; close-to-open ≠ ORB)
- vs D (NQ intraday) : ≈ 0.05-0.20
- **Très bonne orthogonalité** — nouvelle axe overnight, nouvel input data.

**3. Pre-flight L11/L11b — CRITIQUE**
- Coût per trade NQ overnight : $2.15 RT MNQ + slippage close→open ≈ $4-6 retail
- Volatilité overnight NQ : σ ≈ 0.30%/night → annualisée σ ≈ 4.8%
- **Selective gate** (binary L11b) :
  - Si signal selective (top/bot 10% percentile) → ~50 trades/an
  - E[gross/trade] doit être > 3 × cost/trade ≈ $15
  - Cela exige conditional E[|move|] > 0.075% post-cost → IC implied ≈ 0.025 minimum
  - **Plausible mais pas garanti** — l'article doit fournir IC numérique
- Si signal dense (daily) → 252 trades/an
  - Cost drag annuel ≈ 252 × $4 / contract = $1008 / contract ; vs σ_target $4800/contract
  - Cost / σ = 21% — au seuil ; OK seulement si IC ≥ 0.10 (rare overnight)
- **Verdict pre-flight** : INCERTAIN. Pre-registration doit conditionner sur article.

**4. Event-count**
- Selective (top/bot 10%) : ~50/an → au plancher
- Dense daily : 252/an → bien au-dessus
- Compromis : selective top/bot 20% → ~100/an, raisonnable

**5. Faisabilité technique**
- FINRA Reg SHO data : scraping daily CSV (free, public, archive 2009+)
- QQQ constituents : nasdaq.com daily ou yfinance ETF holdings
- NQ overnight OHLC : Dataset_NQ_1min déjà local, agrégation close-16:00 → open-09:30
- Effort : 5-7 jours (data ETL FINRA + ETL constituents historiques + signal construction + WF)
- **Risque #1** : constituents QQQ ont changé sur 15 ans → backtesting nécessite survivorship-corrected constituents (sinon biais)
- **Risque #2** : couplage equities short → NQ futures n'est pas 1:1, le transfert mécanique doit être validé

**6. Caveat L23/L23b explicites**
- L23 vibe : « régulatory window kill » s'applique aux fixings/auctions. FINRA Reg SHO
  est règlementaire mais n'a pas subi de réforme depuis ~2010. **OK sur L23**.
- L23b : edge HFT-medié vs retail. Concretum suggère mécanisme institutionnel ;
  retail accède via FINRA J+1 data. **Pre-flight retail-tier obligatoire** avant test.

**Verdict Phase 2** : **CANDIDATE incertitude élevée**. Mécanisme plausible, data
gratuite, orthogonalité forte ; mais pre-flight conditionnel à lecture article + risque
mécanique transfer equities→futures.

---

## Phase 3 — Shortlist priorisée + 3 protocoles pré-enregistrés

### Scoring qualitatif

| Critère | C1 trailing-SL C iter_11 | C2 HMM régime D3+D5 | C3 FINRA NQ overnight |
|---|---|---|---|
| Force mécanisme | ●○○ (path mgmt, déjà exploré) | ●●○ (régime classique aligné L15) | ●●○ (institutional flow, plausible) |
| Orthogonalité   | ○○○ (corr≈0.7 vs iter_10)    | ●●○ (corr≈−0.13 vs C)            | ●●● (nouveau axe overnight) |
| Faisabilité     | ●●● (1j, engine prêt)         | ●●○ (3-4j, HMM in-fold delicate) | ●○○ (5-7j + risque transfer) |
| Marge pre-flight| ●●● (trivial, 0 coût ajouté)  | ●●● (NQ futures cheap)           | ●○○ (incertain, dépend article) |
| **Score** | **9** | **10** | **8** |

**Ordre proposé** :
1. **C2 — HMM régime filter Strategy D D3+D5** (haute confiance, L15-aligné)
2. **C1 — Strategy C trailing-SL iter_11** (faible coût, faible upside)
3. **C3 — FINRA short volume NQ overnight** (haut upside, haute incertitude)

---

### Protocole pré-enregistré P1 (C2) — HMM régime filter D3+D5

**Hypothèse exacte**
Le portefeuille D3+D5 1/1 pondéré sur NQ intraday, filtré par un HMM 2-state daily
(trending vs mean-reverting), produit un Sharpe OOS > 0.7 avec MaxDD < −25% et WF
positivity > 50% (gate RESEARCH_PASS). Si le portefeuille non-filtré (baseline mesuré
en pré-flight) atteint déjà ce seuil, alors l'effet de filtration doit ajouter un
delta_SR > 0.10 avec p(delta ≤ 0) < 0.05 (paired bootstrap, NeweyWest lag-6).

**Spec figée a-priori**
- Univers : NQ 1-min (Dataset_NQ_1min_2022_2025.csv + extension 2022-2026 si dispo)
- Period IS : 2010-01-01 → 2018-12-31 (8 ans, ~2016 jours trade)
- OOS : 2019-01-01 → 2023-12-31 (5 ans, ~1260 jours trade)
- Holdout : 2024-01-01 → 2026-04-30 (2.3 ans, never-seen pre-paper)
- **Aucune optimization sur OOS, aucun look au holdout avant le rapport final**

**Signal D3** (figé, depuis `Futures/research/active/strategy_d/hypotheses_preregistered.md`) :
- ORB mid-fade 09:45-11:00 ET
- Entry conditions identiques à la pré-registration (à ne pas modifier ici)

**Signal D5** (figé, depuis pré-registration) :
- BB squeeze breakout 14:00-15:30 ET
- Entry conditions identiques

**Régime HMM** :
- Library : hmmlearn 0.3+
- Features (computed at t-1 close, signal at t) : `[vol_5d, mom_20d, range_intra_t-1 / range_overnight_t-1]`
- States : K=2 (trending=1, mean-reverting=0) — pas de K-sweep
- Fit policy : refit on rolling 504-day window, lock parameters for next 21 trading days
- Label remap : per fold, identify state with higher mean-mom_20d as « trending »
- Activation rule :
  - state==trending → trade D5 only
  - state==mean-reverting → trade D3 only

**Gates**
- RESEARCH_PASS : Sharpe_OOS > 0.7, MaxDD > −25%, WF positivity > 50%, DSR > 0.05, bootstrap_p < 0.10
- PROPFIRM_PASS : Sharpe_OOS > 1.0, MaxDD > −10%, WF positivity > 60%, DSR > 0.10
- L15 ADD : delta_SR(filter − baseline) > 0.10, paired bootstrap p(delta ≤ 0) < 0.05

**n_tests incrémental honnête**
- Pre-flight (D3+D5 unfiltered baseline mesurer) : +1 (n=322)
- HMM filter test niveau A (IC + orthogonalité) : +1 (n=323)
- Niveau B (WF + bootstrap + DSR) : +3 (n=326)
- Niveau C (sanity) : +0 (sanity = robustness check, n_tests non-incrémenté par convention pipeline)
- **TOTAL pour cette idée : n_tests passe 321 → 326 (= +5)**

**Critère d'arrêt / kill**
- Si baseline D3+D5 unfiltered Sharpe > 0.7 → L15 inapplicable (sub-threshold lift) → STOP, archiver comme « D3+D5 standalone OK »
- Si baseline D3+D5 SR < 0 → la filtration ne sauvera pas, signal-level problem → STOP, archiver D3+D5
- Si HMM régime labels switchent > 30% des jours dans le fold (instabilité) → STOP, HMM mal calibré
- Si DSR < 0.05 avec n_trials_D=1 → STOP, signal pas distinct du hasard

**Compteur mods Strategy D** : 1/3 consommée (HMM filter = mod 1)

**Artefact écrit** : `Futures/research/active/strategy_d/preregistration_hmm_filter_2026-06.md`

---

### Protocole pré-enregistré P2 (C1) — Strategy C trailing-SL iter_11

**Hypothèse exacte**
Sur Dataset_NQ_1min 2010-2026, la modification iter_11 (TP fixe 1.5R → trailing-SL au
high − 0.5R après atteinte de 1R, BE-move à 1R, time stop 12:30 ET inchangé) produit
un Sharpe OOS > iter_10 baseline avec delta_SR > 0.10, p(delta ≤ 0) < 0.05 (paired
bootstrap), tout en maintenant DSR > 0.05 sous N_mod=11.

**Spec figée a-priori**
- Univers : NQ 1-min 2010-01-01 → 2026-04-30 (16 ans, ≈4000 jours trade)
- Period IS : 2010-2018 (9 ans)
- OOS : 2019-2023 (5 ans)
- Holdout : 2024-2026-04 (2.3 ans, never-touched)

**Signal d'entrée** : iter_10 exact (figé)
- ORB 09:30-09:45 → entry 09:46 ET
- VWAP confirmation
- Gap < 1.2%
- Opening range ≥ 30 pts
- $400 SL cap

**Modification exit (iter_11)**
- SL initial = min(0.5R, 20 pts)  [identique iter_10]
- À +1R atteint : SL → BE + 1 tick
- À +1.5R atteint : trailing SL = high − 0.5R (long) / low + 0.5R (short)
- Time stop : 12:30 ET (identique iter_10)
- Pas de TP fixe (différence iter_10 qui clôturait à +1.5R)

**Gates**
- RESEARCH_PASS : Sharpe_OOS > 0.7, MaxDD > −25%, WF positivity > 50%, DSR > 0.05
- PROPFIRM_PASS : Sharpe_OOS > 1.0, MaxDD > −10%, WF positivity > 60%, DSR > 0.10
- ADD : delta_SR(iter_11 − iter_10) > 0.10 sur la même fenêtre data, bootstrap p < 0.05

**n_tests incrémental honnête**
- Pre-flight test iter_11 vs iter_10 baseline : +1 (n=322)
- Niveau B (WF + bootstrap + DSR avec N_trials=11, T=4000d) : +3 (n=325)
- **TOTAL : 321 → 325 (= +4)**

**Critère d'arrêt / kill**
- Si iter_11 SR ≤ iter_10 SR → STOP (modification ne paie pas)
- Si DSR < 0.05 sous N_mod=11 → STOP (trop de modifications, marge stat insuffisante)
- Si MaxDD iter_11 > 1.5 × MaxDD iter_10 → STOP (trailing introduit variance non rentable)
- Si p_funded propfirm < 50% sur Monte Carlo Tradeify $25K → STOP (échec L24)

**Compteur mods Strategy C** : iter_10 → iter_11 (10 → 11). Marge DSR critique sur ≥10 mods.
**⚠ Important** : selon `Strategy C iter_10 validation 2026-06` (memory), iter_10 a déjà
été invalidé sur 16 ans (Sharpe 0.51, p_pass 24%, LONG-only edge). iter_11 doit prouver
qu'il restore la viabilité — sinon **archiver C et passer à Strategy D / E**.

**Artefact écrit** : `Futures/research/active/nq_intraday/preregistration_iter11_trailing_2026-06.md`

---

### Protocole pré-enregistré P3 (C3) — FINRA short volume → NQ overnight (Strategy E candidate)

**Phase 0 obligatoire AVANT pre-flight** :
- Lire le full article Concretum Group (paywall ? alternative ?) — extraire spec exact
- Si article n'a pas spec numérique → STOP cette idée, retourner à BACKLOG
- Si article confirme univers actions (not futures) → reformuler sur QQQ overnight
  proxy, valider mécanisme transfer NQ ensuite

**Hypothèse exacte (conditionnelle Phase 0)**
La concentration de short volume FINRA daily sur les 100 plus gros constituents QQQ
(survivorship-corrected) prédit le sens de la session overnight NQ futures (close 16:00 →
open 09:30 next day), avec IC > 0.05 t_HAC > 2.5 sur N ≥ 50 events/an post-filtre top/bot
10% percentile.

**Spec figée a-priori (sous réserve Phase 0)**
- Univers : NQ futures continuous front (CME) — overnight session close 16:00 ET → open 09:30 next day
- Period IS : 2010-01-01 → 2018-12-31
- OOS : 2019-01-01 → 2023-12-31
- Holdout : 2024-01-01 → 2026-04-30

**Construction signal**
- Données : FINRA Reg SHO daily short volume CSV (par ticker)
- Constituents QQQ : à reconstruire historiquement (Wikipedia + nasdaq.com ETF holdings,
  survivorship-corrected)
- short_vol_concentration_t = Σ (short_vol_i,t / total_vol_i,t × weight_i,QQQ) pour top 100
- Signal :
  - Si short_vol_concentration_t > 90th percentile rolling 252d → SHORT NQ close→next-open
  - Si < 10th percentile → LONG NQ close→next-open
  - Sinon → flat

**Pre-flight gate (à passer AVANT niveau A)**
- Confirmer Phase 0 + IC > 0.025 minimum sur sample IS
- L11b binary gate : E[gross/trade] > 3 × cost/trade ($4-6 MNQ overnight)
- Event count ≥ 50/an post-filter (top/bot 10%)

**Gates**
- RESEARCH_PASS : Sharpe_OOS > 0.7, MaxDD > −25%, WF positivity > 50%, DSR > 0.05
- PROPFIRM_PASS : Sharpe_OOS > 1.0, MaxDD > −10%, WF positivity > 60%, DSR > 0.10
- ADD : IC_t_HAC > 2.5 (HAC lag-6 sur séries daily)

**n_tests incrémental honnête**
- Phase 0 lecture article : +0 (pas de test stat)
- Pre-flight IC test (FINRA → NQ overnight) : +1 (n=322)
- Niveau A IC + orthogonalité : +1 (n=323)
- Niveau B WF + bootstrap + DSR : +3 (n=326)
- **TOTAL : 321 → 326 (= +5)** — identique à C2 par hasard

**Critère d'arrêt / kill**
- Phase 0 : article sans spec numérique → STOP
- Pre-flight IC < 0.025 → STOP (mécanisme pas réplicable à partir de FINRA J+1)
- Pre-flight event count < 50/an post-filter → STOP (sous plancher puissance stat)
- L11b binary gate fail → STOP
- Niveau A FAIL → STOP, archiver POSTMORTEM (Strategy E candidate fermé)

**Compteur strat** : NEW Strategy E candidate. 0 mod consommée (signal-level test).

**Artefact écrit** : `Futures/research/active/strategy_e_finra_overnight/preregistration_2026-06.md`
+ `Futures/research/active/strategy_e_finra_overnight/_phase0_article_extract.md`

---

## Annexe — Items BACKLOG par déblocage requis

| Bloquant | Items concernés | Action déblocage |
|---|---|---|
| Strategy A FROZEN | tweedie v1/v2, egarch, active_dual_momentum, rethinking_trend_following, surfing_equity_curve, why_momentum_struggling | Dégeler A (décision propfirm) → mission dédiée Strategy A v4 |
| Data payante | quantpedia_commodity_1871 (×2), lazy_prices 10-K, central bank sentiment, quantpedia_awards_2026 winners | Budget Glassnode/Quantpedia/Tiingo Plus, ou abandon |
| Equities universe | identifying_stocks_to_fade (sector_hothand audit en cours, t_HAC red flag) | Résolution audit sector_hothand → décision go/nogo equities |
| L15 sub-threshold filter (C SR>1.0) | k_means_pca_NQ, vrp_intraday_overnight | Reconsidérer si iter_11 ratio Sharpe baisse < 0.7 |
| Rates futures access | curve_trades_macro | Hors infra ; reporter post-déploiement broker rates |
| trailing_dd_simulator L22 | retrospective_simulation Brownian bridge | Intégrer dans Portfolio/risk si MC sim Tradeify/Apex à raffiner |
| Commodities XS Phase B | commodity_portfolio_2026 | Compléter Phase A xs_basis_tsmom avant |

---

## Annexe — Items REJECT (54) — récapitulatif par sous-motif

| Motif rejet | Compte |
|---|---|
| Outil méthodo / methodologie pure (HAC alt, conformal, DSR effective-N, etc.) | 14 |
| Doublons / RSS artefacts (homepages, articles déjà capturés) | 7 |
| Famille archivée (FX, pairs, VRP, GTAA-ETF, sentiment) | 16 |
| Hors infra trading (vol surface DL, RL execution, NLP sentiment central bank) | 9 |
| Pre-flight L11/L11b FAIL (gold-BTC dual momentum) | 1 |
| Faux-positifs scraper (HN Ask threads, YC marketplaces) | 2 |
| Méta-décision / philosophie | 5 |

---

## Synthèse honnête

- **Sur 75 REQUIRES_HUMAN, 3 idées distinctes méritent un test futur pré-enregistré** :
  P1 (HMM régime Strategy D), P2 (Strategy C trailing-SL iter_11), P3 (FINRA short
  volume Strategy E candidate).
- **P1 est la plus prometteuse** : L15-aligné, infra présente, orthogonalité forte.
- **P2 est marginal** : path management sur strat déjà fragile (iter_10 invalidé 16-ans),
  risque DSR-fail sous N_mod=11.
- **P3 est haut-upside / haute-incertitude** : nouvelle axe data gratuite, mais
  dépend de spec article + risque transfer mécanique equities→futures.
- **Total n_tests si TOUS testés** : 321 → 336 (+15) — gérable.
- **Recommandation ordre** : P1 (semaine 1), P2 (parallèle), P3 (lecture article +
  décision phase 0 d'abord). NE PAS lancer en bloc 3 backtests = data snooping.

**Compteur honnête de cette session triage** : 0 backtest lancé, 0 n_test consommé.
Les n_tests prévus n'incrémentent que **si et quand** les protocoles sont exécutés.

---

*Triage produit 2026-06-02 par session Claude Code "max effort" — file `_automation/feasibility/triage/REQUIRES_HUMAN_triage_2026-06-02.md`*
