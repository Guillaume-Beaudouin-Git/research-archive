# From State Prices to Modern Pricing Kernels: Survey of Asset Pricing Probability Measures

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.27658
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 297a2bfaefc79358489c9c8ce8cf5de3

## Summary
A comprehensive historical survey of probability measure transformations in asset pricing, from Bachelier's speculative model through Arrow-Debreu contingent claims, Black-Scholes-Merton, Harrison-Kreps/Pliska martingale theory, Delbaen-Schachermayer's FTAP, Breeden-Litzenberger implied state prices, change-of-numeraire, Hansen-Jagannathan SDF bounds, and modern machine-learning pricing kernels. The unifying theme is that pricing requires constructing a measure under which prices are expectations after discounting or numeraire normalization, not just estimating physical probabilities. Covers empirical SDF work and sentiment/text-based probability transformations as recent extensions.

## Why it might be useful
Background reading for understanding the economic foundations of our excess return methodology (L8: "Excess returns + HAC lag-6 + daily vol targeting mandatory"). The SDF / pricing kernel framing connects to our HAC excess return methodology — we're implicitly working with physical probability and need to ensure our backtests capture the risk premium (not just the drift). Relevant as methodological foundation for the pricing kernel approach if Commodities XS or a new equities strategy needs to separate expected return components. No direct tradeable edge in this survey.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Pure survey paper.

## Action proposed
REFERENCE

Foundational theory survey. No implementation needed. Useful background for understanding why excess returns (L8) over the risk-free rate must be used: the survey frames this as the SDF-adjusted expectation vs raw return distinction.
