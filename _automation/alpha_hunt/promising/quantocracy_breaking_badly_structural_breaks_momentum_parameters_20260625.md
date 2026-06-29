# Breaking Badly: Detecting Structural Breaks in Momentum Strategy Parameters

**Source**: quantocracy (via Investment Idiocy)
**URL**: https://quantocracy.com/redirect.php?key=AtXqCuhVKg&source=feedburner
**Captured**: 2026-06-25 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 2c97c5fa90c54e7fbe225159f5a6aed6

## Summary
This article examines how the performance of different lookback speeds within momentum strategies shifts over time, using cumulative P&L curves as visual and statistical evidence of structural breaks. The central argument is that parameter estimates for trend-following (e.g., the optimal lookback window, signal scaling) are not stationary — they shift at detectable breakpoints. The article apparently discusses methods for identifying when the estimated parameters have meaningfully changed, which has implications for when to refit versus freeze strategy parameters.

## Why it might be useful
Directly relevant to Strategy A (TSMOM v3) which uses a 28-day fixed lookback window frozen since 2026-05-30. The CLAUDE.md status shows Strategy A is in a propfirm-frozen state, but for future TSMOM parameter reviews, knowing whether the 28-day lookback has experienced a structural break since the original backtest period would inform whether the freeze should be maintained or the parameter reconsidered. Specifically: run a Bai-Perron structural break test on the `tanh(cumret_28d / (vol_28d × sqrt(28)))` signal's IC series over the full Binance history to check for regime shifts. The test would be a one-shot diagnostic (no modification count consumed per CLAUDE.md max-3-mod rule). Also relevant to the archived cross-sectional momentum literature (CS momentum G10 dead post-Menkhoff) — the structural break methodology might explain exactly when the G10 TSMOM edge disappeared.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt (the article mentions a "cumulative p&l from different speeds of momentum over time for portfolio" chart). Full article needed for further extraction.

## Action proposed
TEST_LATER — Run Bai-Perron structural break test on Strategy A's 28-day IC series as a one-shot diagnostic before any future parameter review. Requires pulling full Binance daily history (already in `data/raw/`). Estimated 0.5 days. Not urgent while A is frozen; relevant when Propr account status changes.
