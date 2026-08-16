# Estimating and Testing Kinks in Panel Data Models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.07162v1
**Captured**: 2026-08-10 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 0c5b6ccce47780ea5d2286eaa9675aa8

## Summary
This paper handles the case where a relationship between variables in a panel dataset
doesn't jump discretely at a break date but instead bends — the slope changes smoothly at
one or more unknown "kink" points in calendar time. The authors propose a penalized
least-squares estimator (adaptive weighted group penalty on second differences of the
coefficient path) that can recover both how many kinks exist and where they are, with a
proof that this recovery becomes reliable as sample size grows. They derive convergence
rates for slopes at the edges versus the interior of each regime, extend the method to let
different regressors kink at different dates, and demonstrate it in Monte Carlo simulation
plus a macro-finance application on the debt-growth relationship.

## Why it might be useful
This is a structural-break/regime estimation technique for panel coefficient paths, not a
tradable signal. It has no direct application to Strategy A (crypto TSMOM, frozen on a
beta-dominance problem per L11), Strategy B (delta-neutral carry, blocked on a walk-forward
sample-size problem per the hard WF≥5-folds rule, not a coefficient-kink problem), or
Strategy C (cancelled on vehicle access, not model misspecification). It could in principle
be relevant to the repo's structural-break-testing toolkit (e.g., the cointegration
break-testing work in the "Testing for Smooth Structural Change in Cointegrated Systems"
item captured the same week) if the repo ever needed to locate an unknown regime-change date
in a panel of instrument coefficients — but no current active hypothesis does time-varying
panel-coefficient estimation with unknown kink dates, so the tie is background only.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for
further extraction.

## Action proposed
REFERENCE — pure panel-econometrics methodology paper with no current implementation path
in this repo's active strategies or feasibility-gate code; kept for background in case a
future panel-coefficient regime-break question arises.
