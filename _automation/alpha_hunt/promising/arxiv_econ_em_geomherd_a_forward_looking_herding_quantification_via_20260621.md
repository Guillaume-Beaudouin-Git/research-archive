# GeomHerd: A Forward-looking Herding Quantification via Ricci Flow Geometry on Financial Networks

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.11645
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 8e0b266b54fbd458

## Summary
GeomHerd measures herding behavior using Ollivier-Ricci curvature of asset correlation networks. Declining network curvature (increasing geometric "flatness") precedes realized herding episodes by 5-15 trading days in equity markets. Backtested on S&P 500 constituents (2010-2024), curvature-based herding achieves lead-lag correlation of 0.41 with subsequent cross-sectional dispersion, proposed as a market fragility indicator for position sizing.

## Why it might be useful
The 5-15 day lead on herding/fragility episodes is potentially relevant to Strategy A TSMOM (vol targeting adjusts exposure but does not explicitly predict tail risk episodes) and to sector_hothand_propfirm research (which uses S&P 500 sector data). However, Ricci curvature computation on correlation networks is computationally non-trivial and requires the full S&P 500 constituent universe (N≥30 constraint satisfied). The lead-lag correlation of 0.41 measures predictive correlation of the curvature indicator with cross-sectional dispersion, which does not directly translate to Sharpe or MaxDD improvement without a full backtest. Blocked by the sector_hothand audit (t_HAC=10.38 red flag) before new overlays are added.

## Extracted content
- Claims: Ollivier-Ricci curvature decline precedes herding by 5-15 trading days; lead-lag correlation 0.41 with cross-sectional dispersion (S&P 500, 2010-2024)

No verbatim code or formulas in the excerpt.

## Action proposed
REFERENCE
