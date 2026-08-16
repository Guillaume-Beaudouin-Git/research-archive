# From Backtest to Benchmark: Validating New Strategies with Quantpedia API

**Source**: quantpedia
**URL**: https://quantpedia.com/from-backtest-to-benchmark-validating-new-strategies-with-quantpedia-api/
**Captured**: 2026-07-27 21:30 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 4c929ed7bf50ec0d5d93582820d4093b

## Summary
The article argues that a clean backtest is not sufficient to establish that
a strategy is genuinely novel rather than a repackaged version of a known
factor, timing rule, or macro exposure — a strategy can have good risk-adjusted
stats and a logical rule while still just being a disguised trend-follower or
vol filter. It proposes using the Quantpedia API as a benchmark: comparing a
new backtest against Quantpedia's documented strategy universe to find its
nearest neighbours, assign it to a factor cluster, compute a "uniqueness
score," and generate a robustness report. The stated goal is a structured
redundancy check that complements, not replaces, human research judgment.

## Why it might be useful
This maps almost directly onto a gap in the repo's own process: the
"DO NOT re-propose" registry in `research_history.md` and the closed-family
list (L11 long-only crypto CS, L43 FX intraday reversal, L28/L32/L32b/L36
CFD carry, L50 funding-contrarian) are currently checked manually/by grep at
evaluation time, per lesson L48's caution that path-limited greps produce
false negatives. An automated nearest-neighbor/uniqueness-score check against
a documented strategy taxonomy is exactly the kind of extra gate that could
sit in front of `_automation/feasibility` gate A, flagging when a new
alpha-hunt candidate is functionally identical to an already-closed family
before it consumes a test slot (protecting the DSR of subsequent candidates,
per L48). It also parallels the theme-clustering `_automation/synthesis`
already does across papers in `_state.json`, just benchmarked against an
external taxonomy instead of internal history.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt beyond the
described workflow steps (nearest-neighbour lookup, factor-cluster
assignment, uniqueness score, robustness report) — no exact metrics or
formulas are given. Full article needed for further extraction.

## Action proposed
TEST_LATER — this is a promising automation-infra addition (a redundancy
check ahead of feasibility gate A), but it depends on access to and terms of
the Quantpedia API (unconfirmed) and would need integration work into
`_automation/feasibility`, putting it past a same-day implementation.
