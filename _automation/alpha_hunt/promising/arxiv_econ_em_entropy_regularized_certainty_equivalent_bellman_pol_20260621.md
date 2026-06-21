# Entropy-Regularized Certainty-Equivalent Bellman Policies for Risk-Sensitive Market Making

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.24878
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 715c7460146a7ce0

## Summary
A risk-sensitive market making problem is solved where a dealer controls bid/ask quotes to maximize a certainty-equivalent objective with entropy regularization in the Bellman equation. Closed-form solutions are derived under Poisson arrival assumptions, yielding a smooth policy that interpolates between the risk-neutral Avellaneda-Stoikov solution and maximum-spread quoting. Numerical experiments show improved risk-adjusted returns and smoother quote trajectories versus standard risk-neutral market making.

## Why it might be useful
Strategy B (delta-neutral carry on Hyperliquid) involves posting positions on 8h rebalancing cycles — while not strictly market making, the quote-smoothing principle from entropy regularization could inform how to reduce slippage in the execution leg during position adjustments. The certainty-equivalent/entropy tradeoff is also relevant to Strategy B's notional sizing (NOTIONAL_USD=50, conservative). However, Strategy B currently uses simple TWAP-style execution rather than quote optimization, and the Poisson arrival model is a poor fit for the 8h discrete rebalancing cadence. Implement only if Strategy B moves to continuous quoting on mainnet.

## Extracted content
- Key result: entropy-regularized policy interpolates between Avellaneda-Stoikov (risk-neutral) and maximum-spread quoting
- Framework: certainty-equivalent Bellman with Poisson arrivals → closed-form solutions

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Applicable only when Strategy B moves to mainnet with active quote optimization; not relevant to current 8h discrete rebalancing on testnet.)
