# Composite Likelihood Inference of Fractional Gaussian Processes with Spectral Methods

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.11962
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: cdb27c9a7d580793

## Summary
A spectral composite likelihood estimator for the Hurst parameter and variance of fractional Brownian motion and fractional Ornstein-Uhlenbeck processes achieves near-optimal efficiency at O(n log n) cost versus O(n³) for full likelihood, enabling estimation on series of length 10⁶. Applied to realized volatility of equity indices, Hurst parameters are found in the range 0.10-0.16, consistent with rough volatility models.

## Why it might be useful
The Hurst parameter estimates (H∈[0.10, 0.16]) confirm rough volatility structure in equity indices, which is theoretically relevant to vol targeting in Strategy A (28-bar vol window) and D (NQ intraday vol estimation). The O(n log n) algorithm enables fast estimation on the full NQ 1-min dataset (2010-2026, ~8M bars). However, rough volatility is a model selection question that does not change the current TSMOM signal or NQ ORB signal design in any actionable way — the vol estimators in strategies A and B already use rolling realized volatility without assuming H=0.5. This would matter only if a vol forecasting component were added to strategy D.

## Extracted content
- Claims: Hurst H ∈ [0.10, 0.16] for realized volatility of equity indices (consistent with rough volatility); O(n log n) vs O(n³) full likelihood
- Estimators: fractional Brownian motion + fractional OU, spectral composite likelihood

No verbatim code or formulas in the excerpt.

## Action proposed
REFERENCE
