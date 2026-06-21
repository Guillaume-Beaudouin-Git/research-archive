# Robust Lambda-VaR Computation and Portfolio Optimization with Variable Confidence Levels

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.06220
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: ffe59b610b86957271e44bf7246f81f6

## Summary
Lambda value at risk (lambda-VaR) generalizes classical VaR by allowing the confidence level to vary with the portfolio, enabling more flexible tail-risk control. This paper presents a robust numerical algorithm combining Newton's method with bisection for global convergence even in the presence of discontinuities, achieving local quadratic convergence. Applied to portfolio optimization, lambda-VaR minimization is shown to achieve better tail-risk control with lower turnover than CVaR-based approaches in some regimes. Numerical experiments demonstrate the computational efficiency and portfolio construction advantages.

## Why it might be useful
Lambda-VaR's variable confidence level is particularly relevant to the propfirm trailing drawdown simulation in `Portfolio/risk/trailing_dd_simulator.py`, where the effective risk tolerance changes as the account approaches the drawdown floor—at 50% of max drawdown remaining the risk level should be different than at 10% remaining. The lower-turnover property relative to CVaR is directly relevant to Strategy A's weekly rebalancing (Monday 00:05 UTC) where unnecessary turnover costs 0.17% RT on Propr; CVaR-based sizing currently in `Portfolio/risk/sizing.py` may be generating avoidable rebalancing. The bisection+Newton hybrid for global convergence is also directly usable as a numerical improvement in the existing `trailing_dd_simulator.py` without requiring any strategy modification.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Replacing CVaR with lambda-VaR in `Portfolio/risk/sizing.py` and `trailing_dd_simulator.py` is a concrete 1-2 day implementation; defer until Strategy A comes off freeze and Modification 1 is being planned.
