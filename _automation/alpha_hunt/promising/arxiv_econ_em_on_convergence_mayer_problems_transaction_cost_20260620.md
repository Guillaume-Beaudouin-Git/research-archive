# On Convergence of Mayer Problems in Financial Markets With Transaction Costs

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.11717
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f44c5433d29a8187e53bda0f16ccb08a

## Summary
This paper addresses a foundational mathematical question: given a sequence of portfolio optimization problems with transaction costs that converge in some sense (as costs go to zero or as the model is simplified), do the optimal strategies and values also converge? The geometric (convex cone) framework for multi-currency markets with proportional transaction costs is used, and conditions for value function convergence under model perturbations are derived. The results provide theoretical guarantees for limit-taking in transaction-cost portfolio problems.

## Why it might be useful
This is a theoretical mathematics paper with limited direct applicability to Algo_claude's practical research pipeline. The convergence result is relevant if a strategy is designed in a cost-free idealization and then adjusted for transaction costs — the paper guarantees that the optimal strategy converges to the idealized one as costs go to zero. For Algo_claude, this is already handled empirically (we test at actual costs from day one). The one indirect use case: when comparing Strategy A backtest performance at different cost assumptions (e.g., 0.17% vs. 0.10% RT), the convergence theory guarantees that the ranking of strategies is preserved under small cost perturbations — useful if we need to compare backtests across different cost scenarios.

## Extracted content
Geometric (convex cone) framework for multi-currency markets. Proportional transaction costs. "Fundamental questions — no-arbitrage criteria, hedging, optimal portfolio selection — in a natural framework defined by two random processes, S (price) and K (cone-valued solvency set)." Mathematical convergence of value functions and optimal strategies.

## Action proposed
REFERENCE

Theoretical background for transaction-cost portfolio theory. Not actionable for current strategy development. File as methodology reference if multi-currency or multi-asset transaction cost modeling becomes relevant (e.g., FX carry revival or Commodities XS with realistic roll costs).
