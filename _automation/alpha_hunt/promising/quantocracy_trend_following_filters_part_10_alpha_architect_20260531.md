# Trend-Following Filters Part 10 — Alpha Architect (DSP Perspective)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=KfCKDKU12D&source=feedburner
**Captured**: 2026-05-31 08:06 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: a295e0caa370c02e384774d38bc0f0be

## Summary
Alpha Architect continues their series on trend-following filters viewed through a digital signal processing (DSP) lens. Parts 7 and 9 examined filters in the time domain; Part 10 continues this analysis. The DSP framing reinterprets moving averages, momentum windows, and signal smoothers as finite impulse response (FIR) or infinite impulse response (IIR) filters with specific frequency-domain properties — pass-bands, stop-bands, phase lag, and roll-off. This perspective offers principled tools for choosing signal window lengths rather than tuning by backtest.

## Why it might be useful
Strategy A (TSMOM v3) is built on a tanh-normalized 28-day cumulative return signal, which is essentially a FIR filter with a rectangular window — known to have poor frequency-domain properties (high sidelobes). If Part 10 introduces alternative filter shapes (Hann, Butterworth, Savitzky-Golay) that reduce phase lag or improve noise rejection, they could be evaluated as candidate replacements for the 28-day window in a future Strategy A iteration. However, Strategy A is currently FROZEN (Propr breach 2026-05-11, HL testnet continuing), so any modification is blocked until the propfirm situation is resolved. More immediately applicable to Strategy D (3 mods budget, 0 consumed): if D3/D5 use any MA-based regime filter, DSP-informed filter design could improve signal-to-noise without burning a backtest iteration. Lesson 10 (max 3 mods per strategy) makes principled a-priori filter selection more valuable than empirical grid search.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. This is Part 10 of a multi-part series; Parts 7 and 9 are referenced as prior work. Full article needed for filter specifications.

## Action proposed
REFERENCE — DSP filter theory for trend-following. Bookmark for next Strategy A unfreeze decision or Strategy D regime filter design. Not actionable while Strategy A is frozen and Strategy D is at pre-registration stage.
