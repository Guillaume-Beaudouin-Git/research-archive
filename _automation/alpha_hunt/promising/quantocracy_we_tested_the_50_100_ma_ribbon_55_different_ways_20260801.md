# We Tested the 50/100 MA Ribbon 55 Different Ways Over Five Years

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=rVLaMVQOs5&source=feedburner
**Captured**: 2026-08-01 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 8ea81609beefb990de046a7513570f9c

## Summary
Another entry in "The Refutation" series, this one targets the 50/100 moving-average "ribbon" — a popular discretionary regime-identification heuristic (the gap/crossover between a 50-period and 100-period MA is read as telling a trader which market phase they're in). The author frames the piece around exhaustively testing 55 variations of the rule over a five-year window, in the spirit of exposing how fragile the heuristic is once it's forced through systematic, rather than eyeballed, evaluation. The excerpt does not disclose which variations passed or failed, only that the exhaustive-variation approach was taken.

## Why it might be useful
This is a live illustration of exactly the multiple-testing risk the project's toolkit is designed to catch: 55 rule variants tested on one five-year window is the textbook setup requiring AMTP (hard rule: "AMTP if n_tests > 1") and, since 55 ≫ 2, DSR under L20 rather than raw Sharpe reporting. It is a useful reference alongside Strategy C's own history, where an uncorrected multi-parameter search (iter_10) inflated Sharpe from a headline 1.52 down to a DSR-corrected 1.0-1.1 once N_mod ≥ 2 was properly accounted for (L20) — this MA-ribbon piece is the same failure mode in a different indicator family, and useful as a training example rather than a new signal.

## Extracted content
The excerpt states the piece "tested the 50/100 MA ribbon 55 different ways over five years" — a specific claim about test count (55 variants) and sample window (5 years), though no resulting Sharpe/win-rate figures are given in the excerpt.

## Action proposed
REFERENCE
