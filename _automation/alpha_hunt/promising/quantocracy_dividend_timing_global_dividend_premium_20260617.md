# Dividend Timing and Global Dividend Premium

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=WDsgJW8MS2&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e64f72d8882fd0dc89c43e890723fb91

## Summary
The paper argues that the timing of dividend payments — specifically when during a calendar year a company pays dividends relative to peers — is a surprisingly robust predictor of cross-sectional equity returns. This is a distinct mechanism from the dividend yield or dividend growth factors; it's about the fiscal timing pattern creating a systematic premium ("global dividend premium") across multiple markets.

## Why it might be useful
The sector_hothand research (`Equities/research/active/sector_hothand_propfirm/`) currently uses sector-level momentum signals. If dividend timing is a meaningful cross-sectional predictor within sectors, it could either serve as a decorrelating signal (potential factor for Strategy D) or explain part of the spuriously high t-stat = 10.38 in the sector_hothand backtest (if dividend-heavy sectors happen to have strong momentum over the test period). The mechanism is equity-only and long-horizon, making it unsuitable for the FTMO propfirm profile (L24: FTMO needs high daily Sharpe, high win-rate, low kurtosis, ≥40-day materialisation horizon doesn't fit). However, it could be a personal-book equity signal — if Strategy D eventually targets the personal book rather than propfirm, this belongs in the candidate pool. Need N ≥ 30 instruments and monthly rebalance to make HAC and AMTP tractable.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Interesting mechanism but misaligned with current propfirm target (FTMO). Flag for reconsideration if a personal-book equity sleeve is ever added to A+B. Access to global dividend timing data (Compustat or similar) would be a prerequisite.
