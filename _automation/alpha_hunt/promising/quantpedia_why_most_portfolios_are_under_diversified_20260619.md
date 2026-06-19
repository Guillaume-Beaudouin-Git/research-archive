# Why Most Portfolios Are Under Diversified

**Source**: quantpedia
**URL**: https://quantpedia.com/why-most-portfolios-are-under-diversified/
**Captured**: 2026-06-19 11:30 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 9475775861596ef10a6c2ca6d92b5ff6

## Summary

Capital-based equal-weight allocation in multi-asset portfolios systematically concentrates risk in a small number of high-volatility assets, compounded by cross-asset correlations — most of the realized variance ends up in equities and Bitcoin even when their notional weights are modest. The article benchmarks three allocation regimes on a ten-ETF universe spanning equities, bonds, commodities, credit, private equity, and Bitcoin: equal-weight (capital), risk parity (equalize marginal risk contributions), and clustering-based allocation (group correlated assets first, then apply risk parity across clusters). Risk parity reduces concentration but at the cost of lower absolute returns. The clustering layer further decouples exposures by routing capital through genuinely independent risk factor groups rather than through individual instruments, improving risk-adjusted performance. The central claim: effective diversification is governed by the geometry of the underlying risk factors, not the count of instruments or the uniformity of capital weights.

## Why it might be useful

Directly relevant to the A+B book construction decision made 2026-06-10 (SR 2.31, ERC 50/50 by risk-units between Strategy A and B). The book currently uses a two-asset ERC — which is exactly what this article critiques as insufficient when intra-cluster correlations are high. The more actionable link is **Strategy D selection**: the gate requires SR(book+D) > 2.54, and a clustering approach on an expanded A+B+D universe could be used to size D's allocation more precisely than the current ERC formula (which degenerates when B's backtest has 92% zeros, per `_audit/portfolio_recalc_2026-06-10.md`). Concretely: once a D candidate clears RESEARCH_PASS, run a cluster analysis on the (A, B, D) return series to verify that D adds a genuinely independent factor before computing the contribution to the book SR — rather than assuming ρ_AD ≈ ρ_BD ≈ 0. Also cross-references the Commodities XS active research (`Commodities/research/active/xs_basis_tsmom/`): if that strategy reaches testing, its 24-contract universe would benefit from clustering-based portfolio construction to avoid TSMOM + BASIS loading on the same energy/metals factor cluster.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

The clustering-based allocation framework is useful background for Strategy D portfolio construction but requires ≥3 live return series to be non-trivial — currently only A (paused) and B (testnet). Revisit when a D candidate clears RESEARCH_PASS and the A+B+D allocation question becomes concrete. No immediate test path with the current two-strategy book.
