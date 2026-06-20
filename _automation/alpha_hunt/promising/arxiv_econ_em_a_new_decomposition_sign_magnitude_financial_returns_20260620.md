# A New Approach to Modeling Financial Returns: Conditioning Sign on Magnitude

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.04153
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 5b54c5700b496be14a4a07a997e338b9

## Summary
This paper proposes decomposing financial returns into sign and magnitude (absolute value ≈ volatility), then modeling the sign conditional on the magnitude. The key empirical finding: changes in volatility contain significant information about the likelihood of positive vs. negative returns, over and above standard predictors. The joint model P(sign | magnitude) × P(magnitude) outperforms competing return distribution models on S&P 500 daily data. The conditional sign model effectively captures volatility-regime-dependent skewness — higher volatility days have more negative skew.

## Why it might be useful
The Strategy A signal `tanh(cumret_28d / (vol_28d × sqrt(28))).clip(lower=0)` already conditions on volatility magnitude in the denominator. This paper's decomposition suggests an extension: use P(sign | vol_28d) as a probability-of-direction signal rather than a continuous normalized return. For TSMOM, this would mean: "signal = P(return > 0 | vol_28d)" computed from the empirical conditional distribution on historical BTC/ETH/SOL data. The sign-on-magnitude decomposition could also improve the vol targeting in daily rebalance decisions for Strategy B (does higher funding rate volatility predict direction of funding rate change?). However, Strategy A is frozen and this is an incremental modification.

## Extracted content
"Changes in volatility contain valuable information about the likelihood of positive versus negative returns." Joint model: P(sign | magnitude) × P(magnitude). "The joint distribution used to compute expected returns combines a model for the marginal distribution of magnitude with a model for the distribution of the sign, conditional on the contemporaneous magnitude." Applied to S&P 500 daily data.

## Action proposed
TEST_LATER

Apply sign-on-magnitude decomposition as a research extension for future Strategy D crypto arm or post-unfreeze A modification. Test P(BTC return > 0 | vol_28d) computed empirically from Binance daily klines vs. the current `tanh(cumret_28d / vol_28d)`. Data available locally. Strategy A frozen, so defer to next A-review cycle (post-Propr resolution) or new strategy development.
