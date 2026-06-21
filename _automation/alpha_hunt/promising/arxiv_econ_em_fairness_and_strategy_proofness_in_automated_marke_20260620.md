# Fairness and Strategy-Proofness in Automated Market Makers

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.04959
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 3f46a71cd10ff747372aa8fbc7ffd01c

## Summary
For AMMs with three or more assets, no governance voting rule is simultaneously fair (Arrovian) and strategy-proof. Fairness requires the weighted Aitchison centroid (geometric mean) while strategy-proofness forces median-type aggregation — the only rule satisfying both is a single-provider dictator. This impossibility vanishes at two assets where both properties can be satisfied together.

## Why it might be useful
Strategy B trades Hyperliquid perpetuals where AMM governance affects pricing and fill quality. The impossibility result means multi-asset HL pool governance is structurally manipulable — creating predictable temporary mispricings around governance events in VIABLE_ASSETS (TST, MEGA, WLD, STX, WIF, BIO, TRUMP, HMSTR). Monitoring HL governance proposals for multi-asset pool changes and testing for pre/post mispricing could extend Strategy B's edge catalog, but this requires event-driven data infrastructure not currently available.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
