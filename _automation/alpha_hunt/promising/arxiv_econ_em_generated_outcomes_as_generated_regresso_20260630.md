# Generated Outcomes as Generated Regressors: Equivalences in Recursive Causal Estimation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.29009v1
**Captured**: 2026-06-30 02:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 0a85022ced88b3083531c373a3f8c6c8

## Summary
This paper establishes a formal equivalence between three recursive causal estimators (plug-in, balancing-weight, doubly-robust) when each stage is fit by OLS — they coincide exactly in any finite sample regardless of model misspecification. The analysis covers settings where one stage's predicted values become the dependent variable for the next stage (mediation, time-varying treatment, surrogate estimation). Under ridge penalization, the doubly-robust estimator reduces to a backward recursion whose OLS weight decays geometrically with the number of time steps, meaning the cross-sectional bias-toward-OLS intuition becomes progressively weaker in the time-series dimension.

## Why it might be useful
The direct trading relevance is limited, but there is one concrete connection: multi-step signal pipelines where a predicted quantity from one model feeds into another (e.g., using predicted volatility from a GARCH model as input to a TSMOM sizing formula) are exactly the "recursive generated-regressor" setting this paper formalizes. Strategy A's vol-targeting (log returns, 28-bar window) already chains predictions — if the volatility estimate were replaced with a two-stage ML predictor, standard OLS SE inference would break exactly as described here. The methodology lesson is: whenever a signal pipeline has ≥2 sequential prediction steps, standard t-stats on the final stage are likely too optimistic; use HAC SE at each stage independently (already L8 practice) and be aware that ridge penalization in upstream stages shifts the effective estimator away from OLS downstream.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
