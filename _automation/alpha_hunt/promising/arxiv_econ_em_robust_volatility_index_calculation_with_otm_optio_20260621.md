# Robust VIX-Style Volatility Index from Arbitrage-Free OTM Option Pricing Function

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17446
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c1727898a5345f5c5f8e6c5106da127e

## Summary
A method for constructing a volatility index (VIX-like) that robustly handles the discrete strike grid of real options markets. The approach builds a continuous European option pricing function consistent with observed bid-ask spreads while enforcing monotonicity and convexity. The key advantage over prior work: fewer market parameters required, making the procedure robust even with sparse OTM option chains. This allows more stable VIX calculations in thin markets or stress periods.

## Why it might be useful
VIX is used in Strategy D (D3/D5 regime filter candidate) as a potential exogenous variable to condition the NQ intraday signals. However, we would use the VIX level directly from a data feed (Yahoo Finance, Databento) rather than constructing a custom vol index. This paper's contribution (better vol index construction from option chains) is only relevant if we were to construct a crypto VIX from Deribit option chains — which we are not currently doing (L13: BTC VRP costs 2× gross, options path closed). Not directly actionable.

## Extracted content
"Focusing on the fact that volatility indices are primarily calculated from the prices of out-of-the-money (OTM) options, this paper proposes a novel method for constructing a continuous European option pricing function that is consistent with the bid-ask spreads of observed OTM options and strictly satisfies arbitrage-free conditions."

No code or specific numeric claims in excerpt.

## Action proposed
REFERENCE

Vol index construction methodology. Not applicable until a crypto vol surface strategy is considered (blocked by L13).
