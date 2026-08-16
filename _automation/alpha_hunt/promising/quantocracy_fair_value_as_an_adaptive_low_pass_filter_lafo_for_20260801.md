# Fair Value as an Adaptive Low-Pass Filter: LAFO for Mean Reversion

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=xe1CfugDLl&source=feedburner
**Captured**: 2026-08-01 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e89bce0b4d726c5e94fcee126b2e4b7c

## Summary
Aligrithm proposes "LAFO" (the excerpt implies an adaptive low-pass filter) as a replacement anchor for the "fair value" concept underlying mean-reversion strategies, in place of static or fixed-window moving averages. The framing argument is that any fixed "fair value" benchmark is essentially an assumption dressed up as a fact, and that a low-pass filter which adapts its responsiveness to market conditions should track a more defensible notion of fair value than a lagging fixed-window average, reducing spurious reversion signals generated when the anchor itself lags too much or too little.

## Why it might be useful
This bears most directly on Strategy B: the live 8h-rotation delta-neutral carry config is currently negative (SR ≈ -114 per the CLAUDE.md ledger), while a slower ≥10-day rotation variant is flagged as the "hypothèse vivante" with data already available. An adaptive low-pass fair-value anchor is exactly the kind of half-life-responsive mechanism that could replace a fixed rotation window in redesigning B's entry/exit timing. That said, L29 explicitly cautions that "holding calé sur la half-life est nécessaire non suffisant" — an adaptive filter that reduces noise does not by itself create expected value, so any application would still need to clear the same WF ≥5-fold and block-bootstrap bar the rest of B's redesign is held to before being cited.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — plausible relevance to the Strategy B rotation-speed redesign, but requires replicating the LAFO filter and backtesting it against B's viable-asset carry data first; no immediate one-day implementation path.
