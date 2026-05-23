# How to Manage an Intraday Trend Trade [Concretum Group]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=m4te4DxpUO&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 0916de776b2f6c8d24c3040b5be14dd0

## Summary
Concretum Group describes their live experience managing intraday trend positions across multiple speeds — from slower multi-day systems to faster intraday signals. The article addresses exit management once a trend position is established: when to trail the stop, when to take profit early, and how to handle the decay of intraday momentum as the session progresses. The framework emerges from their actual book management rather than backtest optimization.

## Why it might be useful
Directly applicable to Strategy C (NQ opening momentum iter_10, paper trade pending): current exits are hard-coded at TP=1.5R, SL=min(0.5R, 20pts), time stop=12:30 ET. A trailing-SL approach (e.g., trail to 0.5R after reaching 1R) could improve the win rate's contribution to Sharpe without adding a new filter — and would be the most defensible modification given iter_10 is already at the hypothesis complexity boundary. The KNOWN GAP (VWAP 1-min vs 5-min) affects entry signal, not exit management — so exit improvements can be evaluated independently. Cross-reference with the archived "NQ afternoon momentum (4 iter)" to ensure a trailing stop doesn't extend trades into the afternoon reversal zone.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Read full article for trailing exit framework. If trailing-SL approach is described, implement as a modification on Strategy C using the existing backtest data. Counts as one of 3 remaining modifications. 1-day effort.
