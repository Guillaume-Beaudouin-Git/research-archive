# Embedding Foundation Model Predictions in Discrete-Choice Models with Structural Guarantees

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.26432v1
**Captured**: 2026-06-26 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d289ceba43ffc46d86692cf5889ce2dd

## Summary
This paper proposes a two-stage adapter for injecting foundation model predictions into a multinomial logit utility framework while preserving economic constraints like cost monotonicity. Stage 1 fits the logit's structural coefficients via constrained maximum likelihood; Stage 2 freezes those coefficients and adds a small neural correction on top of the foundation model's output. The composition guarantees that the marginal rate of substitution (willingness-to-pay) is analytically computable, rather than being an empirical artifact. Across three datasets and two foundation models, the adapter gains 6.4 percentage points of test accuracy on average over baseline logit, while maintaining 100% cost monotonicity.

## Why it might be useful
Peripheral relevance only. The paper targets consumer choice modeling (transportation, revealed preferences), not financial markets. The methodological insight — using a neural correction layer on top of a constrained structural model to preserve economic constraints — is conceptually applicable to the `_automation/feasibility/` pipeline where you want ML-predicted feasibility scores to respect known constraints (e.g., a strategy's Sharpe must exceed a gate threshold, not just be predicted to). However, the current pipeline uses deterministic L0/L1/L2 rules, not trained models, so this is a future consideration if the pipeline evolves toward learned scoring. No immediate application.

## Extracted content
Author claims:
> "The adapter gains 6.4 percentage points (pp) of test accuracy on average over the multinomial logit and up to 12.8 pp, maintains 100% cost monotonicity, and produces values of time within the published transportation-economics range."

No code or financial performance claims.

## Action proposed
REFERENCE — Consumer choice modeling methodology. No trading application at current pipeline maturity.
