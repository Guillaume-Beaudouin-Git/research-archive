# Intraday Breakout Details That Matter: Exits, Slippage and 0DTE Options (Cracking Markets)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=Cawsw33eNU&amp;source=feedburner
**Captured**: 2026-07-10 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 573462c6c0630befe0dc2c1d1c2bc4ee

## Summary
The author argues that a simple intraday volatility-breakout signal can work well on paper, but that live performance is dominated by implementation details rather than the entry signal itself: how the trade is exited, how slippage is modeled/realized, and whether a 0DTE options overlay is used instead of (or alongside) the underlying. The framing is that most of the edge or its erosion lives in exit mechanics and cost realism, not in the breakout trigger. The excerpt cuts off before any concrete exit rule, slippage figure, or backtest result is given.

## Why it might be useful
This lands squarely on Strategy C's known gap: the NQ opening-range-breakout is an intraday volatility breakout with a fixed exit (TP 1.5R, hard stop 12:30 ET), currently cancelled only for vehicle reasons (FTMO doesn't support CME futures) but explicitly kept reusable under the 2026-07-30 propfirm-reopening policy (L51) if Apex/Topstep/MyFundedFutures gets re-evaluated. It also directly matches lesson L59 (delay+1 only certifies the entry — the exit/stop fill must be re-priced separately; 25% of stop bars in the repo's own gap-pattern audit opened beyond the stop) and L19 (NQ slippage baseline 4 ticks RT, up to 3x on adverse fills, asymmetric). Concrete test if C is reopened: re-run iter_10's exit rule against 1-2 alternative exit variants from this piece with L19-calibrated stressed slippage, and check whether the current TP1.5R/stop12:30 combination is itself contributing negative edge under L59's stricter fill assumption.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — direct conceptual fit to Strategy C, but C currently has no funded vehicle (Tradeify/FTMO both closed to it), so testing only makes sense contingent on a futures-friendly propfirm re-evaluation; prototyping alternate exits against the existing Databento NQ dataset is a 1-3 day job once that vehicle question is resolved.
