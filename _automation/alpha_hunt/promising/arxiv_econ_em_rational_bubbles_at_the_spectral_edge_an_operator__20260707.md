# Rational Bubbles at the Spectral Edge

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.03933v1
**Captured**: 2026-07-07 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 550e803a1e0c53f905a57745c9cebc81

## Summary

The paper builds a single "fragility edge" measure from a market's return covariance structure and a discount rate, arguing that a crisis becomes reachable once the market's dominant common factor gets strong enough relative to that discount. Tested on eighteen global equity indices from 2004-2024, the dominant factor's strength systematically rises during every documented crisis in the sample — markets effectively collapse from roughly six independent factors down to about four. The authors are explicit about what the measure can and can't say: it identifies the fragility threshold precisely, flags that a bubble might exist only roughly, and says nothing about which specific asset is carrying it. The readings line up with crises after the fact rather than forecasting them ahead of time.

## Why it might be useful

This connects directly to L15 in the methodology registry: "Regime overlays on high-Sharpe (SR>1.0) strategies: sub-threshold lift... only useful for strategies with MaxDD>20%." Strategy A (crypto TSMOM, MaxDD -6.9%) is exactly the kind of high-Sharpe, low-drawdown strategy where L15 already predicts a crisis-timing overlay wouldn't move the needle — this paper's own admission that "these readings coincide with crises, not forecasts" reinforces that conclusion rather than overturning it. It also touches the Strategy D regime-filter work in progress (`Futures/research/active/strategy_d/`, handler `RegimeFilter` in `_automation/feasibility/`): a factor-concentration measure is a candidate regime input, but the paper's own coincident-not-predictive caveat means it would only ever flag a crisis as it's happening, which is the wrong timing for the current D3/D5 regime filter (needed to avoid entering, not to exit mid-crisis).

## Extracted content

No code or formulas in the excerpt. Numeric claim (attributed, qualitative): "the market collapsing from about six to about four independent factors" during crises, across 18 global equity indices 2004-2024. Full paper needed for the fragility-edge formula and the discount-rate calibration.

## Action proposed

REFERENCE

L15 already establishes that this class of regime overlay is sub-threshold for Strategy A's drawdown profile, and the paper's coincident (not predictive) nature limits its use as a Strategy D entry filter. Useful background only.
