# Asymptotic Unexpected Losses in Large Portfolios Under Diversification

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.18049
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 98509d45ea31b7a27e55e4e1e414e1ff

## Summary
A mathematical finance paper studying how the excess of a nonlinear risk measure over the mean (the "unexpected loss") behaves as portfolio size grows. For monotone cash-additive risk measures on Banach-lattice-valued Orlicz spaces, convergence along weighted averages is equivalent to scalar continuity at the origin. For positively homogeneous risk measures, unexpected losses scale as o(n × λ̄_n) where λ̄_n is the average weight. Analogous results are derived for Choquet insurance premia, plus asymptotic bounds on the potential underestimation when treating diversified portfolios as co-monotonic (worst-case assumption).

## Why it might be useful
This is a pure measure-theory paper about asymptotic behavior of risk measures in large credit/insurance portfolios. Our portfolio has N=2 strategies (A+B), which is far from the "large portfolio" asymptotic regime. The co-monotonic risk ratio result has weak relevance to our ERC calculation (Portfolio/risk/propfirm_canonical.py), but since the full-sample ρ_AB=0.039 suggests near-independence, not co-monotonicity, the bound is not binding. No direct application to trading strategies.

## Extracted content
No code, formulas stated at high abstraction level, no specific numeric claims in excerpt.

## Action proposed
REFERENCE

Pure theory for large credit/insurance portfolios. Not applicable at our N=2 strategy portfolio scale.
