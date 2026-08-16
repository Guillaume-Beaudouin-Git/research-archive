# How Many Backtests Is Too Many? We Ran the Same Search Twice to Find Out

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=4m3pZdOXzq&source=feedburner
**Captured**: 2026-07-11 06:00 UTC
**Filters passed**: L1=[trading_topic, metrics, methodology], L2_OK
**Hash**: 35dee411c04b65d04ca20e72b3fb147d

## Summary
Rulyfi ran an identical strategy search-and-select process twice (same trades, bit-for-bit) and got different verdicts depending on how the surrounding scan was scoped: in one framing the strategy's deflated Sharpe came out to 0.035 inside a search space of 21.9 million trials (essentially indistinguishable from luck), while in another framing the same trades scored close to real skill. The piece is a demonstration that deflated-Sharpe verdicts are not a property of the strategy alone but depend heavily on how the "number of trials" denominator is counted. The excerpt cuts off before stating the resolution/recommendation.

## Why it might be useful
This is a direct stress test of the exact mechanism the project already relies on: L20 mandates DSR from N_mod ≥ 2 (the iter_10 NQ strategy went from a naive Sharpe 1.52 down to 1.0-1.1 once deflated), and the "5 mandatory script fixes" require honest naming of any multiple-testing correction (`approx_multi_test_penalty`, not "DSR" unless the full Bailey-López de Prado machinery is used). The finding that the SAME trades can grade as luck or skill depending on trial-count framing is a warning specifically relevant to the project's own n_tests ledger (global count fixed at 321, with local per-program counters reconciled at closure) — if the denominator convention is inconsistent across `_meta/n_tests_ledger.md` reconciliations, DSR/AMTP numbers already cited for Strategy A/B/C could be similarly framing-dependent. Worth reading in full before the next DSR computation to confirm the trial-count denominator used in `Portfolio/` or `Futures/research/` scripts is counted the same way the article warns against.

## Extracted content
"A single strategy, its trades bit-for-bit identical, grades as luck in one scan (deflated Sharpe 0.035, inside a 21.9M-trial search) and close to real" [excerpt cuts off before completing the contrast].

## Action proposed
REFERENCE — this is a methodology-validation piece about DSR trial-counting, not a testable trading signal; it has no direct implementation path onto an active strategy, only a caution to apply the next time DSR/AMTP is computed.
