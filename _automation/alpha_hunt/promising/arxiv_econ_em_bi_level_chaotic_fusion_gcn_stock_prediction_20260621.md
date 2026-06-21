# Bi-Level Chaotic Fusion GCN for Calibrated Prediction Intervals on Stock Data

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.16324
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 44138e55aec45ca1e562adb4290fd8e9

## Summary
Most deep learning approaches for financial markets produce point predictions that fail to quantify uncertainty, which is insufficient for risk-aware trading. This paper introduces BCFGCN, a graph convolutional network extended with bi-level optimization and chaotic initialization to output calibrated prediction intervals (upper and lower bounds) rather than point estimates. The architecture models inter-stock dependencies via graph structure, and the chaotic initialization improves coverage calibration close to the nominal level while maintaining narrow interval widths. The authors report substantially better calibration than competing prediction interval methods across multiple forecast horizons on stock market data.

## Why it might be useful
Prediction interval calibration is directly relevant to the vol-targeting logic in Strategy A (`strategies/tsmom_v2_propfirm/signal.py`): the 28-bar vol window produces a point estimate, but the actual uncertainty around that estimate determines whether the guardrails in `execution/__init__.py:46-47` are tight enough given MAX_DAILY_DD=2.8%. The GCN inter-stock dependency modeling could also complement the Commodities XS cross-sectional work (`Commodities/research/active/xs_basis_tsmom/`) by capturing basis and momentum co-movements across the 24 contracts more explicitly than a standard covariance matrix. However, the graph architecture requires labeled edge construction (which commodity contracts share structural co-movement?) and the calibration claims depend heavily on the specific dataset used, which is equities rather than futures.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Graph-based prediction interval methodology is architecturally interesting but requires significant ML infrastructure not currently in the project; point estimates with HAC-corrected uncertainty bounds are more operationally tractable for the current pipeline.
