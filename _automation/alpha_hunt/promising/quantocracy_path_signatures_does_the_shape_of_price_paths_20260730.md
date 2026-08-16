# Path Signatures: Does the Shape of Price Paths Predict Returns?

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=esQeekHqCf&source=feedburner
**Captured**: 2026-07-30 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 18cbf63f40fcf42f24c076d07292dffa

## Summary
The piece (from Delphic Alpha) argues that conventional rolling-window indicators — momentum, RSI, Bollinger bands — collapse a price path down to a handful of scalar summary statistics and in doing so throw away the sequencing information: two windows with the same total return can have completely different intra-window shapes (e.g. steady grind vs. sharp reversal then recovery). It proposes path signatures, a mathematical-finance/rough-path-theory tool that encodes the full ordered geometry of a path as a feature vector, as an alternative representation that could recover this discarded information for return prediction. The excerpt is purely conceptual/motivational and does not yet present backtest results or performance numbers.

## Why it might be useful
This is a feature-engineering idea, not a strategy per se, but it is directly relevant to Strategy A (TSMOM v3), whose live excess Sharpe is only 0.566 with IC95 [-0.50, 1.63] (containing zero) — cumret_28d/vol_28d is exactly the kind of scalar summary the article critiques, and path signatures could in principle be tested as an alternative/augmented signal on the same BTC/ETH/SOL series without new data. Any such variant would still have to clear the project's hard rules (walk-forward ≥5 folds, HAC lag-6, AMTP given n_tests>1) before being trusted, and given L20 (DSR mandatory from N_mod≥2), a path-signature variant would count as a strategy modification against Strategy A's 3-mod budget. It's also conceptually adjacent to L38's β-orthogonality test — a shape-based signal would need to be checked it isn't just re-deriving standard momentum in disguise.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — implementation requires building/vetting a path-signature feature pipeline (e.g. via the `esig`/`iisignature` library) and validating it isn't redundant with existing momentum features, which is a multi-day methodological investment before it can touch Strategy A.
