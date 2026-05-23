# Overfitting and Parameter Selection in Trading Strategies [Relative Value Arbitrage]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=xEkmGncXCy&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: c64e2f0d0d57fc33722cabb6367c58d4

## Summary
Relative Value Arbitrage revisits overfitting in parameter selection, arguing that the risk is systematic and underappreciated even among experienced quants. The article provides a framework for distinguishing genuine parameter sensitivity (where the right value matters and backtest tuning helps) from fragile optimization (where the "optimal" parameter just cherry-picks a favorable sample window).

## Why it might be useful
Directly relevant to Strategy C (NQ opening momentum iter_10): the strategy has iterated 10 times with specific parameters (1.5R TP, 0.5R SL, 30pt ORB minimum, 1.2% gap cap, 12:30 time stop). With 346 backtest trades and 9 walk-forward folds, the risk of parameter-specific overfitting is real. The CLAUDE.md AMTP requirement (n_tests = 134+, counting all research tests) applies, but within Strategy C's own iteration history, a parameter sensitivity analysis would complement the walk-forward result. Run robustness checks: how does Sharpe change if TP is 1.3R or 1.7R, if ORB min is 20pt or 40pt? The DSR (Deflated Sharpe Ratio) is the correct tool here given >5 modifications (iter_10).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Run parameter sensitivity grid on Strategy C: vary TP (1.2-1.8R), SL (0.4-0.6R), ORB min (20-40pt) and report DSR-corrected Sharpe across the grid. This confirms or challenges the iter_10 parameter set before paper trading. 1-day effort with existing NQ data.
