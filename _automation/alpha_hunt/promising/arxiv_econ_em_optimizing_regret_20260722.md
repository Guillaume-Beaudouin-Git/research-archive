# Optimizing Regret

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.18866v1
**Captured**: 2026-07-22 01:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 9866430efead9d52c96b9ea43e62d606

## Summary
Develops a full derivative theory for a "covariance regret" functional, built on the identity that expected regret equals the covariance between realized costs and the decisions taken. Derives the Gateaux derivative and shows the universal steepest-descent direction is a contrarian policy (bet against the demeaned cost), while ascent yields a momentum policy; for linear policies the gradient is the cost covariance matrix, and a zero Hessian implies the optimum sits at a boundary, recovering the minimum-variance portfolio as a special case. Extends to constrained optimization, a sign-gradient duality between regret-minimization and alpha-maximization, and finite-sample convergence bounds paralleling Thompson Sampling, with noted applications to portfolio tilting and LLM-based allocation strategies.

## Why it might be useful
Formalizes momentum and mean-reversion as the two possible steepest-ascent/descent directions of the same covariance-regret functional — a clean theoretical frame for why TSMOM-style strategies (Strategy A) and contrarian/carry strategies (Strategy B) sit at opposite ends of one continuum rather than being unrelated bets, useful background for the book-level admission framework (`Portfolio/admission/`) when arguing why a momentum sleeve and a contrarian sleeve diversify each other. Second link: the boundary-optimal (zero-Hessian) result formally argues that corner solutions like long-only or minimum-variance sizing are not obviously suboptimal versus interior-optimized weights — a theoretical justification for the project's preference for fixed daily vol-targeting over continuously re-optimized weights.

## Extracted content
Formula (paraphrased from description): for a linear policy pi(c) = A*c + b, the regret gradient is the cost covariance matrix Sigma_c, and a zero Hessian implies boundary-optimal solutions such as the minimum-variance portfolio. No numeric/Sharpe claims — pure theory paper.

## Action proposed
REFERENCE.
