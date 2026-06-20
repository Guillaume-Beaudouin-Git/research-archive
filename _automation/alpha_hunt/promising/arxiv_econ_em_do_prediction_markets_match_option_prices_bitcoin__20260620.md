# Prediction Market vs. Options Pricing Gap on Bitcoin: A HAC-Robust Arbitrage Study

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.19517
**Captured**: 2026-06-20 10:02 UTC
**Filters passed**: L1=[methodology, metrics], L2_OK
**Hash**: 6a0cc9cf417c02a3462e71b355b9716a

## Summary

Portnaya documents a systematic pricing wedge between Polymarket binary contracts and Binance option-implied risk-neutral probabilities for the same Bitcoin threshold, strike, and maturity. In the September 2023 anchor contract, the mean gap is 5.6 percentage points across 214 hourly observations (t = 6.46, p < 10⁻⁹). Pooling three Binance-compatible Bitcoin threshold markets yields a mean gap of 6.3 points across 287 observations, robust to HAC and block-bootstrap inference. The gap is persistent — AR(1) half-life roughly four hours — but ultimately mean-reverting, which the author attributes to slow information transmission between segmented venues rather than noise. A delta-hedged arbitrage proxy remains profitable after conservative transaction costs but with marginal statistical precision (full details deferred to the paper). The cross-sectional pattern shows the wedge is largest at low option-implied probabilities and long maturities, consistent with speculative demand (not measurement error) on the prediction-market side.

## Why it might be useful

This paper uses HAC + block-bootstrap inference — the exact methodology mandated in CLAUDE.md for all our tests — and applies it to a Bitcoin cross-venue pricing study. The finding is relevant at two levels. First, methodologically: the paper demonstrates how to correctly measure a persistent but mean-reverting cross-venue gap with N=287 hourly observations and HAC corrections, which is exactly the situation we face when evaluating cross-exchange opportunities (L12b: HAC deflation on autocorrelated signals). Second, strategically: the venue pair Binance options ↔ Polymarket is outside our current tradable universe (Strategy B is on Hyperliquid perps, not options), but the approach of cross-venue binary-payoff arbitrage using risk-neutral probability benchmarks is a methodology we could apply to Hyperliquid vs. Polymarket BTC/ETH threshold contracts if such pairs exist. Before adding this to the research pipeline, check L12 (event-count ceiling: at ~365 events/yr per position, cost gate is roughly 0.17% RT Binance options) — the paper acknowledges marginal significance post-costs.

## Extracted content

From the abstract/summary:
- "the mean pricing gap equals 5.6 percentage points across 214 hourly observations (t = 6.46, p < 10^{-9})"
- "Pooling three Binance-compatible Bitcoin threshold markets yields a mean gap of 6.3 percentage points across 287 observations, robust to HAC and block-bootstrap inference."
- "The gap is persistent - with an AR(1) half-life of roughly four hours - yet mean-reverting, consistent with slow information transmission between segmented venues rather than mechanical noise."
- "Cross-sectional regressions reveal that the wedge is largest at low option-implied probabilities and long maturities, a pattern consistent with speculative demand for prediction-market contracts rather than measurement error."
- "A delta-hedged arbitrage proxy remains profitable after conservative transaction costs, though with marginal statistical precision."

No code in excerpt. Full article needed for transaction cost breakdown and the delta-hedge implementation details.

## Action proposed

TEST_LATER

Interesting as a future Strategy D candidate (cross-venue crypto arb), but requires Binance options API access (not currently in data pipeline) and Polymarket API. Our current free-data universe doesn't cover this. Check in 3-6 months when exploring new crypto strategies — pre-register with L12 ceiling check first. Reference methodology section for HAC treatment of persistent cross-venue gaps.
