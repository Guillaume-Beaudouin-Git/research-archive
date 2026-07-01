# One of These Things Is Not Like the Others. Or Is It? Pooling Rule P&L Estimates [Investment Idiocy]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=au02cgng5c&amp;source=feedburner
**Captured**: 2026-07-01 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 2c5cbf900afb809ad3109c8afc21b121

## Summary

Eighth post in Carver's portfolio-optimisation series, addressing whether individual trading-rule P&L estimates should be pooled across rules/instruments (shrinking toward a common estimate) rather than treated as fully independent, when combining a portfolio of rules with limited per-rule sample history. The excerpt is an intro paragraph and doesn't yet state the recommended pooling method or a numeric example.

## Why it might be useful

This maps directly onto the open Strategy D construction problem: D3 (opening-range mid-fade, n_test=156) and D5 (afternoon BB-squeeze breakout, n_test=158) both failed individually (Sharpe -1.08 / -1.32) and are under study as a combined portfolio with a regime filter (budget: 3 mods, 0 consumed, pre-registration in progress per `Futures/research/active/strategy_d/hypotheses_preregistered.md`). Estimating the combined D3+D5 Sharpe from two short, noisy, individually-negative histories is precisely the "pool vs. treat-independently" problem this post addresses — a shrinkage/pooling estimator would give a more honest combined-Sharpe estimate than naively summing two per-rule estimates, which is relevant before committing any of the 3-mod budget to the regime filter. Also connects to the AMTP/DSR discipline in CLAUDE.md's methodology toolkit: pooling rule estimates is an alternative (or complement) to multiple-testing correction when the rules share structure.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

Concrete fit to Strategy D, but the excerpt doesn't contain the pooling methodology itself — need the full post to know which shrinkage estimator Carver proposes before applying it to the D3+D5 combination. Read before committing budget to the regime-filter modification.
