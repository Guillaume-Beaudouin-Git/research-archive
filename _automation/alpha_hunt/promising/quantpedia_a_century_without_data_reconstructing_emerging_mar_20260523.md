# A Century Without Data: Reconstructing Emerging Markets Equity History

**Source**: quantpedia
**URL**: https://quantpedia.com/a-century-without-data-reconstructing-emerging-markets-equity-history/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 37e869003097832723315d03280dea2e

## Summary
Quantpedia applies its previously developed historical data reconstruction methodology (used for US equities, fixed income, and commodities) to emerging market equities, where reliable data before ~1990 is scarce. The framework reconstructs country-level return histories in a "consistent and economically meaningful way" by leveraging cross-country relationships, macro factor linkages, and available proxies to extend usable time series back to the early 20th century. The goal is enabling robust long-term backtesting and multi-regime stress-testing for strategies that include EM allocations.

## Why it might be useful
None of the current Algo_claude strategies include EM equities. Strategy A (crypto TSMOM), Strategy B (HL delta-neutral), and Strategy C (NQ futures) are all developed-market or crypto instruments. The data reconstruction methodology is interesting in principle for the Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`): if commodity futures data from the Quantpedia 1871 index (see companion item `quantpedia_an_index_of_commodity_futures_returns_since_1871_20260523.md`) is used, the same reconstruction framework could extend individual commodity series back to fill gaps. However, both items are Quantpedia-paywalled and the commodity index item is already flagged for the same verification. No near-term test path.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Emerging markets data reconstruction; no fit to current strategies. Could be useful for Commodities XS long-run validation once Phase A is complete, but paywall access is the blocking constraint.
