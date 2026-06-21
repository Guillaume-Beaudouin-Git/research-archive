# Stochastic Game Model for Competing Battery Energy Storage Dispatch with Market Power

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.01178
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 75369505dc0c7e3ca7beb632c111e100

## Summary
This paper models intraday dispatch of grid-scale battery storage operators competing in an electricity market where prices are endogenous (function of aggregate charging/discharging rates). The Nash equilibrium of the resulting linear-quadratic differential game with a shared stochastic driver is characterized semi-explicitly. Market power leads to higher equilibrium prices and lower aggregate dispatch relative to the social optimum. The model provides a rigorous foundation for energy arbitrage strategies that account for strategic interactions between storage operators.

## Why it might be useful
The energy storage arbitrage problem—optimally charging when prices are low, discharging when high, with price endogeneity—is structurally analogous to the delta-neutral carry problem in Strategy B: on Hyperliquid, the funding rate (analogous to the price signal) is endogenous to aggregate positioning, and multiple bots competing to capture the same funding rate signal create a game-theoretic structure similar to the battery operators. The semi-explicit Nash equilibrium characterization suggests that as Strategy B scales from testnet to mainnet notional, the funding rate advantage will compress due to strategic competition, and the equilibrium notional at which the carry edge nets to zero could be computed using the paper's framework. This is speculative at NOTIONAL_USD=50, but relevant as a scaling limit analysis.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Energy economics paper; structural analogy to Strategy B carry is speculative and not directly implementable. File for potential mainnet scaling analysis once NOTIONAL_USD grows beyond pilot level.
