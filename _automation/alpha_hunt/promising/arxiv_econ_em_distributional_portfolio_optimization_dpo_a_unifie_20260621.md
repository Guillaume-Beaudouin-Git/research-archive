# DPO: Unified Framework for Distributional Portfolio Optimization

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.30464
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: dcfd95e159048edf68af6b15833673f9

## Summary
A unifying theoretical framework for portfolio methods where weights, returns, and parameters can all be modeled as probability measures (the "distributional portfolio optimization" DPO framework). The joint coupling Γ_θ(dw,dr) connects Bayesian, robust, chance-constrained, stochastic-allocation, and distributional RL portfolio methods. Key technical results: a portfolio specialization of Wasserstein-CVaR duality, a static no-randomization theorem, a Bayesian credible-radius calibration of Wasserstein DRO, and a distributional Bellman contraction for RL. Empirically, the credible-radius calibration (vs Ledoit-Wolf shrinkage, equal-weight, no-view BL) lands within 3-7bp of oracle tail risk on K=25 DJIA backtest.

## Why it might be useful
The credible-radius calibration result is directly relevant to our ERC methodology in `Portfolio/risk/propfirm_canonical.py`: instead of assuming a point estimate for ρ_AB, treating the correlation as a probability measure (with a credible radius based on sample uncertainty) would give more robust risk allocation. With only ~60 days of live B testnet fills and historical A fills, the credible radius around ρ_AB=0.039 is wide — probably ±0.3, which materially affects optimal allocation. The Ledoit-Wolf comparison result (within 3-7bp) suggests Ledoit-Wolf shrinkage is a practical approximation that already captures most of the DRO benefit. Already potentially implemented in existing propfirm_canonical.py — check if covariance shrinkage is applied there.

## Extracted content
"A controlled experiment shows that across factor models at K in {10,25,50}, the credible-radius rule lands within 3-7 bp of the oracle out-of-sample tail risk and beats a 24-month validation-tuned radius while spending no validation data."

"Equal-weight, no-view Black-Litterman, and Ledoit-Wolf shrinkage attain [compared performance]."

No code in excerpt. Full paper has implementation details.

## Action proposed
REFERENCE

Theoretical unification of portfolio methods. The practical implication (use Ledoit-Wolf shrinkage as DRO approximation) may already be implemented in propfirm_canonical.py — check before implementing anything new. Revisit when portfolio B mainnet launches and more data is available for robust covariance estimation.
