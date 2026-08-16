# Optimizing Regret

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.18866v2
**Captured**: 2026-07-31 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b7621d39a4ebc167a613f25c957feaf1

## Summary
Develops a derivative theory for a "covariance regret" functional, built on the identity that expected regret equals the covariance between realized costs and the decisions taken. Derives the Gateaux derivative and shows the universal steepest-descent direction is a contrarian policy (bet against the demeaned cost), while ascent yields a momentum policy; for linear policies the gradient is the cost covariance matrix, and a zero Hessian implies the optimum sits at a boundary, recovering the minimum-variance portfolio as a special case. Extends to constrained optimization, a sign-gradient duality between regret-minimization and alpha-maximization, and finite-sample convergence bounds paralleling Thompson Sampling.

## Why it might be useful
Same substance as the earlier arXiv version of this paper (9866430efead9d52c96b9ea43e62d606, captured 2026-07-22, filed separately in this batch) — formalizes momentum and mean-reversion as opposite steepest-ascent/descent directions of one covariance-regret functional, relevant background for the book-level admission framework (`Portfolio/admission/`) on why a momentum sleeve (A) and a contrarian/carry sleeve (B) can diversify each other. Second link: the boundary-optimal (zero-Hessian) result argues corner solutions like fixed daily vol-targeting are not obviously suboptimal versus interior-optimized weights.

## Extracted content
Formula (paraphrased): for linear policy pi(c) = A*c + b, the regret gradient is the cost covariance matrix Sigma_c, zero Hessian implies boundary-optimal solutions such as the minimum-variance portfolio. No numeric/Sharpe claims.

## Action proposed
REFERENCE — revised version of the same paper as arxiv_econ_em_optimizing_regret_20260722.md (captured 2026-07-22); read that file first, this one drops the explicit note on portfolio-tilting/LLM-allocation applications but is otherwise identical in substance.
