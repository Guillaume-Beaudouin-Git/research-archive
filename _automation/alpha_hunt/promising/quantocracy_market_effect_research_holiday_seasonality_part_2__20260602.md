# Holiday Seasonality in Systematic Markets — Part 2

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=fjoFWV57k5&source=feedburner
**Captured**: 2026-06-02 06:06 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: dacb858f11d59f8e825b2b0a832a6d78

## Summary
The second part of a TradeQuantiX series on calendar seasonality around holidays in financial markets. The series targets systematic traders and frames holiday-driven return patterns as an implementable filter for strategies. The excerpt truncates before any empirical findings are shown — no holiday list, no magnitude of effects, no statistical methodology is revealed.

## Why it might be useful
Pre-holiday drift and post-holiday mean-reversion are well-documented anomalies (Lakonishok & Smidt 1988, Fields 1934). For Strategy C (NQ ORB, `Futures/live/strategy_c_live/`), paper trading is pending and the signal engine is not yet live. Adding a holiday calendar filter to `signal_engine.py` is a zero-cost modification to test before paper start: NQ on pre-holiday sessions tends to have compressed ranges and lower volume, which directly degrades the ORB signal quality and increases adverse fill risk near SL (L19). Concrete test path: extract the holiday calendar from the full article, add a `trading_day_type` column to the NQ 1-min dataset (`Dataset_NQ_1min_2022_2025.csv`), re-run walk-forward excluding pre-holiday sessions, and check whether the remaining N≥300 trades still yield WF≥7/9. Apply AMTP since this is modification #1 of the 3-mod budget for Strategy C post-backtest. Note: L15 caution — calendar overlays on SR>1.0 strategies provide limited lift (~1.7%/yr); only pursue if the exclusion removes demonstrably adverse sessions, not just to improve in-sample SR.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — Full article needed to identify exact holiday list and effect sizes claimed. Low-cost modification candidate for Strategy C signal engine before paper trading starts.
