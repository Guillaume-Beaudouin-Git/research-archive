# Two Sides of Schur Damping: Portfolio Allocation and High-Dimensional Statistics

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.14798
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d9f8424169dffbc003ac82670453a941

## Summary
Spatial statisticians and quantitative investors have independently derived the same Schur complement structure — as conditional covariance in Vecchia pseudo-likelihoods and as residual risk net of hedge in portfolio allocation. A single damping parameter interpolates between hierarchical risk parity and mean-variance, with consistency proofs for both estimation contexts.

## Why it might be useful
The A+B book ERC calculation degenerates because Strategy B has 92% zero-return days (CLAUDE.md: solveur ERC série dégénère). The Schur-damped allocator interpolates between HRP (robust to degenerate covariance) and MV (optimal when covariance is well-estimated) — a direct solution to the current ERC instability. Concrete test: implement on the A+B daily return panel with varying damping parameter, check if the resulting allocation is more stable than ERC across different estimations of ρ_AB. 1-2 days with numpy. TEST_LATER pending Strategy B mainnet returns.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Implement Schur-damped allocator as alternative to ERC for A+B book; test on current degenerate B-series; 1-2 days, numpy available.
