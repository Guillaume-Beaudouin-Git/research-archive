# Nonlinear Filtering with Stochastic Discontinuities

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.12142
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 6ceb047560fc553f

## Summary
A general nonlinear filtering framework is developed for systems with jumps in both signal and observation, modeled as marked point processes. The paper derives Kushner-Stratonovich-type equations for the conditional distribution, establishes robustness results, and provides a particle filter implementation with convergence guarantees. Prior literature handled only linear systems or specific jump structures.

## Why it might be useful
Nonlinear filtering with jumps is theoretically relevant to real-time state estimation in volatile markets (e.g., detecting regime switches in Strategy D's NQ research, or credit events). However, this paper remains entirely in the theoretical PDE/SDE domain with no numerical financial applications. The particle filter convergence result is too abstract to directly inform Algo_claude's regime-detection work (where Inspectable Neural Markov Models, paper #20, is more directly applicable).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
