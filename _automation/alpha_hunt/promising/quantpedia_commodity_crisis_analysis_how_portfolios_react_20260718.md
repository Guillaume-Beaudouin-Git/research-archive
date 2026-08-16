# Commodity Crisis Analysis – How Portfolios React to Commodity Shocks

**Source**: quantpedia
**URL**: https://quantpedia.com/commodity-crisis-analysis-how-portfolios-react-to-commodity-shocks/
**Captured**: 2026-07-18 21:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: e8dee00cda23ad97ac7a44664f9c1f17

## Summary
The piece argues portfolio risk analysis is usually framed around equity bull/bear regimes, but a distinct and under-studied regime is the commodity-driven shock — market stress that originates in energy or commodity markets rather than equities. It cites the recent US-Iran tensions, the 2022 Russian invasion of Ukraine, and the 2002 Iraq invasion buildup as episodes where commodity (mainly oil) price and volatility shocks propagated into broader financial assets independently of the equity cycle. The implicit methodological point is that portfolio stress-testing should condition on commodity-shock regimes as a separate axis from equity drawdown regimes, since the two do not necessarily coincide.

## Why it might be useful
This maps directly onto the repo's open `Commodities/research/active/xs_basis_tsmom/` chantier (phase A incomplete, n<=279) — a commodity-shock regime indicator (e.g. oil vol spike or geopolitical event flag) is a natural candidate conditioning variable to test there rather than relying only on equity-drawdown regimes. It is also a direct test case for lesson L54's binding condition for any regime overlay: the regime must predict the MEAN in the same direction as the VARIANCE, not just flag high volatility — before building a commodity-shock overlay on the XS basis/TSMOM research, the concrete next step is to check whether commodity-shock windows are also the windows where the existing TSMOM/basis signal's mean return improves (L54 test), not just where its variance spikes, exactly the failure mode that killed the book-level regime overlay experiment.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt (only qualitative historical episode references: 2026 Iran attacks, 2022 Russia invasion, 2002 Iraq invasion). Full article needed for further extraction of any quantitative regime-conditioning results.

## Action proposed
TEST_LATER — a commodity-shock regime flag is a plausible conditioning variable for the active `xs_basis_tsmom` research, but phase A there is still incomplete and the article's actual regime-definition methodology needs to be read in full before it can be operationalized, so this is a 1-3 day follow-up once phase A lands, not an immediate test.
