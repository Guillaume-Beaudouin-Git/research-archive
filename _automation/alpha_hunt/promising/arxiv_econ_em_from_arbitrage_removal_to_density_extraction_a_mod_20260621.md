# ARIES+SEDEx: Model-Free Risk-Neutral Density Extraction for Short-Dated Options

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.22792
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 206ed1dea35b371d20321d2491554e5d

## Summary
A two-step pipeline for extracting risk-neutral densities from short-dated (hours to one week) SPX option chains using bid-ask quotes as the primitive constraint rather than mid prices. Step 1 (ARIES) removes executable static arbitrages under market-depth constraints. Step 2 (SEDEx) recovers a smooth density via a smoothness-plus-entropy objective. The motivation is that near-expiry options have bid-ask spreads comparable to premia, making mid quotes unreliable. Validated on synthetic Heston panels and real SPX data, producing stable densities even around macro announcements.

## Why it might be useful
We have no live options strategies. The archived SPX VRP angle (n=1 test, wrong direction IC) and BTC VRP (L13: costs 2× gross) are both closed. This paper is relevant only if a short-dated options vol-surface strategy is reconsidered, which requires either Deribit API access (crypto) or SPX chain data (not in our current data sources). Background reference for the VRP archived research. No connection to Strategies A/B/C/D.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Options-pricing methodology with no path to current active strategies. Density extraction technique potentially useful if Deribit VRP is ever reconsidered, but L13 economics gate would need to be cleared first.
