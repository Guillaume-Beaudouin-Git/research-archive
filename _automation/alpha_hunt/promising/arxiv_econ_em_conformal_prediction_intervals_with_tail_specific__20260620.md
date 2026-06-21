# Conformal Prediction Intervals with Tail-Specific Guarantees

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.18199
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 089590c5778fc18329b0380df88ba22c

## Summary
Split conformal prediction is extended to produce intervals with calibrated coverage separately for each tail rather than only as a global average. Lower and upper one-sided conformal intervals are constructed independently, then intersected to form two-sided intervals that provably satisfy both tail-specific and overall marginal coverage guarantees. The framework is generalized beyond the exchangeable setting to covariate shift, covering distribution-shifted test environments.

## Why it might be useful
Strategy A's walk-forward Sharpe (1.33 OOS) is reported as a point estimate with no formal coverage bounds on the lower tail — the propfirm gate (Sharpe>1.0) requires knowing the lower-tail confidence interval. For Strategy D's pre-registration (Futures/research/active/strategy_d/hypotheses_preregistered.md), the tail-specific framework directly maps to the asymmetric gate structure (MaxDD<-10% is a hard left-tail constraint, Sharpe>1.0 is a right-tail constraint). Conformal intervals are distribution-free and do not require block-length selection, complementing the Politis-Romano block bootstrap mandated in CLAUDE.md. Concrete test: wrap the sector_hothand_propfirm walk-forward loop with split conformal bounds on Sharpe, providing a formal lower-tail 95% CI on performance.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Wrap Strategy D walk-forward Sharpe estimates in split conformal bounds; 1-2 days, directly applicable to pre-registration uncertainty quantification.
