# Tweedie's Formula, Variance Functions, and Score-Driven Updating (v1)

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.15902v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: dbce7cade93100715c7409cbfcc565c3

## Summary
Score-driven (GAS) models update time-varying parameters by taking steps proportional to the score of the conditional log-likelihood. This paper provides a Bayesian interpretation of this update rule using Tweedie's formula: in the Gaussian case, the inverse-Fisher-scaled score update is exactly the posterior mean correction. For natural exponential families, analogous identities apply in both natural-parameter and expectation-parameter spaces. Under local precision discounting, the predictive covariance becomes proportional to inverse Fisher information, recovering the standard GAS recursion. The paper distinguishes when score updates are exact Bayesian filters versus local approximations.

## Why it might be useful
The GAS/score-driven framework is applicable to Strategy A's volatility targeting: the current 28-bar rolling standard deviation is a simple but non-adaptive estimator. A GAS-GARCH(1,1) vol model would update volatility estimates proportionally to forecast errors, adapting faster to regime changes (e.g., post-FOMC or crypto-market shock vol spikes) than the fixed 28-bar window. This paper's Bayesian interpretation provides formal grounding for why GAS is a principled replacement — it is the exact Bayesian filter under Gaussian noise. Note: Strategy A is currently FROZEN (Propr breach), so this modification cannot be deployed until a new propfirm is engaged. A v2 revision of this paper exists (`arxiv_econ_em_tweedies_formula_and_score_driven_updating_20260527.md`) with a cleaner exposition; see that entry for the primary reference.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Theoretical backing for GAS-based vol updating. See v2 entry for more complete exposition. Applicable to Strategy A v4 vol estimation as modification #1 toward 3-mod cap, but Strategy A is currently FROZEN.
