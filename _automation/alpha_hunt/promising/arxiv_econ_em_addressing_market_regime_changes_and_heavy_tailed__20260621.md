# BAVAR-BLED: Regime-Aware Portfolio Optimization with Fat-Tailed Returns

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.09104
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: c54094d1c0af8b3d46999d82ce64bd63

## Summary
A deep reinforcement learning portfolio optimizer (BAVAR-BLED) that combines Bayesian-Averaged Vector Autoregression (for multi-scale regime-aware return/covariance forecasts) with a Black-Litterman model adapted for Student-t distributions (for fat-tail-resilient allocation), embedded in a TD3 RL architecture. Evaluated on 29 DJIA constituents over a decade, reporting Sharpe 1.72 and Sortino 2.70, total return 57.26%. The key contribution is that the BAVAR component produces time-varying prior estimates for the BL views, allowing the allocation to adapt when regimes shift, while the Student-t distribution in BLED accounts for fat tails that normal-distribution BL models ignore.

## Why it might be useful
The Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) is working with 24 continuous contracts where heavy tails and regime shifts are significant concerns — commodity futures exhibit fat-tailed returns, especially at monthly rebalancing. The BAVAR multi-scale forecasting for covariance is directly applicable to the Phase A (data fetch + roll validation) pipeline: using lagged cross-sectional variance estimates as BL views would be a step up from the current rolling vol-targeting approach. The Sharpe 1.72 on DJIA over a decade is suspicious at face value (L20 DSR applies: one model, multiple hyperparameters in TD3), but the BAVAR covariance shrinkage component is the relevant methodological contribution, independent of the RL wrapper. The Student-t BL formulation also addresses the fat-tail issue identified in Strategy A's vol targeting (log returns, 28-bar window) during extreme crypto drawdowns.

## Extracted content
"BAVAR captures a set of vector autoregressive representations that consider multi-scale temporal features, enabling adaptive allocation decisions based on regime-aware estimates of return expectations and dispersion matrices. These estimates serve as prior inputs to BLED, a model that uses Student's t-distributions, allowing for more realistic fat tail return estimates."

The authors claim Sharpe 1.72 and Sortino 2.70 on DJIA, 29 constituents, "over a decade-long market period."

No code or formulas in excerpt. Full paper needed for BAVAR architecture.

## Action proposed
TEST_LATER

Extract only the BAVAR component (ignore TD3 wrapper): implement multi-scale VAR with Bayesian model averaging as covariance prior for Commodities XS. Cost: 2-3 days. Prerequisite: complete Phase A of `xs_basis_tsmom/` first. LATER because Commodities XS is still in Phase A, and the DRL wrapper adds implementation complexity disproportionate to the likely marginal gain over simpler shrinkage (compare against Ledoit-Wolf first, then BAVAR).
