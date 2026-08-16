# Bivariate Isotonic Regression by Dynamic Programming

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.12629v1
**Captured**: 2026-07-15 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b82caf6b1d307df3b92d51b1cf64c649

## Summary
Extends a known dynamic-programming algorithm for univariate isotonic (monotone) regression to the bivariate case via an anti-diagonal traversal procedure, demonstrated on a baseball salary dataset. Framed as one instance of the broad applicability of dynamic programming in economics (savings, growth, job search, business cycles, recursive contracts, forecasting).

## Why it might be useful
Isotonic regression is relevant to signal calibration — the project's TSMOM diagnostics require quintile-monotonicity checks (methodology toolkit item 4) and the propfirm barrier/p(pass) simulator effectively needs a monotone mapping between a sizing/regime variable and outcome probability. A bivariate (two-signal) isotonic fit would let a monotonicity check run jointly on two conditioning variables at once (e.g., signal strength x regime flag) instead of one at a time, closing part of the gap L54 exposed (a regime overlay that predicted variance correctly but not the mean in the right direction) by directly testing monotonicity of E[return | signal, regime] rather than assuming it.

## Extracted content
No code (algorithm described, not reproduced) — application is a baseball salary dataset, not finance. No numeric claims transferable to trading.

## Action proposed
REFERENCE.
