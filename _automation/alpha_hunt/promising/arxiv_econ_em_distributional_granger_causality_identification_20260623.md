# Distributional Granger Causality: Testing Predictive Dependence Beyond the Conditional Mean

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.22230v1
**Captured**: 2026-06-23 03:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f377aaa642fc734e40ffab39758596b8

## Summary

Standard Granger causality tests only capture predictive content in the conditional mean, missing scale, tail, or asymmetry channels. This paper formalizes "distributional Granger causality" via a finite menu of channel-specific tests — covering mean, variance, skewness, tail behavior — and proves the menu is complete: distributional non-causality is equivalent to passing all channels simultaneously. The authors then build a sequential adaptive testing procedure with familywise error control via alpha-investing, which allocates inferential power across channels and provably matches an oracle that knows which channel matters. Finite-sample validity holds under arbitrary selection rules, using a circular-block permutation scheme compatible with short time series.

## Why it might be useful

This framework directly addresses a structural gap in CLAUDE.md's HAC/AMTP methodology: the current toolkit tests conditional mean IC (t-stat threshold 2.5, HAC lag-6), but funding-rate carry (Strategy B) and TSMOM (Strategy A) both have well-documented tail and variance predictability that mean-only tests miss. The L50 registry entry (funding extremes confirm momentum) was identified via percentile rank — a variance/tail channel — not mean Granger causality; this paper provides a formal testing framework to validate and quantify that channel. Concrete application: run distributional Granger tests on HL funding rates predicting BTC/ETH 8h returns across mean + variance + tail channels to separate which channels are statistically live (informing how aggressively to size Strategy B carry signals). The circular-block permutation is also directly compatible with the Politis-Romano block bootstrap already mandatory in CLAUDE.md, making integration clean. Most immediately useful for `_automation/feasibility/` gate A (IC feasibility) — adding a distributional channel test alongside mean IC would catch edges that die on mean but live on variance (e.g., vol-targeting signal refinements for Strategy D candidates).

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

High methodological value for gate A IC testing. Implementation cost: ~1-2 days to wrap the framework into `_automation/feasibility/` as a distributional IC handler alongside mean HAC. Not TEST_NOW because the feasibility gate pipeline would need refactoring, and no live strategy is currently blocked specifically on a tail-channel IC question.
