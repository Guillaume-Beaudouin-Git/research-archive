# RED-2400: Public Benchmark of Algorithmically-Rejected DEX Token Events with Outcome Labels

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.12151
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: db64b26af947c384bb3471b3848c4a42

## Summary
RED-2400 is a public benchmark of 6,659 algorithmically-rejected token events from a live Solana DEX filter stack, logged from 2026-04-10 to 2026-05-02, linked to 169,122 post-rejection price and liquidity observations. Outcome labels follow a five-tier classification (saved windowed, saved early-death, missed, flat, unclassifiable) computed deterministically from fixed thresholds rather than fitted to post-rejection data. The key finding is that only 15.8% of rejected events were classified as missed opportunities (would have been profitable), suggesting reasonable filter precision. The benchmark is designed to evaluate counterfactual filter precision—whether the filter correctly excluded unprofitable tokens.

## Why it might be useful
The RED-2400 benchmark methodology—tracking post-rejection outcomes to evaluate filter precision—is directly applicable to the `_automation/alpha_hunt/` pipeline's feasibility filter: currently there is no systematic measurement of whether ideas rejected at L0/L1/L2 gates would have passed backtesting. Building a post-rejection tracking log analogous to RED-2400's approach (logging rejected ideas with their reasons, then checking one month later if similar ideas that did proceed validated) would calibrate the `_automation/feasibility/` handlers. The 15.8% false-negative rate also serves as a benchmark reference: if the alpha hunt pipeline's false-negative rate exceeds ~20%, the L1/L2 filters may be too conservative relative to what Solana DEX filters achieve in an entirely different domain.

## Extracted content
Specific numeric claims: 6,659 rejection events, 169,122 post-rejection observations, 1,836 graveyard-tracker snapshots, 15.8% missed opportunity rate (p<0.05 threshold for the ILS-dl companion paper).

## Action proposed
REFERENCE

Solana DEX context is not directly tradeable in this pipeline; the methodology for filter calibration via post-rejection tracking is useful as a design pattern for the feasibility pipeline audit.
