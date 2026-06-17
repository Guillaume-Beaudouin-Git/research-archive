# Feature Selection: Filter-Based Methods for Trading Signals

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=4qxF5YIn84&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 4d7ed8ac18e67c6e6c43fbbc5ba9db7d

## Summary
The piece challenges the assumption that more data always means better predictive power in financial contexts. It introduces filter-based feature selection methods — techniques that evaluate each predictor independently of a model, using statistical criteria like correlation, mutual information, or variance — as a first-pass triage step before model fitting. The argument is that irrelevant features add noise and overfit; a small set of statistically relevant features outperforms a kitchen-sink approach.

## Why it might be useful
This is most applicable to the Strategy D research in `Futures/research/active/strategy_d/` (D3+D5, N_test=156/158). D3 and D5 were built from NQ intraday signals; if there's a grid of candidate features (time-of-day, momentum, BB squeeze parameters), filter-based selection run before the walk-forward WF would reduce the multiple-testing load and be more defensible with AMTP. The sector_hothand audit (`_audit/sector_hothand_audit_2026-05-30.md`) is a second application: if many sector momentum variants were tested, a filter pass on IC t-stats would quickly identify which survived. Note that filter-based methods assume feature independence, which is violated for financial returns — block-bootstrap IC testing (Politis-Romano) is a sounder filter criterion for this context than naive correlation thresholds.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Useful as a reminder to apply pre-selection on feature grids before WF (e.g. Strategy D iterations), but the Algo_claude toolkit (HAC t-stat IC filter, AMTP) already covers this ground more rigorously than standard filter methods.
