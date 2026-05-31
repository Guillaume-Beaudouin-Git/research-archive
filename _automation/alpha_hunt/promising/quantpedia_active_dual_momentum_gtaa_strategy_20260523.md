# Active Dual Momentum GTAA Strategy

**Source**: quantpedia
**URL**: https://quantpedia.com/active-dual-momentum-gtaa-strategy/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 5665bf7d577d078cb0bd18789795bb6e

## Summary
A weekly-rebalanced Global Tactical Asset Allocation strategy that selects assets using dual momentum: a relative momentum rank among candidates combined with an absolute momentum filter that prevents holding assets in downtrends. Two sub-strategies with different lookback horizons are merged into a single portfolio, the hypothesis being that short- and long-term momentum signals complement each other. The study reports competitive Sharpe and Calmar ratios versus a buy-and-hold ETF benchmark while maintaining materially lower drawdowns.

## Why it might be useful
The dual momentum structure (absolute + relative, multiple lookback horizons) is a clean extension of Strategy A (crypto TSMOM v3, tanh signal, 28-bar window). Specifically: (1) adding an absolute momentum filter to Strategy A — don't go long BTC/ETH/SOL if the asset's 28-day return is negative — could improve the MaxDD from -6.9% toward the PROPFIRM_PASS gate of <-10%. (2) Combining short-term (7-day) and long-term (28-day) momentum signals into a composite score is a candidate modification for Strategy A v4. However: Strategy A is currently FROZEN (Propr breach) and any modification awaits a new propfirm engagement. Also, ETF roll drag caution applies — the GTAA paper uses ETFs, not futures; the absolute momentum filter works better on futures-like instruments. The Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) could more immediately benefit from dual momentum construction across 24 contracts.

## Extracted content
The description states the strategy achieves "attractive Sharpe and Calmar ratios, while maintaining lower drawdowns compared to a simple equally weighted benchmark." No specific numerical values in the excerpt.

## Action proposed
TEST_LATER — Read full article for absolute momentum filter specification and dual-lookback construction. Evaluate as modification #1 for Strategy A v4 (when FROZEN status lifts) OR as a signal enhancement for the Commodities XS monthly IC scan.
