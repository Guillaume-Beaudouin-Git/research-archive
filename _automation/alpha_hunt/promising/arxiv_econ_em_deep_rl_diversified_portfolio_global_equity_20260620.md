# Deep Reinforcement Learning for Diversified Portfolio Management Across Global Equity Markets

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17307
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 4bcf034909412e1816b3de868129ceb8

## Summary
This paper implements Soft Actor-Critic (SAC) for continuous portfolio weight allocation across global equity markets, incorporating transaction costs, turnover penalties, and diversification constraints into the reward function. Five model configurations are compared, varying the reward formulation (Sharpe vs. CVaR vs. combined) and policy structure (flat vs. hierarchical Dirichlet). The hierarchical Dirichlet policy structure — which first allocates to regions then to stocks within regions — outperforms flat weight allocation under the same training setup. The paper uses walk-forward out-of-sample validation but does not specify fold count or evaluation period.

## Why it might be useful
The hierarchical Dirichlet allocation structure is potentially relevant to the A+B portfolio level when Strategy D is added. The Dirichlet hierarchy (global → regional → asset) mirrors the logical structure of the Algo_claude book: propfirm book (FTMO, Propr) → asset class (crypto, futures) → individual strategy. However, the SAC approach requires a differentiable portfolio reward, which conflicts with the propfirm constraints (daily DD cap, consistency cap) that are non-differentiable. The sector_hothand_propfirm research is the nearest use case: hierarchical sector → stock allocation could use Dirichlet priors. Main issue: the paper doesn't specify WF fold count or sample size, making DSR assessment impossible.

## Extracted content
SAC (Soft Actor-Critic) for continuous portfolio weights. Five configurations: reward formulations (Sharpe/CVaR/combined) + policy structures (flat/hierarchical Dirichlet). "Hierarchical Dirichlet policy" outperforms flat. Transaction costs, turnover penalties, diversification constraints in reward. Walk-forward OOS validation (fold count not specified in abstract).

## Action proposed
REFERENCE

Read Section 4 for the hierarchical Dirichlet policy specification. Potentially applicable to sector_hothand_propfirm's sector-to-stock allocation design. Do not use for A+B portfolio without resolving propfirm constraint differentiability issue. Must confirm WF fold count ≥ 5 (hard rule) before citing in any research document.
