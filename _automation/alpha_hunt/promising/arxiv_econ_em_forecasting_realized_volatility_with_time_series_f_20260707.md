# Forecasting Realized Volatility with Time Series Foundation Models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.05291v1
**Captured**: 2026-07-07 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 5c8360f491acacc0084bdddbe846dbd4

## Summary

The paper runs the first systematic head-to-head between nine pretrained, zero-shot time-series foundation models and eight classical econometric volatility forecasts (the HAR family and relatives), across 50 assets in equities, FX and futures at three horizons. The headline result is negative for the hype: once the comparison is done asset-by-asset instead of pooled, only one small foundation model (Tiny Time Mixers) narrowly beats a well-specified Log-HAR benchmark at every horizon, and the rest don't improve on it at all. A recalibration step shows much of the apparent short-horizon edge is really just better-scaled forecasts rather than genuinely better dynamics, with a real informational gain surviving only at the monthly horizon. The most robust finding is that a simple equal-weight average of Log-HAR and the foundation model matches the best single model almost everywhere, so you don't need to pick the "right" architecture per asset.

## Why it might be useful

This is a direct hit on the "daily vol targeting" mandatory rule (CLAUDE.md core lesson 8) and on the realized-vol estimator underlying Strategy A's sizing (`tanh(cumret_28d / (vol_28d × sqrt(28)))`, 28-bar log-return window, VOL_TARGET_LIVE=0.18). Strategy A currently uses a naive rolling realized-vol estimate, not a HAR-family forecast — this paper's finding that HAR remains highly competitive against fancier models is a low-cost validation that the existing approach isn't leaving much on the table, while also suggesting a concrete, cheap upgrade path (HAR-RV regression, well-documented closed form, no new data needed) if vol-targeting responsiveness ever becomes a bottleneck. Strategy A itself is frozen (2026-05-30), so this isn't actionable there right now, but it's directly relevant to any future Strategy D or Commodities XS vol-targeting implementation, and generalizes the "always compute cost drag first" / vol-scaling discipline already baked into the methodology toolkit.

## Extracted content

Numeric claims (attributed, from the abstract): "only one small model, Tiny Time Mixers (TTM), beats the [Log-HAR] benchmark at every horizon, and by a narrow margin"; an equal-weight TTM/Log-HAR average "enters the Model Confidence Set for 98 to 100% of assets." No code or formulas in the excerpt — full paper needed for the HAR specification and MCS test details.

## Action proposed

TEST_LATER

Concrete and cheap to implement (HAR-RV regression on existing return data) but Strategy A — the only strategy currently doing daily vol-targeted sizing — is frozen, so there's no live target to apply it to. Revisit if Strategy D or a future strategy needs a vol-targeting model, or if Strategy A unfreezes.
