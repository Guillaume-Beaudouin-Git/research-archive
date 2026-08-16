# Feature Selection: Wrapper-Based Feature Selection Methods

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=EWsD5aY4Ba&amp;source=feedburner
**Captured**: 2026-07-13 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 1c8c9b74d9a1f85c3cf45de5f13a2de7

## Summary
The post argues that feature selection in systematic trading research is
usually treated too casually — as a quick pruning step of "weak" variables —
when it should instead be approached as a research process in its own right.
It sets up wrapper-based methods (which select feature subsets by iteratively
evaluating actual downstream model performance) as distinct from cheaper
filter-based methods (which score features independently via correlation-type
statistics), implying the wrapper approach is more rigorous but more
expensive and more exposed to overfitting if not controlled carefully.

## Why it might be useful
Wrapper-based feature selection is, by construction, an iterative search over
many feature-subset "hypotheses" evaluated against the same data — exactly
the kind of implicit multiple-testing exposure the repo's AMTP/DSR discipline
(hard rule: AMTP when n_tests>1; L20: DSR mandatory once n_mod>=2) exists to
catch. It's directly relevant to `_automation/feasibility` gate B (walk-forward
+ bootstrap + DSR), since any future hypothesis handler that does feature
search internally would need its search trials counted toward n_tests/DSR,
not treated as a free pre-processing step. It also reinforces the honesty
checklist in L46 for any propfirm-adjacent backtest that used wrapper
selection to arrive at its feature set.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article
needed for further extraction.

## Action proposed
REFERENCE
