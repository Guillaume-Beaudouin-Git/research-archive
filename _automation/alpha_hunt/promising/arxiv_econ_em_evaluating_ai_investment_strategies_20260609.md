# Regret Decomposition for Black-Box Algorithmic Audit: Covariance-Based Performance Attribution

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.08791v1
**Captured**: 2026-06-09 06:04 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: d9bebd816ef7d1978f1a8b3750a37afc

## Summary
The paper provides an exact decomposition of the cumulative regret of any dynamic policy into a sum of per-period covariances between the cost vector and the policy's decision vector. This extends a single-period identity to the full multi-period stochastic dynamic programming setting. The result holds under i.i.d. costs and mean-unbiased Markov policies, with closed-form bias corrections for non-stationary cases. A Bellman recursion connects the decomposition to standard RL algorithms. The associated trajectory estimator is HAC-consistent, asymptotically normal, and O(T·nd) to compute. The paper frames applications as algorithmic auditing for platform mechanisms and algorithmic portfolio strategies.

## Why it might be useful
The HAC-consistent trajectory estimator is methodologically aligned with the mandatory toolkit (HAC lag-6). More concretely: the covariance decomposition offers a principled way to post-hoc attribute Strategy A (TSMOM v3) performance to periods where the signal correctly "agreed" with realized cost conditions. In practice, this means computing per-period cov(tanh_signal, realized_return) — if TSMOM's alpha is concentrated in a few high-covariance periods (e.g., 2022 crypto crash regime), that would be a red flag suggesting the historical Sharpe 1.33 OOS may be regime-specific rather than robust. The audit could be run against `strategies/tsmom_v2_propfirm/` using the fills.csv log as the trajectory. This is less urgent while Strategy A is frozen (Propr breach), but directly relevant if/when a Strategy A pivot (Voie B FTMO, `Futures/research/active/voie_b_ftmo/`) is evaluated — the covariance attribution would establish whether TSMOM alpha is genuine or concentrated in a survivable subset of market regimes.

## Extracted content
The paper states: "The associated trajectory estimator is consistent, asymptotically normal with HAC variance, and computable in O(T·nd) time." The regret decomposition identity: "cumulative regret of a dynamic policy equals the sum of per-period covariances between the cost vector and the policy's decision." No Python code in the excerpt.

## Action proposed
REFERENCE
