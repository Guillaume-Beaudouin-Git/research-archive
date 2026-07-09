# Relevance triage of the 77 purged false-FAIL_A — 2026-07-09

**But** : trier les 77 (ex-faux FAIL_A, ré-ouverts dans `promising/`) **par pertinence/
utilité**, avant d'en attaquer un. **Découverte préalable** : ce sont des **extraits
scrapés tronqués**, pas des specs backtestables — chaque `.md` s'arrête avant les
empiriques (« Full article needed »). « Backtester le premier » n'a donc pas de sens tel
quel : il faut d'abord transformer une *idée* en *spec pré-enregistrée*. Ce triage
identifie lesquelles valent cette transformation.

## Tiers (relevance × testabilité-sur-infra × orthogonalité × fit-focus)

### TIER 2 — TESTABLE MAINTENANT sur infra existante → **à attaquer** (1 idée distincte)
| Item(s) | Mécanisme | Pourquoi testable maintenant | Route |
|---|---|---|---|
| `dual_vs_single_momentum_in_commodities` (06-15) **+** `dual_vs_single_momentum_commodities` (06-17, doublon) | XS relative-momentum rank **+** filtre trend absolu (flat si sous son propre trend) | Spécifiable **sans article** (construction standard type Antonacci) ; **données déjà fetch** (24 futures continus 2005-26, Phase A faite) ; mensuel = coût-safe (L11) ; **c'est la Phase B de `xs_basis_tsmom`** (axe actif) | INVEST LONG / diversifier perso (orthogonal crypto). **PAS FTMO** (mensuel lumpy, mismatch barrière symétrique L24) |

→ **GAGNANT**. Seul item qui coche testable-maintenant **ET** pertinent. Caveat honnête :
prior sceptique (momentum XS commodités **décayé post-2015**, documenté ; version ETF
archivée L5). L'« evidence neuve » qui justifie d'y retoucher = la **claim de robustesse
paramétrique** du dual-momentum (≠ perf brute).

### TIER 1 — TRADABLE mais BLOQUÉ (spec possible, mais data/article/famille) → référence
| Item | Blocage | Verdict |
|---|---|---|
| `holiday_seasonality_part_2` (06-02) | besoin liste jours fériés (article) ; pensé pour **C annulé** ; calendaire lumpy (L24) | fetch article si un jour ; basse prio |
| `trend_following_filters_part_10` (05-31) | besoin article ; overlay trend → sur **A gelé** | bloqué (A frozen + article) |
| `dividend_timing_global_dividend_premium` (06-17) | besoin Compustat (dividendes globaux) | data-bloqué ; perso-equity si un jour |
| `do_prediction_markets_match_option_prices_bitcoin` (06-20) | besoin Polymarket + Deribit | data-bloqué ; **crypto = perso**, à noter |
| `institutions_return_expectations_across_assets` (06-02) | données d'enquête (survey) | data-bloqué |
| `continuous_cash_overlay_filters_growth_defensive` (06-20) | rotation défensive/cash-overlay, vague ; adjacent GTAA (clos) | reference |

### TIER 0 — PAS UN SIGNAL TRADABLE (~65) → REJECT (le classifieur les a laissés passer)
Regroupés par famille (le pipeline devrait auto-rejeter ceux-là, pas les « tester ») :
- **Économétrie/estimation** (~20) : debiased estimators, panel VAR, granular IV, causal
  forecasting, covariate transition, consumer demand, nonlinear factor models, tempered-skew
  fitting, incremental SVD, Langevin volatility, Bayesian realized-vol, DCC correlations…
- **Méthodo/overfitting/métriques** (~12) : sharpe stability, **sharpe of pure noise ×2**,
  crossword of fitting, UFC fitting championships, honey-shrunk-weights, VaR estimation,
  feature selection, factor zoo, return-contribution analysis…
- **LLM/AI-meta** (~8) : AI overfitting, evaluating AI strategies, right way to use AI,
  macro-economists-machine LLM ETF, LLM A/B testing, beyond-agent-architecture, agentic DeFi…
- **Microstructure/exécution/market-making** (~7) : price-impact detection, sunshine/shade
  market impact, optimal execution, axiomatic market making, hour-aware risk mgmt, entropy Bellman…
- **Risk models / vol-surface / éconophysique** (~8) : resga tail-risk, scale-ordered contagion,
  beyond-the-smile VAE, trends-vol-correlations critical phenomena, stress testing, anomaly detection…
- **Infra/RSS/pub/niche** (~10) : toy TPU, IV solver, build-infrastructure, Quantpedia updates ×3,
  Quantpedia days offer, testing-AI-workflow, procurement/electricity ×2, SpaceX IPO, Polymarket perps…

## Conclusion
Sur 77 : **~65 ne sont pas des signaux** (à auto-rejeter, pas à tester — ils n'auraient
jamais dû compter comme un « test »), **~6 tradables mais bloqués** (data/article/famille close),
**1 idée distincte testable + pertinente maintenant** : le **dual-momentum commodités**.
→ On attaque celui-là, via la **Phase B de `xs_basis_tsmom`**, avec pré-enregistrement d'abord.

---
*Triage lecture-seule, 2026-07-09. Rien backtesté, n_tests intouché.*
