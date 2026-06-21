# Graph Neural Networks Improve Univariate Financial Time Series Forecasting

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.21192
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c7bc38b87a8ba436b1d093228e454629

## Summary
Introduces the "Time-Geometric model" that combines standard temporal sequence models with Graph Neural Networks to capture geometric patterns in univariate financial time series. The GNN component encodes the geometric structure of price paths (adjacency defined by price-similarity or temporal proximity), while the temporal component captures standard autoregressive dependencies. The paper claims statistically significant improvements in forecasting accuracy over temporal-only models, measured by standard prediction metrics.

## Why it might be useful
The connection to the archived Network Momentum (GMOM) research is relevant: `Multi_Asset/research/archived/network_momentum/` was closed because the universe was too small (N<35 after quality filter) and graph density=1.0. This paper's GNN approach targets univariate forecasting (one series), not cross-sectional momentum (which was GMOM's use case). For our NQ 1-min data, a GNN that encodes price-path geometry might be a novel approach for Strategy D's signal generation — but "statistically significant" forecasting improvements in academic papers on financial TS are routinely overfitted (L20). The paper reports prediction metrics, not trading P&L or HAC-validated IC. No code in excerpt.

## Extracted content
"Our findings underscore that leveraging geometric patterns, captured through Graph Neural Networks, yields statistically significant improvements in forecasting accuracy."

No code available in excerpt. No specific numeric claims (no Sharpe, IC, or t-stat reported).

## Action proposed
REFERENCE

GNN-augmented forecasting. "Statistically significant" on prediction metrics is insufficient without IC validation and WF testing. No direct action until full paper methodology is available for HAC-validated evaluation.
