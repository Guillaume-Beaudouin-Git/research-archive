# Optimal Consumption-Investment Under Epstein-Zin Preferences in Incomplete Markets

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.02945
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 7d19391aa4959f9ab72a6170cb012fe4

## Summary
This paper studies infinite-horizon optimal consumption and investment for an Epstein-Zin utility investor where risk aversion and intertemporal substitution are separated, in an incomplete market with stochastic investment opportunities. The value function is characterized as the unique viscosity solution of an HJB equation, and the optimal policy is derived. The key qualitative difference from CRRA utility is that the hedging demands arising from risk aversion and from intertemporal substitution are no longer confounded—they can push in opposite directions depending on parameter values.

## Why it might be useful
The separation of risk aversion from intertemporal substitution has indirect implications for how vol targeting is calibrated in the A+B book: the current 50/50 ERC allocation in `_audit/portfolio_recalc_2026-06-10.md` implicitly assumes a single risk aversion parameter, whereas Epstein-Zin preferences would generate different hedging demands for the weekly-rebalanced Strategy A versus the 8h-rebalanced Strategy B. This is primarily a theoretical paper with no direct empirical test path given the project's operational constraints. The viscosity solution characterization is also not directly implementable without a stochastic control solver significantly more complex than the current `Portfolio/risk/propfirm_canonical.py` framework.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Pure theory; no direct implementation path for solo systematic trader. File for potential portfolio theory review when formalizing the multi-strategy book allocation.
