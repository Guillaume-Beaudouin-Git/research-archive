# Large-Scale Asset Selection via Metric Dependence with Enriched High-Frequency Information

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.02326
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 665b325f1bed39175a6b5e14ee783ca2

## Summary
This paper proposes Metric Dependence Screening (MDS), an asset selection procedure that incorporates high-frequency intraday data as object-valued inputs (functional data) rather than scalar summaries. Each asset-day is represented as an intraday return curve, and the MDS selects assets whose intraday functional data is most informative for predicting risk-adjusted portfolio returns. The method handles large asset universes (N > 1000) with a screening step that reduces the search space before optimization. Applied to S&P 500 stocks, MDS outperforms correlation-based and scalar-return-based selection on out-of-sample Sharpe.

## Why it might be useful
The Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) currently uses 24 continuous futures contracts — below the N≥30 minimum (hard rule) but manageable for cross-sectional work. When/if the universe expands, MDS could improve the asset selection stage. More directly: for the sector_hothand_propfirm research (12 sector ETFs), MDS-based asset selection using intraday curves could identify which sectors have the most predictive power for the hothand signal. The object-valued data representation (intraday curve per asset-day) is also applicable to NQ MNQ intraday research — each MNQ trading day as a functional object, selecting days with similar intraday structure to the current day for regime identification.

## Extracted content
MDS = "Metric Dependence Screening." Uses "intraday data as object-valued data." Screening step for large N. Applied to S&P 500 stocks. "Outperforms correlation-based and scalar-return-based selection on out-of-sample Sharpe."

## Action proposed
REFERENCE

File for Commodities XS Phase A completion (when universe selection is finalized) and for sector_hothand_propfirm Phase 2 (after t_HAC audit). The object-valued day representation is also an interesting approach for NQ day-type classification, complementary to the VVG Classifier (paper 056537d9). Lower priority given more targeted tools already staged.
