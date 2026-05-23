# An Index of Commodity Futures Returns Since 1871 [Quantpedia]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=AjTXA83nc3&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 32bfe57ddbe11db6a8a5b4dde3f12644

## Summary
Quantpedia constructs a commodity futures return index extending back to 1871, covering geopolitical tension, inflation, and supply-shock regimes across 150 years. The index separates spot return, roll yield, and collateral return components — which is the appropriate decomposition for testing any momentum signal on commodity futures. The long history allows testing across macro regimes rarely covered by post-2000 crypto data.

## Why it might be useful
CLAUDE.md archives "TSMOM on commodity ETFs: ETF roll drag contaminates momentum signal." But this article uses *futures*, not ETFs — eliminating the roll drag contamination problem. The decomposition (spot + roll + collateral) is exactly what Strategy A's signal would need if extended to commodity futures. However, accessing 1871-2025 commodity futures data would require the full Quantpedia dataset (likely paywalled). The methodology is also applicable to Strategy A's crypto TSMOM: verifying that the 28-day return includes or excludes funding carry (analogous to roll yield) is a clean decomposition question already present in our data/funding_carry/.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Check whether full Quantpedia dataset is accessible. If so, test TSMOM on the commodity futures index as potential Strategy D (decorrelated from NQ and crypto). Resolves the ETF-vs-futures distinction that killed previous commodity tests. Data likely paywalled — confirm before investing time.
