# A Taxonomy of Event-Linked Perpetual Futures: Variant Designs Beyond the Single-Market Binary Case

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.10428
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f40a47d1d8574e5e4ca92394cbb0022f

## Summary
This paper extends the design space of prediction market perpetual futures beyond the simplest case (single binary market, single resolution). The taxonomy includes: conditional probability perpetuals P(A|B), spread contracts (p_A - p_B), weighted basket contracts (Σw_i p_i), derivatives on the variance or entropy of the probability process, contracts on liquidity itself, and perpetual-on-expiring-event roll structures. For each variant, the paper derives the resolution-aware funding rule and margin sizing requirements. The taxonomy is motivated by the gap between current Polymarket/Kalshi designs and the theoretical design space.

## Why it might be useful
This is companion paper to the PIRAP paper (6d819cfb). For Strategy B, the conditional probability perpetual P(A|B) design is interesting: "given BTC is above $X, what is the probability of ETH outperforming?" — a conditional prediction market that could capture the BTC/ETH basis spread dynamic. Strategy B currently uses simple perpetual funding rate carry; a conditional probability perpetual over HMSTR resolution events could be a new Strategy B variant. However, HL does not currently offer prediction market perpetuals, and the design space is theoretical. File for future reference when/if HL expands its perpetual offering.

## Extracted content
Taxonomy includes: conditional probability perpetuals P(A|B), spread contracts (p_A - p_B), basket contracts, volatility/entropy contracts, liquidity contracts, perpetual-on-expiring rolls. Resolution-aware funding rule derived for each variant. Companion to PIRAP paper (2605.10400).

## Action proposed
REFERENCE

Future reference for Strategy B evolution if HL expands to event-linked perpetuals. Pair with paper 6d819cfb (PIRAP) and paper ff0a6c90 (Polymarket-v1 database) for complete prediction market context. Not actionable with current HL instrument set.
