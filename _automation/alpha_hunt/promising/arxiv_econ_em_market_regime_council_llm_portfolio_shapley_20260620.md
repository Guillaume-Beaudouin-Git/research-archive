# Market Regime Council: Shapley Credit Assignment in Multi-Agent LLM Portfolio Systems

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.24490
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 8e141a42323c6ac463324c52a3932911

## Summary
The Market Regime Council (MRC) is a cooperative multi-agent decision system for portfolio management that addresses three problems: credit assignment across specialist agents, cold-start dominance under regime shifts, and transparency. The system computes exact Shapley values across all single, pairwise, and grand-coalition agent outputs for online weighting. Three specialist agents (momentum, mean-reversion, macro) are combined with Shapley-weighted aggregation, and the regime council dynamically shifts credit assignment based on which agent coalition performed best in recent periods. Tested on multi-asset portfolios with regime shifts.

## Why it might be useful
The Shapley credit assignment approach is an interesting portfolio aggregation framework, but the use case for Algo_claude is limited. The A+B book is already a two-strategy portfolio (A: TSMOM, B: delta-neutral) with ERC weighting — adding a Shapley-weighted meta-layer would complicate risk management without clear benefit at this scale. More interesting is the "cold-start dominance" problem: when a new strategy (e.g., B mainnet) is added to the book with insufficient live history, it tends to be underweighted. Shapley credit could dynamically bridge the cold-start period. However, with only 2 active strategies and a 3rd (D) in research, the infrastructure is premature. File for future reference when N≥4 strategies are active.

## Extracted content
MRC = "cooperative multi-agent decision system that computes exact Shapley credits across all single, pairwise, and Grand-coalition outputs." Three specialist agents: momentum, mean-reversion, macro. Online weighting updates credit assignment based on recent regime performance.

## Action proposed
REFERENCE

Premature for current 2-strategy book. Revisit when the book expands to N≥4 active strategies. The cold-start credit assignment is the most immediately applicable concept — apply to B mainnet onboarding in the A+B recalc (~2026-07-17). Cross-reference with `_audit/portfolio_recalc_2026-06-10.md`.
