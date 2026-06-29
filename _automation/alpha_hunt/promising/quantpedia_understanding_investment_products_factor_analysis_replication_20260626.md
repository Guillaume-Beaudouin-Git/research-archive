# Understanding Investment Products Through Factor Analysis and Replication

**Source**: quantpedia
**URL**: https://quantpedia.com/understanding-investment-products-through-factor-analysis-and-replication/
**Captured**: 2026-06-26 13:30 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 0b1dcb171aeb940a3801683fcee92c7d

## Summary
This article applies four complementary Quantpedia Pro tools — multi-factor analysis, factor model decomposition, 100-year portfolio analysis, and ETF replication — to build a unified framework for understanding what drives investment product returns. The methodology decomposes portfolio returns into systematic factor exposures, assesses statistical and economic significance of those exposures, and evaluates behavior across market regimes. The goal is to distinguish factor-explained performance from genuine alpha, and to replicate investment products cheaply via liquid instruments.

## Why it might be useful
The ETF replication and factor decomposition framework is methodologically relevant to two situations in Algo_claude: (1) understanding the beta exposure of Strategy A (TSMOM crypto long-only, L11 confirmed β_crypto ≥ 0.80) — a formal factor attribution would quantify how much of A's Sharpe 1.33 OOS is market-timing vs crypto beta; (2) for the FTMO CFD research arc, factor attribution can test L25 (two-sided test gate) by checking whether a long-only sleeve is just equity/carry up-drift. The Quantpedia Pro tools are commercial and not reproducible locally, but the conceptual framework (decompose → validate significance → replicate) maps directly onto the methodology already used in `PropFirms/ftmo/program_2026-06/`. No immediate test — the statistical tooling is already in the repo (HAC OLS, walk-forward).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
