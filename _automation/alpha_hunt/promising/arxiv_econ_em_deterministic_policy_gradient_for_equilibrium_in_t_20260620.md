# Deterministic Policy Gradient for Equilibrium in Time-Inconsistent Control via RL

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.11798
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 34e2e083c68c9c0e92839b282b37f526

## Summary
A continuous-time model-free RL algorithm learns equilibrium policies in time-inconsistent control problems — those where the optimal plan shifts as time passes due to changing preferences. The Hamilton-Jacobi-Bellman system is reformulated into two stages: an auxiliary time-consistent stage solved with deterministic policy gradient, and a fixed-point iteration to recover the equilibrium. The method is model-free and learns from simulated or observed transitions.

## Why it might be useful
Propfirm challenges create time-inconsistent sizing: the optimal drawdown-budget allocation shifts as the account balance evolves through the evaluation period. Strategy A's Propr execution uses fixed vol-targeting that doesn't adapt to remaining DD budget. This RL framework could motivate an adaptive sizing policy for trailing_dd_simulator.py in Portfolio/risk/, but bridging continuous-time RL to discrete daily rebalance requires significant infrastructure. Theoretical background only at this stage.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
