# An Index of Commodity Futures Returns Since 1871

**Source**: quantpedia
**URL**: https://quantpedia.com/an-index-of-commodity-futures-returns-since-1871/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 7be62b8925bae8f2e08ed6c2d3857b49

## Summary
A newly released paper constructs a hand-collected US commodity futures database spanning 150+ years to 1871. The index separates spot return, roll yield, and collateral return components — the appropriate decomposition for testing momentum and basis signals on futures. The long-run history includes geopolitical shocks, inflation regimes, supply-chain disruptions, and resource nationalism episodes rarely covered in post-2000 datasets. The authors reportedly find that diversified commodity futures historically delivered equity-like risk premia with distinct diversification benefits relative to stocks across macro regimes.

## Why it might be useful
Direct relevance to the active Commodities XS — Basis + TSMOM research (`Commodities/research/active/xs_basis_tsmom/`). CLAUDE.md archives "Commodity TSMOM ETF: Sharpe 0.39, AMTP p=0.808 — ETF roll drag" — but the roll drag issue disappears when using actual futures, which this paper's index represents. The roll + spot + collateral decomposition is exactly what's needed to test whether the Erb-Harvey (2006) basis signal and Moskowitz (2012) TSMOM signal have persistent IC over the long run. However, accessing the 1871-2025 futures data likely requires the paper's supplemental dataset (may be publicly available) or a Quantpedia Premium subscription. Concrete first step: check whether the underlying paper (check arxiv or SSRN for "An Index of Commodity Futures Returns Since 1871") has a public data appendix before paying for Quantpedia access.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — Directly applicable to Commodities XS active research once Phase A (data fetch + roll validation) is complete. Check whether the underlying academic paper has a public data appendix. If data is accessible, test S_TSMOM and S_BASIS signals on the long-run index. This is the cleanest test of commodity momentum without ETF roll drag contamination.
