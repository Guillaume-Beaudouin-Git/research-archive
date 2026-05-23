# Why Momentum Investing Has Been Struggling — And What Volatility Has to Do With It [Alpha Architect]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=91n57Nmh4A&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 67305d635bfab005d7fc5d5dad416fba

## Summary
Academic research by Haim Mozes connects volatility spike events to the underperformance of momentum strategies, particularly the long/short variety. The mechanism: sudden vol expansion reverses momentum leaders faster than the signal can adapt, causing momentum crashes that disproportionately hit the long side. The study covers the past decade of momentum underperformance and finds vol-spike frequency explains most of it.

## Why it might be useful
Critical context for Strategy A (crypto TSMOM v3, tanh signal, long-only): the long-only constraint means Strategy A avoids the short side of momentum crashes, but crypto vol spikes are frequent and extreme. The 28-bar vol window in Strategy A may lag vol spikes by 2-4 weeks, causing position sizing to be too large going into a crash. This is precisely the scenario where EGARCH (item 05) would improve the vol estimate. Concretely: backtest Strategy A with vol-spike regime filtering (e.g., don't enter when 5-day realized vol > 2x 28-day realized vol) and measure the effect on MaxDD vs Sharpe tradeoff. The PROPFIRM_PASS gate (MaxDD<-10%) would benefit from this filter.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Haim Mozes' study cited as primary reference — retrieve full study for methodology.

## Action proposed
TEST_LATER

Implement vol-spike regime filter for Strategy A v4: no new position when 5-day realized vol > 2x trailing 28-day vol. Test with walk-forward ≥5 folds. Data in data/raw/. Counts as modification #1 toward 3-mod cap if EGARCH not chosen first.
