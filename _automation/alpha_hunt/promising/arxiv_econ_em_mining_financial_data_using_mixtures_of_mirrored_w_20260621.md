# Mirrored Weibull Mixtures for Fat-Tailed Financial Return Modeling

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.20142
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a40d96dae86d74c1e1f07c1d79a0d2d3

## Summary
Proposes a Mixture of Mirrored Weibull (MMW) distributions for fitting stock return distributions and VaR estimation. The MMW model accommodates skewness and heavy tails not captured by normal distributions, has a simple closed-form density, and fast parameter estimation. Evaluated against Gaussian mixture model and t-mixture model on three S&P500 stocks for VaR estimation, showing significant improvements. The "mirrored Weibull" symmetrizes the Weibull distribution around zero to handle signed returns.

## Why it might be useful
For Strategy A (crypto TSMOM), the vol-targeting uses the assumption of log-normal returns (rolling std of log returns). In extreme crypto drawdowns (BTC -80%, L45), the fat tail misspecification from Gaussian vol estimates leads to position sizing errors. The MMW distribution offers a parametric alternative with better tail calibration for VaR. However, our primary use case is vol-targeting for propfirm guardrails (MAX_DAILY_DD=2.8%, `execution/__init__.py:46-47`), and the computational overhead of fitting an MMW on 28 daily returns (small sample) would likely dominate any tail calibration improvement. With N=28, parameter estimation for a 4+ parameter mixture model is unreliable. Limited practical value for current setup.

## Extracted content
"The MMW model can flexibly accommodate non-normal features frequently exhibited in financial data. It also enjoys appealing properties such as having a simple density expression and fast parameter estimation."

"We demonstrate the effectiveness of our model by assessing its performance in Value-at-Risk estimation of three S&P500 stocks."

No code in excerpt. Parameter estimation details in full paper.

## Action proposed
REFERENCE

Fat-tail distribution for VaR estimation. Potentially useful for propfirm DD guardrail calibration but parameter instability with N=28 daily returns makes it impractical for our rolling vol window. Review if longer lookback window is needed for DD stress testing.
