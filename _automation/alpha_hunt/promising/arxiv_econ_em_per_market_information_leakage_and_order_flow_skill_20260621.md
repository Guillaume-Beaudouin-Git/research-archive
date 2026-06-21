# Per-Market Information Leakage and Order-Flow Skill: Two Methodological Notes

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.02287
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a4a2314ddf5ea749

## Summary
Two concurrent methodological refinements for studying informed trading on DEXs: (1) a per-market decomposition of price impact separating genuine information leakage from mechanical inventory effects, and (2) an order-flow skill metric measuring directional accuracy of liquidity-taking orders net of momentum. Applied to Hyperliquid perpetual futures (2023-2026), 3-7% of accounts show persistent order-flow skill, concentrated in tokens with low float and high funding dispersion.

## Why it might be useful
This paper is directly relevant to Strategy B (delta-neutral carry on HL testnet, mainnet ~Jul 2026) and to the broader Hyperliquid microstructure understanding needed before mainnet deployment. The finding that persistent order-flow skill is concentrated in tokens with high funding dispersion aligns with Strategy B's VIABLE_ASSETS selection criterion (MIN_VOL_USD=1_000_000, carry-based selection including HMSTR, WLD, STX). Concretely: the per-market decomposition methodology could be applied to validate whether Strategy B's carry positions coincide with informed accounts, which would signal adverse selection risk. The 3-7% skilled account concentration is also relevant to understanding HL market depth and slippage for the ~$50 notional Strategy B trades. Actionable: read the full paper to extract the order-flow skill formula and check whether Strategy B's account shows skill classification.

## Extracted content
- Claims: 3-7% of HL perpetual futures accounts show persistent order-flow skill (2023-2026), concentrated in low-float tokens with high funding dispersion
- Methodology: per-market price impact decomposition (information leakage vs inventory effects) + order-flow skill = directional accuracy net of momentum

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Read full paper to extract order-flow skill formula; apply to Strategy B account data on HL testnet to check adverse selection exposure before mainnet launch ~Jul 2026.)
