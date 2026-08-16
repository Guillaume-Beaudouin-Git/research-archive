# The Random-Max Percentile: Grading Every Backtest Against Its Search's Random Maximum

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=R0pkGjM251&amp;source=feedburner
**Captured**: 2026-07-15 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: c26128ec9c1887880def47570ed29d42

## Summary
Rulyfi introduces "Random-Max Percentile" (RMP), a new metric attached to each row of their
strategy-scan results and paid-plan exports. RMP reports the probability that the best
result obtainable from a purely random search over the same parameter/rule space would
exceed the observed backtest's performance — effectively a per-strategy overfitting/luck
gauge benchmarked against the null distribution of "best of N random draws" rather than a
single null strategy. The excerpt cuts off before describing the exact computation or
worked examples.

## Why it might be useful
This is a direct methodological analog to the DSR (Bailey-Lopez de Prado) discipline this
repo already enforces per L20 (mandatory once n_mod≥2, degrading a naive 1.52 Sharpe to
~1.0-1.1) and to the AMTP hard rule for n_tests>1 — RMP is essentially a resampling-based
alternative to the closed-form DSR/PSR correction, benchmarking against the max of a random
search rather than the expected max of N independent trials. It is concretely relevant to
`_automation/feasibility`'s gate B (walk-forward + bootstrap + DSR): if RMP's construction
is more robust than the current DSR estimate for search-heavy hypotheses (e.g. the ORB
Strategy C iterations, iter_10, or the feasibility pipeline's handler grid searches), it
could be implemented as a supplementary sanity check in that gate, comparing its verdict
against the existing AMTP/DSR numbers for a few already-tested items (e.g. Strategy C
iter_10's known DSR degradation) as a validation case.

## Extracted content
No code or formulas given in the excerpt; the article promises a "Key Takeaways" list
whose content is cut off before any numbers appear. No specific numeric claims present.

## Action proposed
TEST_LATER — implementing or replicating RMP as a check inside `_automation/feasibility`
gate B requires reading the full methodology (exact random-search construction, percentile
computation) and building/validating it against known cases like Strategy C iter_10, a
1-3 day effort rather than a same-day addition.
