# The Inflation Compass Model

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=tPHwp1K3Fa&source=feedburner
**Captured**: 2026-07-28 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 712352e808494a1a8b60315799c0e020

## Summary
CSS Analytics presents a regime-switching allocation model built around inflation direction, motivated by the standard critique that a static 60/40 stock-bond portfolio fails when inflation shifts from low to high because both asset classes can fall together, and that real assets (commodities, TIPS, etc.) are needed as ballast in that regime. The excerpt cites the Ray Dalio "all-weather" framing but stops before describing the model's actual inflation-regime classification rule, rebalancing frequency, or backtested performance.

## Why it might be useful
This is a regime-overlay concept, which is exactly the territory covered by L54 (the binding condition for a regime overlay is that the regime predicting variance must predict the mean in the SAME direction — the project's own MONO book overlay failed this test despite satisfying the old MaxDD-based L15 criterion). Any inflation-regime allocation model proposed here would need to pass the L54 test (does high-inflation regime predict both higher stress AND lower forward returns for the "risky" leg, not just higher variance) before being trusted, and would need to be benchmarked against a simple vol-target de-levered baseline the way O3 was in the L54 writeup (de-lever at equal vol beat every regime variant tested). There's also a partial overlap with the Commodities XS Basis+TSMOM active research (`Commodities/research/active/xs_basis_tsmom/`) if the "real assets" leg is implemented via commodity futures, since that would inherit the roll-drag caveat (Lesson 5, ETFs≠futures) if implemented via commodity ETFs instead.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — the regime-classification rule and backtest aren't in the excerpt, and validating it against L54's mean/variance-same-direction test plus a de-levered baseline comparison is a multi-day effort once the full methodology is known.
