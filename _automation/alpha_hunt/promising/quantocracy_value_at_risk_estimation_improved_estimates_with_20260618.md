# Value-at-Risk Estimation: Improved Estimates with the Harrell-Davis Quantile Estimator

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=lwV3VvJdAQ&source=feedburner
**Captured**: 2026-06-18 05:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 43c49f6ba0976ce255bc57bb1d223a64

## Summary
A practical guide comparing classical empirical-quantile VaR against the Harrell-Davis (HD) quantile estimator, which replaces the single order statistic at level α with a weighted linear combination of all order statistics, using a Beta(nα, n(1-α)) kernel. The HD estimator produces smoother tail estimates with lower variance, particularly relevant at extreme quantiles (1%–5%) where the sample quantile suffers from high variance and discreteness artifacts. The post is part of a series on univariate VaR methods from Portfolio Optimizer.

## Why it might be useful
The most direct application is improving tail estimation inside `Portfolio/risk/trailing_dd_simulator.py`, which currently drives propfirm pass-probability calculations for FTMO challenges. The simulator uses empirical daily-return distributions calibrated from historical strategy returns to model the symmetric-barrier problem (L24). The current implementation uses a calibrated trade-based generator — switching to HD quantile estimates for the 1%-5% tail region would reduce the variance of the estimated bust probability, potentially narrowing the uncertainty band on the ~44% structural ceiling identified for lumpy strategies (L24). The second application is Strategy B delta-neutral carry: with N<250 testnet observations (L14), tail estimates are noisy; HD smoothing would give more reliable daily VaR estimates for the 8h rebalance cycle, consistent with CLAUDE.md's requirement for HAC-adjusted inference at small sample sizes.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction (the description was truncated at the method introduction).

## Action proposed
TEST_LATER — HD quantile estimator is a direct drop-in for the empirical quantile in `trailing_dd_simulator.py`. Implementation cost is 1-2 hours (scipy has `harrell_davis_quantile` approximations, or implement via Beta CDF weights). Worth pulling the full article first to check if they provide code or benchmark comparisons.
