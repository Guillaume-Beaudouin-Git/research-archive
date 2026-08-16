# Deep Learning for Dynamic Programming with Recursive Utility Using First-Order Conditions

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.09461v1
**Captured**: 2026-07-13 01:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 3e6d45e571229a87bc563e4e9f7701d2

## Summary
The paper introduces CEFOL (certainty-equivalent first-order learning), a deep-learning
method for solving dynamic programming problems where the agent has recursive
(Epstein-Zin-style) rather than standard expected utility — a setting that's hard because
the nonlinear certainty-equivalent term inside the Bellman equation is difficult to
evaluate. CEFOL trains a separate neural network just to represent the certainty
equivalent, alongside networks for the value function, policy function, and Lagrange
multipliers, and fits them all by minimizing residuals from the Bellman equation and the
model's first-order/KKT conditions — which lets it handle occasionally-binding constraints
natively without penalty-function hacks. Tested on risk-sensitive and Epstein-Zin
consumption-saving problems, a small-noise robust-control problem, and a DSGE model with
recursive preferences and stochastic volatility, the learned solutions match classical
value-function-iteration benchmarks with out-of-sample residuals on the order of 1e-4 to
1e-3.

## Why it might be useful
This is a numerical-methods paper for solving macro/finance dynamic-programming models
(consumption-saving, DSGE) via deep learning — it targets a completely different problem
than anything in this repo, which does empirical backtesting of trading signals rather than
structural-model solving. It has no tie to Strategy A/B/C's known gaps, no tie to the
HAC/AMTP/DSR/walk-forward/bootstrap toolkit, and no tie to the feasibility-gate or synthesis
automation, which operate on historical return series rather than solving Bellman equations.
There is no dynamic-programming or optimal-control component anywhere in this repo's current
strategy set.

## Extracted content
No code or formulas in the excerpt. Numeric claim preserved: out-of-sample Bellman and
first-order/Euler residuals generally in the range 1.0e-4 to 1.0e-3 across the tested
applications.

## Action proposed
REFERENCE — structural dynamic-programming/DSGE numerical method with no application to
this repo's empirical, signal-based research process.
