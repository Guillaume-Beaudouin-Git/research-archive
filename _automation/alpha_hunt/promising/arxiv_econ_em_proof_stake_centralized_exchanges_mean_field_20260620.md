# Proof of Stake Economy Under Centralized Exchanges: A Mean Field Model

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.09003
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 30cac217df6c6347fc1d690fca6bdf11

## Summary
This paper models the strategic interaction between centralized exchange trading and decentralized Proof-of-Stake (PoS) staking behavior using a continuous-time mean field game. A validator simultaneously acts as a market participant on a centralized exchange (CEX) and a PoS validator, allocating capital between staking (for block rewards) and trading (for market returns). The model analyzes how token price dynamics, CEX trading activity, and staking yields interact in equilibrium. The key result: concentrated staking by large validators creates a feedback loop where CEX price impact and staking rewards are correlated, amplifying both returns and risks.

## Why it might be useful
Strategy B (delta-neutral carry on HL testnet) holds perpetual positions on assets where the underlying is a PoS token (HMSTR, TST, MEGA). The mean field model here describes exactly the feedback loop that could affect Strategy B's carry rate: if large PoS validators stake more during high CEX price periods (buying pressure on CEX), the funding rate on HL perpetuals for those tokens increases (because long demand rises). This could create autocorrelation in the CARRY_FLOOR signal that the current strategy doesn't model. The EIP-1559 paper (e48dbbfd) studies a related ETH mechanism; together these two papers bracket the token economics relevant to B's asset selection.

## Extracted content
Continuous-time mean field game. Validator = simultaneous CEX market participant + PoS staker. "Concentrated staking by large validators creates a feedback loop where CEX price impact and staking rewards are correlated." Token allocation dynamics between staking (block rewards) and trading.

## Action proposed
REFERENCE

Background theory for understanding funding rate dynamics in Strategy B's VIABLE_ASSETS (mostly PoS tokens). Not directly implementable as a trading signal, but informs why funding rates on PoS tokens exhibit different autocorrelation than non-PoS tokens. Cross-reference with Strategy B's state.json for asset selection rationale.
