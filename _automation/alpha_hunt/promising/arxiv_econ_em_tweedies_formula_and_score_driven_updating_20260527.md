# Tweedie's Formula and Score-Driven Updating (v2)

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.15902v2
**Captured**: 2026-05-27 12:08 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d5f21cc5504a51d575690048a88a7bb4

## Summary
Version 2 of the paper previously captured as v1 on 2026-05-23. The paper gives a Bayesian interpretation of score-driven (GAS) models by connecting their parameter-update rule to Tweedie's formula. In the Gaussian case, Tweedie's formula implies that the inverse-Fisher-scaled score update is exactly the posterior mean correction. For natural exponential families, analogous identities characterize posterior means in both parameter spaces. Under local precision discounting, the predictive covariance becomes proportional to inverse Fisher information, recovering the exact GAS update rule. The v2 revision appears to tighten the exposition; the core results are unchanged from v1.

## Why it might be useful
Score-driven models (GAS, Dynamic Conditional Score) are directly applicable to Strategy A's daily volatility targeting: the 28-bar log-return rolling vol used in the tanh signal could be replaced by a GAS-based dynamic volatility filter that is formally Bayesian-optimal under the chosen observation density. This would also affect Strategy C (NQ ORB): the 63d rolling std vol targeting could be upgraded. The CLAUDE.md mandatory fix #3 (daily vol targeting: 63d rolling std × √252) is correct but a GAS model would adapt faster to regime changes (e.g., post-FOMC volatility spikes). However, an entry for v1 (`arxiv_econ_em_tweedie_s_formula_variance_functions_and_score_dri_20260523.md`) already exists in promising/ and was marked REFERENCE. No additional action needed beyond the prior entry; the main update in v2 is presentational.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Supersedes the v1 entry from 2026-05-23. Read the full paper before replacing the rolling-vol methodology in Strategy A or C; GAS upgrade is a modification that counts against the 3-mod budget (L10).
