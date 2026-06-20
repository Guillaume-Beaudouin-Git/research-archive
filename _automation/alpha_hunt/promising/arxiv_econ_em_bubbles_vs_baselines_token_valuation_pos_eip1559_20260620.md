# Bubbles vs. Baselines: Token Valuation and Institutional Capital in PoS Networks Under EIP-1559

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.07445
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e48dbbfdb6765f77994b22d2124c6589

## Summary
This paper develops a macroeconomic equilibrium model for Ethereum-style PoS networks with EIP-1559 fee-burn mechanics, formalizing the interaction between a Kelly-optimizing institutional investor and a utility-driven retail consumer. The model predicts that in the "Unbounded Accumulation" regime (consumer accumulates tokens, creating buy-side pressure), institutional portfolio rebalancing creates predictable patterns in token price dynamics. The paper derives conditions for bubble formation and stable valuation, finding that institutional rebalancing intervals and retail accumulation rates are the key parameters.

## Why it might be useful
This is background theory for Strategy B's ETH-adjacent pairs. HMSTR, WLD, and other PoS tokens in Strategy B's VIABLE_ASSETS are subject to the same ETH/PoS token dynamics described here. The model's "institutional portfolio rebalancing creates predictable patterns" finding is relevant to Strategy B's 8-hour rebalancing rhythm — if institutional rebalancing is clustered (e.g., at 00:00/08:00/16:00 UTC), Strategy B's rebalance times (00:10/08:10/16:10 UTC) may capture or be affected by institutional flow. The EIP-1559 burn mechanics also affect SOL/ETH token supply dynamics relevant to Strategy A's long-only holdings.

## Extracted content
"Kelly-optimizing rational institutional investor and a utility-driven retail consumer." Two regimes: Unbounded Accumulation and stabilization. "Institutional portfolio rebalancing creates predictable patterns in token price dynamics." Key parameters: rebalancing intervals and retail accumulation rates.

## Action proposed
REFERENCE

Background theory for Strategy B token selection. The model's rebalancing interval prediction is potentially testable (do funding rates spike at 00:00/08:00/16:00 UTC?), but would require at least 6 months of HL funding rate data at 1-hour resolution to test with HAC significance. Current VIABLE_ASSETS analysis uses 8h intervals — examine whether 8h funding rate autocorrelation supports the institutional rebalancing hypothesis.
