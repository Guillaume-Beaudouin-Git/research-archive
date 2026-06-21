# Asymmetric Nonlinear Return Extrapolation and Portfolio Choice Under Stochastic Volatility

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.10805
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 5a617ce7447a839e2b7f12b6fcb14768

## Summary
Extending the linear return extrapolation framework of Atmaz (2022) to incorporate behavioral realism, this paper introduces saturation (very strong past performance generates proportionally smaller bullish expectations) and asymmetry (losses extrapolated more strongly than equal-magnitude gains). Under Heston stochastic volatility, the optimal CRRA portfolio decomposes into myopic demand, variance hedging demand, and a new sentiment hedging demand. Survey evidence is cited as supporting both the saturation and asymmetry features. The pessimism discount from asymmetric loss extrapolation implies that investors overhang drawdowns.

## Why it might be useful
The asymmetric extrapolation finding has direct relevance to Strategy A's tanh signal shape: the tanh function is symmetric by construction (clip(lower=0) makes it long-only, but the underlying signal before clipping is symmetric). If actual investor expectation formation is asymmetric—losses extrapolated more than gains—then the tanh signal may underweight the momentum signal following a loss drawdown, which is exactly the situation during the May 2026 Propr breach. The saturation feature (diminishing extrapolation for very strong trends) is already partially captured by the tanh's S-curve, but the paper's finding that the degree of saturation is empirically calibratable could provide a way to validate the current tanh vs. alternative functional forms. For the Commodities XS basis+TSMOM strategy, the pessimism discount suggests carry and momentum signals following drawdowns may be underestimated by symmetric models.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Behavioral finance theory with implications for signal design; no direct test without the full model equations and a behavioral parameter calibration step not feasible with available data.
