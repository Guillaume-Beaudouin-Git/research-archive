# SNAPO: Smooth Neural Adjoint Policy Optimization for Optimal Control via Differentiable Simulation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.06570
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: fc61527a5e7e16b1

## Summary
SNAPO uses differentiable simulation and neural adjoint methods to train smooth control policies satisfying exact constraints. On portfolio rebalancing benchmarks (5-50 assets, quarterly frequency), SNAPO achieves 15-23% improvement in certainty-equivalent wealth versus PPO with 10× fewer environment interactions. The method addresses the curse of dimensionality in dynamic programming and sample inefficiency in model-free RL for sequential control problems.

## Why it might be useful
SNAPO's portfolio rebalancing benchmark (5-50 assets, quarterly frequency) is potentially relevant to Strategy A (BTC/ETH/SOL, weekly/daily rebalancing) and the broader portfolio construction for book A+B (ERC risk-units 50/50, SR=2.31). The 15-23% improvement in certainty-equivalent wealth is meaningful if the methodology generalizes to the 3-asset crypto setting. However, the quarterly frequency is much lower than Strategy A's daily/weekly cadence, and the differentiable simulation requires an accurate environment model (crypto dynamics are highly non-stationary). Implementation complexity is high (requires differentiable portfolio simulator + neural adjoint backpropagation), and the benefit over current vol-targeted rebalancing would need to be demonstrated on Strategy A's specific regime structure. Worth revisiting when Strategy B reaches mainnet and the combined book has sufficient live performance data for model fitting.

## Extracted content
- Claims: 15-23% improvement in certainty-equivalent wealth vs PPO, 10× fewer environment interactions (portfolio rebalancing, 5-50 assets, quarterly frequency)
- Method: differentiable simulation + neural adjoint optimization → smooth policies with exact constraint satisfaction

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Revisit when Strategy B is live on mainnet for ≥60 days and combined A+B book has sufficient data for environment model fitting; current 3-asset weekly cadence is too sparse for reliable differentiable simulation training.)
