# Building a Robust Portfolio with Risk Parity

**Source**: quantinsti
**URL**: https://blog.quantinsti.com/risk-parity-portfolio/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 9a892257fa2453b7f7378eba9c114a77

## Summary
A practical Python guide to risk parity portfolio construction, comparing equal-capital-weight versus equal-risk-contribution (ERC) allocation. The article walks through computing covariance matrices, inverse-volatility weighting, and iterative ERC solvers, with benchmark comparisons showing that risk parity typically reduces drawdowns and smooths volatility contributions across assets relative to the naive 1/N portfolio.

## Why it might be useful
ERC allocation is the current method used in Algo_claude's theoretical A+B+C portfolio (Sharpe 2.24, MaxDD -1.0%, ERC: A=10%, B=68%, C=22%, per CLAUDE.md Portfolio context). The Python implementation described here would be useful for validating or rebuilding the `Portfolio/state/portfolio_state.py` ERC weight calculation. Two specific checks: (1) confirm that Strategy A's 10% ERC weight correctly reflects its higher volatility relative to Strategy B (delta-neutral, near-zero realized vol) and Strategy C (NQ futures); (2) verify that the covariance matrix used for ERC is rolling (not static), since static covariance between crypto and NQ futures can change dramatically in risk-off regimes. The "58-year risk parity audit" item (quantocracy_where_risk_parity_hurts...) in this run provides the complementary stress-test perspective.

## Extracted content
No code in excerpt. Full article contains Python implementation — retrieve for code extraction.

## Action proposed
TEST_LATER — Use the Python ERC solver from the full article to independently verify the A+B+C portfolio weights in Portfolio/state/portfolio_state.py. Add a rolling 30-day covariance input to detect regime shifts. 1-day effort. Hard-fail path (touches `Portfolio/`) — requires human review per CI rules.
