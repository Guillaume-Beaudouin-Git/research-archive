# Skill or Luck? We Ran 100 Million Bitcoin Backtests to Show You How to Tell

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=HcBjWwuT9Y&source=feedburner
**Captured**: 2026-07-11 06:00 UTC
**Filters passed**: L1=[trading_topic, metrics, methodology], L2_OK
**Hash**: e62587d048b15f8903f47a97d5261fc9

## Summary
Rulyfi generated 100 million bitcoin backtest variants to illustrate the Deflated Sharpe Ratio (DSR) in practice, explaining that DSR rescales a strategy's Sharpe ratio for how many strategies were tried and sets the passing bar not at zero but at the best Sharpe expected purely from chance given that trial count. The excerpt cuts off mid-explanation of exactly how that bar is computed, but the framing (massive search space, best-of-N under the null) matches the standard Bailey-López de Prado construction the project already cites in its methodology toolkit.

## Why it might be useful
This is a crypto-specific illustration of exactly the failure mode the project's own crypto research has flagged: L21 sets expected Sharpe ranges by strategy category (delta-neutral carry crypto 1.5-4.0) and flags anything more than 2x that range for DSR/cherry-pick audit, while L14 already ruled Strategy B's raw testnet Sharpe of 9.64 inadmissible (N<250) and proxied it down to 2.0. A 100-million-variant demonstration of how easily a large search space inflates apparent skill is a useful sanity re-check for Strategy A's now-current live excess Sharpe of 0.566 (IC95 contains zero) and for any future crypto momentum/carry variant before it gets folded into the n_tests ledger — particularly since L11/L45 already closed the long-only and CFD-TSMOM crypto families on mechanistic grounds, and this piece is a reminder to distinguish a mechanistic kill from a search-space artifact.

## Extracted content
"The Deflated Sharpe Ratio (DSR) adjusts a strategy's Sharpe for how many strategies you tested. It sets the bar not at zero, but at the best S[harpe expected under the null]" — quoting the excerpt as given, cut off mid-sentence. The headline claims a search of "100 Million Bitcoin Backtests" as the demonstration's scale.

## Action proposed
REFERENCE — a DSR methodology explainer applied to crypto backtests, useful as a cross-check on the project's existing DSR practice, but it proposes no tradable signal and has no direct implementation path.
