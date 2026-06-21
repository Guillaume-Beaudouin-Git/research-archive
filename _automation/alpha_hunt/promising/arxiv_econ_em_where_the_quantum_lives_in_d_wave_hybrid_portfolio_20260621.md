# D-Wave Hybrid Portfolio Optimization Audit: 99.3% Classical, 0.7% Quantum

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17623
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: c8c23b80fb82f448088ff57026ca2dcb

## Summary
An audit of D-Wave's hybrid quantum-classical portfolio optimization service (LeapHybridCQM) showing that the QPU contributes only 0.034 seconds out of 5-second wall-clock time (≈0.7%), with the remaining 99.3% being classical decomposition and assembly. On cardinality-constrained mean-variance instances (N=10 to 640), the hybrid service matches Gurobi's proven optimal on all 54 tractable instances. Structural finding: the standard cardinality penalty creates a dense rank-one term in the QUBO that makes the interaction graph fully connected regardless of covariance sparsity, eliminating the intended density benchmark axis. The service also returns identical solutions across 10 repeated calls (deterministic), revealing that reported D-Wave "wins" are attributable to the classical pipeline, not quantum sampling.

## Why it might be useful
This is a rigorous audit paper that deflates quantum computing claims for portfolio optimization — directly relevant context if the `sector_hothand_propfirm` research (`Equities/research/active/`) were to consider quantum solvers for its portfolio construction step. More broadly, it confirms that classical solvers (Gurobi, scipy.optimize) are sufficient for our portfolio sizes (N≤3 strategies, N≤24 commodities), and that quantum annealing offers no advantage at current hardware fidelity. Not actionable for current strategies.

## Extracted content
"The mean QPU access time is only 0.034 seconds out of a 5-second wall-clock budget, roughly 0.7 percent of the run."

"The constraint-native LeapHybridCQM service matches Gurobi's proven optimum on all 54 instances where Gurobi proves optimality."

"Chain-break fractions reach 83 percent at N equal to 24 and 92 percent at N equal to 49, producing no feasible samples" (for penalty-encoded QUBO).

## Action proposed
REFERENCE

Confirms quantum annealing is not a practical advantage for portfolio optimization at any scale accessible today. Use classical solvers (scipy, Gurobi) for all portfolio problems. No further investigation needed.
