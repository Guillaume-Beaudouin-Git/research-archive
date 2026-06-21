# Conditional Reverse Stress Testing: Reconstructing Full-Path Scenarios from a Single Shock

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.09274
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a171fffceeb18808e21d3491dc51e518

## Summary
Reverse stress testing traditionally identifies scenarios that cause a portfolio to breach a loss threshold, but constructing multivariate scenarios coherent with empirical dependence structure from a single prescribed shock is methodologically underdeveloped. This paper formulates the problem as maximizing the conditional density given an imposed shock on one asset class, solving it under three assumptions of decreasing restrictiveness: parametric Gaussian, empirical copula, and fully non-parametric inference. All three produce full stressed time-series paths rather than static covariance shocks, enabling time-series-compatible scenario generation. A practical demonstration reconstructs a 2020-March-style stress scenario from a prescribed S&P 500 drop.

## Why it might be useful
This methodology is directly applicable to the propfirm drawdown simulator in `Portfolio/risk/trailing_dd_simulator.py`: instead of using a Gaussian or trade-based generator, the reverse stress testing framework could identify which specific market scenarios (S&P 500 drop of X% while BTC moves Y%) cause Strategy A+B portfolio to breach the MAX_TOTAL_DD=5.5% guardrail in `execution/__init__.py:47`. For Strategy B (delta-neutral carry on HL), the empirical copula approach would capture the non-Gaussian dependence between HMSTR funding rates and broader crypto vol, which is exactly the tail risk that matters for the mainnet deployment decision around 2026-07-17. The full-path scenario output (not static shock) is particularly valuable for testing the kill switch logic against realistic correlated stress paths.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Full-path stress scenario generation for `Portfolio/risk/trailing_dd_simulator.py` is a concrete enhancement; implement after Strategy B mainnet deployment decision since the correlated stress path analysis would directly inform MAX_DAILY_DD parametrization.
