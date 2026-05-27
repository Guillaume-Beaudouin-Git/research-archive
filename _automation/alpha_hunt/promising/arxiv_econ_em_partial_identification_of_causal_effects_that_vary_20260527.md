# Partial Identification of Causal Effects That Vary by Setting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.25483v1
**Captured**: 2026-05-27 12:08 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: acf10c4c55dfcb6fa7539e76ecefd03b

## Summary
When estimating the same causal effect across many distinct settings, natural experiments (quasi-experiments) are often available only in some settings while others rely on selection-on-observables (conditional independence). This paper shows that pooling omitted-variable-bias information across settings sharpens the jointly identified set of causal effects, even when conditional independence fails. The method is valuable precisely when standard quasi-experimental identification is infeasible across the full sample — it provides a principled way to narrow bounds rather than point-identify.

## Why it might be useful
The "metrics" L1 match reflects genuine methodological relevance. In strategy research, this framework maps to the problem of estimating signal IC across multiple market regimes or asset classes when clean identification is only possible in some (e.g., only in trending regimes for TSMOM, or only in specific funding-rate environments for Strategy B). The most concrete application would be: Strategy D D3+D5 portfolio research — both strategies failed individually (Sharpe -1.08/-1.32) and a regime filter is under study. Partial identification could formalize the argument that the regime filter is warranted without overfitting: if the effect of the fade signal is partially identified in low-volatility regimes, tighter bounds there could justify regime-conditional activation. Implementation would require reading the full paper and adapting the multi-setting pooling estimator to time series; this is a 2-3 day project and requires the right regime partition.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
