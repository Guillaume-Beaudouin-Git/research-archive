# From Vector Autoregressions to AI-based Time Series Forecasting: A Review

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.14279v1
**Captured**: 2026-07-17 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b136ba74bc14e8c2ac3ae8f8257282cf

## Summary
A review connecting classical VAR-based econometric forecasting to modern AI forecasting methods (transformers, large pretrained zero-shot models, diffusion-based generative forecasters), framed around a shared object — the conditional distribution of the future given the past — and organized around three persistent challenges: high dimensionality, nonstationarity, and nonlinearity. Argues modern methods progress by loosening the classical template (richer dynamics, larger training sets, richer predictive distributions) but typically lack the inferential/structural tooling (significance testing, causal structure) that makes classical models useful for explanation and policy analysis, not just point forecasts.

## Why it might be useful
Directly relevant background for the project's own methodology stance — Algo_claude's hard rules privilege HAC-tested, walk-forward-validated, interpretable signals over black-box forecasts precisely because, per this review, modern AI forecasters trade away the inferential tooling needed to trust an OOS claim. Useful context next time a candidate strategy proposes a transformer/diffusion forecaster (e.g., c65d91a1's Bitcoin regime-fusion model, filed elsewhere in this batch) and needs to be checked against the walk-forward/HAC/AMTP discipline rather than judged on raw predictive metrics alone. Second link: relevant to `_automation/synthesis/` (weekly cross-paper synthesis) as a framing document — a review like this is exactly the kind of source theme-tracking synthesis should index against, since it maps the landscape several other arxiv_econ_em papers in this same batch (ridge regression, factor loadings, mixed-frequency learning) sit inside.

## Extracted content
No code/formulas, no numeric claims — qualitative review paper.

## Action proposed
REFERENCE.
