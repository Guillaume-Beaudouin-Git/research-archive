# Polymarket-v1 Database: Complete On-Chain Trade Archive 2022–2026

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.04217
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: ff0a6c90747b6e6b1e198922dafb3eef

## Summary
The Polymarket-v1 Database is a complete on-chain trade archive of Polymarket's first-generation CTF Exchange on Polygon, spanning November 2022 to April 2026 with 1.20 billion trade records across 1.30 million markets and $61 billion in nominal volume. The defining feature is 100% ground-truth aggressor direction derived from the blockchain settlement layer — a property unavailable in centralized order books. The dataset enables fill-side analysis, spread measurement, institutional vs. retail participation identification, and liquidity dynamics across prediction market types (sports, politics, crypto).

## Why it might be useful
The "Fill-Side Non-Retail Trading on Polymarket" paper (from prior runs, already in `promising/`) uses this dataset. More directly relevant: the archived "Resolution-Aware Perpetual Futures on Binary Prediction Markets" paper (6d819cfb, this run) uses Polymarket data for counterfactual PIRAP evaluation. Having the full database available enables cross-checking of that paper's empirical results. For Strategy B, Polymarket prediction market prices for crypto events (e.g., "Will ETH exceed $X by date Y?") could serve as regime signals — if Polymarket heavily discounts upward moves, reduce B's long-side exposure. Data access: on-chain at Polygon, derivable from public blockchain data (though 1.2B records requires significant compute).

## Extracted content
Dataset: "1.20 billion trade records across 1.30 million markets with $61 billion in nominal volume." Coverage: "2022-11-21 to 2026-04-28." "100% ground-truth aggressor direction derived from the blockchain settlement layer." On Polygon blockchain. Available via blockchain node or academic sharing.

## Action proposed
REFERENCE

Not actionable without significant data infrastructure. Note for future reference if prediction market sentiment signals are tested for Strategy B's asset selection (see CLAUDE.md "Untested" section). Pair with paper 6d819cfb (PIRAP framework) for full prediction market research context.
