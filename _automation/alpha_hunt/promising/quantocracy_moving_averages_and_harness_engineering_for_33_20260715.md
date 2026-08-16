# Moving Averages and Harness Engineering for +33% CAGR on Portfolio Optimization

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=RnSDEgi5nB&source=feedburner
**Captured**: 2026-07-15 07:00 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 88db3ed63bf902cb23337adc9eff846e

## Summary
The post (Paper to Profit) opens by framing moving averages as a beginner trap: traders keep chasing a mythical MA variant that is simultaneously smoother and more responsive, predictive rather than reactive. It then pivots to what the author calls "harness engineering" — presumably a testing/evaluation framework wrapped around MA-based signals — applied to a portfolio-optimization context, with a headline claim of +33% CAGR. The excerpt cuts off before describing the actual mechanism, so neither the MA variant nor the "harness" methodology is specified here.

## Why it might be useful
Strategy A's live signal is itself a smoothed momentum construction (`tanh(cumret_28d / (vol_28d × sqrt(28)))`), and its live excess Sharpe has been recalculated to 0.566 with a 95% CI of [-0.50, 1.63] that contains zero — any claimed improvement to an MA/momentum blend is a candidate to probe that gap, but only after passing the same walk-forward ≥5 folds and HAC lag-6 significance bar the project requires everywhere. Before trusting any "harness" that blends multiple MA signals, L37's filter sanity check applies directly: if sign(new blended signal) disagrees with the native momentum signal less than 5% of the time, the blend is cosmetic rather than a real improvement. A +33% CAGR headline with no cost, drawdown, or fold count in the excerpt is also a textbook case for L20 (DSR mandatory once more than one variant is tried) and the n_tests ledger discipline before any number from this post could be cited internally.

## Extracted content
The description text repeats the article's headline claim verbatim: "+33% CAGR on Portfolio Optimization." No supporting Sharpe, drawdown, sample size, cost assumption, or code is present in the excerpt — the CAGR figure is a bare headline number with no context for how it was computed.

## Action proposed
TEST_LATER — the excerpt gives no code, formula, cost assumption, or fold structure, so the actual mechanism (and whether it survives HAC/walk-forward) can't be assessed without reading the full article first.
