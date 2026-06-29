# Why Mean-Variance Optimization Breaks Down in Practice

**Source**: quantocracy (via Quantpedia)
**URL**: https://quantocracy.com/redirect.php?key=eLoQfS2Afq&source=feedburner
**Captured**: 2026-06-29 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 0a404f2ff703a5c77c4c7b9d9c981baa

## Summary
Plug-in Mean-Variance Optimization — using sample estimates of expected returns and covariance directly — systematically generates unstable, over-leveraged portfolios in live deployment. The root cause is estimation error in expected returns, which scales with portfolio size and destabilizes the optimizer. The article presumably covers shrinkage estimators, robust alternatives (Black-Litterman, minimum-variance), and why even modern variants of MVO require regularization to function in practice. The argument is that theoretical elegance does not translate to reliable sizing without explicit error control.

## Why it might be useful
Directly relevant to the A+B book risk construction validated 2026-06-10: the choice of Equal Risk Contribution (ERC) over MVO was correct for exactly the reasons this article describes — ERC is robust to return estimation error because it only requires the covariance matrix, not expected returns. This serves as methodological validation of the current `Portfolio/state/portfolio_state.py` approach. For any future Strategy D integration, this reinforces keeping ERC as the default sizing method and treating MVO-based allocations with suspicion unless expected returns are pinned via a factor model. No immediate test needed, but useful to reference when justifying ERC in any propfirm presentation or portfolio audit.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
