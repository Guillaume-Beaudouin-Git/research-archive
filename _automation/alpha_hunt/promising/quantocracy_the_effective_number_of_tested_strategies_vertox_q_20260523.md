# The Effective Number of Tested Strategies [Vertox Quant]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=slMTiCRhwO&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: d6e6d79477bf6a21df5f8e20cba014a3

## Summary
Vertox Quant presents a measure of "effective number of strategies tested in-sample" — a metric that accounts for the correlation structure among tested strategies. Rather than counting raw test count N, the effective N adjusts for the overlap between strategy variants: if all tested variants are highly correlated (same signal, different parameters), the effective N is much lower than the raw count. This effective N feeds into multiple-testing corrections more accurately than raw test count.

## Why it might be useful
CRITICALLY relevant to Algo_claude's AMTP requirement: CLAUDE.md records n_tests = 134+ in the research history. But how many of those 134+ tests are truly independent? Strategy C alone went through 10 iterations (iter_1 through iter_10), each highly correlated with the previous. If the effective N for Strategy C's iteration history is 3 rather than 10, the AMTP p-value threshold changes significantly. Concretely: compute effective N for the Strategy C test history using the correlation matrix of the iteration backtest returns, then recheck whether the current iter_10 Sharpe of 1.52 clears the AMTP-adjusted threshold. This could validate or challenge the current walk-forward claim. Also applies to Strategy A (3 iterations mapped to v1→v2→v3) and the full 134-test history.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for the effective-N formula.

## Action proposed
TEST_NOW

Read full article, extract the effective-N formula. Apply to Strategy C's 10-iteration history: compute correlation matrix of iter returns, calculate effective N, re-run AMTP with corrected N. Half-day implementation. Data available in existing backtest outputs.
