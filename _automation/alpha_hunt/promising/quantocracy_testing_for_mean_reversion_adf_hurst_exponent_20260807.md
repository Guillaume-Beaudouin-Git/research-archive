# Testing for Mean Reversion: ADF, Hurst Exponent and Half-Life

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=1fjWIeYoHi&source=feedburner
**Captured**: 2026-08-07 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 3ebec81535cc07940addcec54611b042

## Summary
The piece lays out the standard three-part toolkit for confirming a time series is genuinely mean-reverting rather than just noisy or trending: the Augmented Dickey-Fuller test for stationarity, the Hurst exponent to quantify the strength/direction of reversion (vs. trending or random-walk behavior), and half-life estimation (typically via an Ornstein-Uhlenbeck fit) to derive the natural holding period implied by the series' own reversion speed. The framing emphasizes that true mean reversion requires a well-defined, stable unconditional long-run level the process reliably returns to — not just any series that occasionally dips and recovers.

## Why it might be useful
This is precisely the diagnostic chain the project already needs but doesn't explicitly script: L29 states "holding calé sur la half-life = nécessaire non suffisant" (half-life-calibrated holding removes a confounder but doesn't create EV on its own) — this article describes exactly the ADF+Hurst+half-life pipeline that produces that holding-period input, and its own warning that "necessary not sufficient" matches. It applies directly to two open active-research lines: `Futures/research/active/zn_baltussen/` (ZN mean-reversion candidate) and `Forex/research/active/fx_intraday_deepdive/`, both of which need a rigorous mean-reversion pre-screen before any signal-building modification is spent (protecting the DSR budget per L48 — every avoidable re-test protects all subsequent candidates' multiple-testing correction).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_NOW

Run an ADF + Hurst exponent + half-life diagnostic script (statsmodels `adfuller` + a standard Hurst estimator, <1 day to write) directly on the ZN series already staged for `Futures/research/active/zn_baltussen/`, as a pre-screen gate before any further modification is spent on that hypothesis.
