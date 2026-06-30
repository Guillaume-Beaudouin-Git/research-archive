# Liquidity-Based Audit of Algorithmic Trading Strategies

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.29018v1
**Captured**: 2026-06-30 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e4d5e800c31970a9f300a1e9a31665b0

## Summary
This paper shows that a strategy's net demand for liquidity is recoverable from its own trade and price history alone, without knowing the underlying signal or optimization problem. The key construct is a multi-period regret decomposition whose sign classifies a linear strategy as a net liquidity consumer (informed-trader type, Kyle 1985) or provider (market-maker type). Under an AR(1) cost process, this statistic equals the product of strategy size and the squared Roll (1984) implied spread — making it a direct proxy for prevailing illiquidity. When aggregating across N correlated strategies, the welfare loss from a liquidity imbalance scales as N², a closed-form fire-sale externality. The authors calibrate to CRSP equity data (2016–2025) and track implied spreads through COVID-19 and the 2022 rate-shock episode, with an estimator computable in O(Tnd) time.

## Why it might be useful
Two concrete applications to Algo_claude:

1. **Strategy B cost validation**: Strategy B (delta-neutral carry on HL testnet) currently uses a fixed cost of ~0.17% RT. The Roll (1984) implied spread computed from HL price/fill history would cross-validate this assumption. If the observed implied spread diverges from 0.17% on a given asset or market condition, it's a signal to adjust the carry floor (`CARRY_FLOOR_8H=0.0034/(30×3)` in `strategies/delta_neutral/`). The estimator is O(Tnd) so computable on the existing `logs/fills.csv` VPS data.

2. **Commodities XS concentration risk**: For any future N-contract XS strategy (N=24 commodities), the N²-scaling fire-sale externality means that correlated exit (e.g., all 24 contracts triggering momentum reversal in the same month) produces welfare loss 576× that of a single strategy. This is a regime-level risk not captured by single-period volatility. Pre-register a maximum N and correlation cap before running the full Commodities XS backtest to bound this externality.

## Extracted content
No code in the excerpt. Mathematical construct referenced:

- Liquidity-demand statistic: sign classifies strategy as net consumer or provider (Kyle dichotomy from observables)
- Under AR(1) costs: statistic = strategy_size × Roll_implied_spread²
- Aggregate welfare loss across N correlated strategies: scales as N²
- Calibrated on CRSP equity data 2016–2025, COVID + 2022 rate-shock episodes
- Estimator complexity: O(Tnd)

Full article needed for formula derivation.

## Action proposed
TEST_LATER

Roll implied spread from HL fill data is a 1-day implementation to cross-validate Strategy B cost assumptions. Defer until Strategy B transitions to mainnet (~2026-07-17), where observed fills are available at sufficient volume to estimate the spread reliably. Tag: `strategies/delta_neutral/`.
