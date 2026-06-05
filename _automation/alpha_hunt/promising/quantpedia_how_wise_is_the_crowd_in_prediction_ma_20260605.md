# How Wise is the Crowd? Bias and Edge in Prediction Markets

**Source**: quantpedia
**URL**: https://quantpedia.com/how-wise-is-the-crowd-in-prediction-markets/
**Captured**: 2026-06-05 16:03 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: ad0940d877b723ba89c4026d47e91531

## Summary
A recent paper constructs a high-frequency data pipeline that ingests tick-level order flow, on-chain wallet histories, and social commentary from both decentralized (Polymarket) and regulated (Kalshi) prediction market venues. The central argument is that crowd-aggregate probabilities in Web3 betting markets appear efficient at the surface level but conceal structural inefficiencies that benefit informed or automated participants. The paper attempts to quantify who extracts edge versus who provides liquidity, using microstructure metrics rather than terminal payoff decomposition (which distinguishes it from the companion paper "Who Profits from Prediction Markets?" — already filed 2026-05-23).

## Why it might be useful
The paper's methodology — combining tick-level on-chain flow with social commentary signals on a DEX venue — is structurally adjacent to the on-chain signal families already exhaustively archived in Crypto (netflow HAC deflation at L12b, MVRV/FGVD sentiment at L17/L18). It does not reopen those paths. The more concrete connection is to Strategy B (HL testnet delta-neutral carry): Hyperliquid is a DEX perp venue, and the paper's technique of cross-referencing on-chain wallet histories against execution timing could theoretically be applied to HL funding-rate arbitrage to characterize whether the B carry captures structural edge or just beta. However, the analytical lift is high (tick-level HL data is not cached locally, and the `_raw` funding data is 8h granularity), so this remains distant from any immediate test. The paper also provides no replicable Sharpe or methodology that maps to any CLAUDE.md gate. Note: this is the second Quantpedia filing on prediction market microstructure in two weeks — if a third appears, consider whether a dedicated "prediction market" cluster belongs in the deferred bucket.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. The description is an editorial summary of the paper rather than the abstract. Full article and underlying paper needed for methodology and performance statistics.

## Action proposed
REFERENCE — Prediction markets are not in active research scope, and the on-chain signal families are exhaustively archived (L12b, L17, L18). The microstructure pipeline technique is intellectually interesting but produces no test path against current strategy data. Filed for completeness alongside the companion paper from 2026-05-23.
