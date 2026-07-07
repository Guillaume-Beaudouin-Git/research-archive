# Geometric Control of Decisions' Affordability

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.04885v1
**Captured**: 2026-07-07 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 3fd7de072604b217399944da9c4f46c9

## Summary

The paper frames data-driven policy decisions (a policymaker deciding whether to extend an intervention from a "donor" population to a new "target" population) as a certification problem: an estimator is certified if it bounds the probability of a costly mistake whenever the true effect is large enough. It shows this bound translates into a worst-case compensation cost, and that for matching estimators with positive weights, minimizing that worst-case cost in large samples reduces to a purely geometric problem solved by a Delaunay triangulation over the donor data. The authors then use this to design donor-data collection strategies that keep worst-case cost below a target, illustrated on a semi-synthetic development-economics example.

## Why it might be useful

This is a development-economics / causal-inference paper with only a loose methodological echo in Algo_claude's world: the "certification" idea (bound the probability of acting on a false signal, before acting) is conceptually parallel to the 3-level feasibility gate in `_automation/feasibility/` (Level A: IC screen; Level B: WF+bootstrap+DSR; Level C: sanity checks) and to AMTP/DSR correction for pre-registered hypotheses — both are ways of pre-committing to an error-tolerance before trusting an estimate. It does not, however, map onto any live signal-generation problem — there is no "donor vs target population" structure in any active strategy (A/B/C/D), and the Delaunay-geometry result is specific to matching estimators, which nothing in this codebase uses.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt beyond the qualitative geometric result (Delaunay interpolant is optimal for worst-case affordability). Full paper needed for the certification bound's exact form.

## Action proposed

REFERENCE

Weak, background-only link to the feasibility-gate philosophy already in place (pre-committing to error tolerance). No concrete test path — the estimator class (matching on donor/target populations) doesn't correspond to anything in the current research pipeline.
