# Single-Period Portfolio Selection as Information Projection under CRRA Utility

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.03184
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 788344cc61db9336f5d22b8a95cf794f

## Summary
Under CRRA utility with finite-support market payoffs, the certainty-equivalent growth rate decomposes into three information-theoretic terms: a portfolio-induced Rényi divergence, a Rényi entropy of the risk-tilted market law, and a log-partition term. The Rényi order equals one minus the coefficient of relative risk aversion, giving a clear operational interpretation. The optimal portfolio is identified as an information projection of the physical probability law onto a simplex, bridging portfolio theory and information geometry. The framework provides a unified theoretical lens on risk aversion and portfolio choice without requiring Gaussian or continuous distributions.

## Why it might be useful
The Rényi divergence decomposition of portfolio utility provides a theoretically clean way to think about the risk-aversion parameter implicit in Strategy A's vol targeting (VOL_TARGET_LIVE=0.18) and the ERC risk-unit allocation in the A+B book described in `_audit/portfolio_recalc_2026-06-10.md`. Specifically, the information projection framing gives a way to check whether the 50/50 ERC allocation is utility-consistent given the different return distributions of A (weekly, lumpy) and B (8h carry, near-continuous). The Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) with 24 contracts needs a principled portfolio construction step—the information projection framework with non-Gaussian, finite-support payoffs may handle the heavy-tailed commodity distributions better than Gaussian mean-variance optimization.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Theoretical portfolio construction paper; no direct test path without substantially more infrastructure. Relevant when formalizing the A+B book allocation methodology.
