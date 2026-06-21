# Modeling Dynamic Correlation Matrices with Shrinkage Priors

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.06818
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: a7806277b9911a8a6ca2335487f30c43

## Summary
A Bayesian low-rank factor model for time-varying correlation matrices where latent states evolve under a dynamic shrinkage prior and observation errors follow a multivariate factor stochastic volatility model. The key contributions are: (1) locally adaptive regularization that tightens around stable periods and loosens during structural breaks; (2) the first posterior contraction theorem for dynamically regularized Bayesian models, showing convergence at an explicit rate under averaged Hellinger distance; (3) a total-correlation scalar measure of cross-sectional dependence derived from information theory. Applied to monitoring equity portfolio correlations during market stress, showing changing diversification benefits in backtesting.

## Why it might be useful
The multi-asset A+B book has current correlation ρ_AB=0.039 (full-sample ERC), but this is a static estimate. When Strategy B launches on mainnet (~July 2026), measuring dynamic correlation between A and B becomes operationally important for ERC rebalancing in `Portfolio/state/portfolio_state.py`. The total-correlation scalar is a one-number summary of cross-sectional dependence, more informative than a pairwise correlation for 3+ asset books. The paper's stress-period focus directly addresses the portfolio recalc observation that "MaxDD book: à mesurer sur ≥60j live B mainnet" — the dynamic shrinkage prior would reveal whether the historical ρ_AB=0.039 compresses or explodes during risk-off events, which is the key unknown for the portfolio book (current MaxDD unresolved because B backtest has 92% zeros). Compare against existing ERC methodology in `Portfolio/risk/propfirm_canonical.py`.

## Extracted content
"We build on the information-theoretic concept of total correlation to obtain a scalar measure of cross-sectional dependence."

"We establish, to our knowledge, a first-of-its-kind posterior contraction result for dynamically regularized Bayesian models, showing contraction around the true model parameters at an explicit rate under averaged Hellinger distance."

No code or formulas in excerpt. Full paper needed.

## Action proposed
TEST_LATER

After B mainnet launch (~July 2026): apply the total-correlation scalar to rolling 30-day windows of A+B daily returns to detect correlation regime shifts. Simpler first step: implement dynamic DCC (DCC-GARCH with Ledoit-Wolf initialization) on current live B testnet + A daily fills, which is 2-3x faster than the full Bayesian model and covers the portfolio monitoring use case. LATER because B mainnet not yet live; revisit after 30 days of mainnet fills.
