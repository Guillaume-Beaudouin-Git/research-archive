# Sharpe and Return-VaR Maximization for Options under Skew-Elliptical t-Returns

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.17032
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 8725a1e15ef904a466156af9a449b6de

## Summary
Derives closed-form portfolio weights for maximizing Sharpe ratio and return-to-VaR ratio when the underlying asset returns follow a skew-elliptical t-distribution (heavy tails and asymmetry). The main result shows that the optimal portfolios for the two objectives (Sharpe vs return/VaR) have meaningfully different compositions, contrary to the Gaussian case where they coincide. The formulas are explicit and depend on the skew parameter and degrees of freedom of the t-distribution.

## Why it might be useful
Strategy A vol-targeting uses a 28-day log return volatility window under the implicit assumption of symmetric distribution. For BTC/ETH/SOL which exhibit significant negative skew and heavy tails, the skew-elliptical t allocation could improve position sizing during stress periods. However, the paper optimizes an option portfolio (not a futures portfolio), and the extension to our TSMOM long-only crypto context requires adapting the multi-asset formulas. The Sharpe-vs-VaR difference is most important for our propfirm context (FTMO 10% DD limit): under fat tails, VaR-optimal is not Sharpe-optimal, and our current Strategy A sizing (propfirm_canonical.py) uses a symmetric DD model. The formulas require estimating skew and degrees-of-freedom parameters, which with only 3 assets and daily data would have high estimation error.

## Extracted content
"We provide explicit formulas for the portfolio weights when maximizing the Sharpe ratio and return-to-Value-at-Risk (VaR) ratio in the skew-elliptical setting. Numerical experiments reveal that the optimal portfolios for the two ratios are different."

Formulas in full paper, not available in excerpt.

## Action proposed
REFERENCE

Theoretically relevant for fat-tail-aware sizing, but requires options context for the full formulas and has high estimation noise with 3 assets. Current propfirm focus is on Propr (TSMOM paused) and FTMO (strategy TBD). Revisit if a new multi-asset propfirm strategy with N>5 assets is developed.
