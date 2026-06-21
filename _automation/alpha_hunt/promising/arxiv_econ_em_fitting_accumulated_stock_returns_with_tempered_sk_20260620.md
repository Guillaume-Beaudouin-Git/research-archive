# Fitting Accumulated Stock Returns with Tempered Skew t-Distribution

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.19318
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e433c02f84f4b2079d67b1b75973a73b

## Summary
S&P 500 multi-day accumulated returns from 20 to 120 trading days show progressive tempering of power-law tails toward a finite tail index. A 'capped Inverse Gamma' stochastic volatility model generates a tempered Student-t distribution, extended with a Jones-Faddy asymmetry mechanism to produce the tempered skew-t. The distribution fits empirical accumulation horizons 20-120 days well.

## Why it might be useful
Strategy A targets a 28-day signal horizon with vol-target 18% and MAX_TOTAL_DD=5.5%. The 28-day return distribution tail shape directly determines what percentile the DD guardrails correspond to. Concrete test: fit the tempered skew-t to BTC/ETH/SOL 28-day returns from Binance daily klines, compute the percentile of -5.5% under the fitted distribution, and verify the current guardrail is calibrated appropriately (target: ~1% tail). 1-day effort with scipy. TEST_LATER pending Strategy A unfreeze.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Fit tempered skew-t to BTC/ETH/SOL 28-day returns to validate DD guardrail calibration; Binance klines available, 1 day, post Strategy A unfreeze.
