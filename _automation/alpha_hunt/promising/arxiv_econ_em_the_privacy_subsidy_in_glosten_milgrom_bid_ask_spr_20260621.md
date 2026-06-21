# Privacy Subsidy in Sequential Trading: Bid-Ask Spread under Noisy Direction Observation

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.19742
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 63ad4a0596bc39cbd5bf6fb3a42f36b0

## Summary
Extends the Glosten-Milgrom sequential trading model to a market maker who observes trade direction corrupted by a binary flip channel with probability η (a differential privacy model). The equilibrium bid-ask spread becomes μ(1-2η)Δ where μ is the informed-trader fraction and Δ is the value range. The "privacy subsidy" — a per-trade transfer from the liquidity pool to traders — equals μηΔ, mirroring an earlier Gaussian-Kyle analog. The result holds for both classical two-state and continuous Gaussian microstructure models, suggesting the privacy subsidy is a robust phenomenon.

## Why it might be useful
This paper models how bid-ask spread changes when trade direction is partially obscured. For Strategy B (delta-neutral carry on Hyperliquid), the HL order book is transparent with publicly visible liquidity — no privacy mechanism applies. For Strategy A (TSMOM via Propr), execution is via market orders where we are the liquidity taker, not provider. The Glosten-Milgrom framework is academic market microstructure and does not translate to practical execution improvement for our strategies. Not directly actionable.

## Extracted content
"The equilibrium spread is μ(1-2η)Δ, where μ is the informed-trader fraction and Δ = v_H - v_L the value range."

"The per-trade transfer μηΔ from the protocol's liquidity pool to traders — the 'privacy subsidy'."

## Action proposed
REFERENCE

Market microstructure theory. No application to current execution strategies (we are aggressive takers, not liquidity providers).
