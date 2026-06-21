# Penalty-Free Quantum Portfolio Optimization: Classical Post-Processing Explains the Wins

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17628
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f65b4d78a36396ed06f66290e84c4de8

## Summary
Shows that the standard penalty-encoded QUBO formulation for cardinality-constrained portfolio optimization fails on D-Wave hardware due to the cardinality penalty creating a fully-connected interaction graph (chain-break fractions 83-92% at N=24-49). The proposed fix: remove the cardinality penalty, optimize only the return-minus-risk objective on the QPU, then enforce cardinality classically as a post-processing step. This reduces chain-break fractions to ≤0.04%. However, the paper notes that for "structurally favorable cases... the classical feasibility projector alone explains the result rather than the QPU." Companion paper to `c8c23b80` (D-Wave audit).

## Why it might be useful
Companion to the D-Wave audit paper (`c8c23b80`): both conclude that quantum advantage in portfolio optimization is currently illusory, with the classical components doing the heavy lifting. This further confirms that our classical ERC/propfirm_canonical.py approach is appropriate for current strategy sizes (N=2-3 strategies, N≤24 commodities). The "penalty-free" insight (drop cardinality from QUBO objective, enforce classically) is a general combinatorial optimization technique applicable to classical solvers too — using a projected gradient or Lagrangian relaxation approach for our Commodities XS universe selection is already implicitly what scipy.optimize.minimize does.

## Extracted content
"Mean chain-break fractions per sample averaged over reads drop from the range of 71 to 92 percent down to at most 0.04 percent" (after removing penalty).

"For structurally favorable cases such as betting with settlement-graph priors the classical feasibility projector alone explains the result rather than the QPU."

## Action proposed
REFERENCE

Quantum computing tool audit. Confirms classical solvers are the right choice. No implementation needed beyond existing approach.
