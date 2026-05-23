# "Surfing the Equity Curve": Using Trend-Following to Switch Strategies On and Off [Allocate Smartly]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=G93W5HZYZv&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 189c9887603cdee7ff8e00c13122603a

## Summary
Third installment in a TAA performance-selection series. This approach applies a trend-following filter to each strategy's own equity curve — when a strategy is below its moving average of cumulative P&L, it's switched off; when above, it's switched on. The article tests whether this equity-curve surfing reduces drawdowns or improves Sharpe for TAA strategy combinations.

## Why it might be useful
Directly applicable to Strategy A (crypto TSMOM, PAUSED after propfirm breach): applying an equity curve trend filter on top of the TSMOM signal is a natural extension that could have prevented trading during the drawdown that caused the propfirm breach. However, CLAUDE.md limits modifications to 3 per strategy — and this would be one modification toward that cap. More importantly, if the equity curve filter is applied during walk-forward, it must not use future knowledge of the final equity curve (look-ahead risk that the Vertox Quant stress-test framework in item 01 would catch). For the propfirm book, this aligns with the PROPFIRM_PASS gate: MaxDD<-10%, and equity curve surfing specifically targets drawdown reduction.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Evaluate equity-curve trend filter for Strategy A v4 (counts as 1 modification toward 3-mod cap). Must implement cleanly in walk-forward without look-ahead. Read full article for implementation details first.
