# Compositional Synthetic Controls

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.16991v1
**Captured**: 2026-07-21 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 04c6c47a6ce1b77289ea104746276b37

## Summary
The paper builds a synthetic-control estimator for outcomes that are compositions (vectors of shares summing to one) rather than scalars, derived from a random-utility model with interactive fixed effects. It maps compositions into log-odds space where the standard synthetic-control convex-hull identification applies, which is equivalent to finding the Fréchet barycenter of donor units under the Aitchison metric — the natural geometry for share data — using one shared weight vector across all categories simultaneously. It also introduces a placebo inference procedure based on Aitchison distance rather than raw Euclidean distance. Applied to Pennsylvania's electricity generation mix after a renewable-portfolio-standard policy change, it finds natural gas share ends up nearly 60 percentage points above its synthetic counterfactual by 2022, with renewables losing relative ground versus the counterfactual.

## Why it might be useful
The concrete technique that carries over is the Aitchison-metric placebo inference procedure, which sits on the same methodology axis as this repo's existing placebo-testing lessons (L49's vol-matched calendar placebo, L58's requirement that a placebo pool's mean match the unconditional expectation of the trade form) — a compositional/simplex-aware placebo distance is a more principled tool than a naive share-difference test whenever a future study needs to placebo-test a change in relative weights rather than a level. The one plausible internal application is Strategy A's BTC/ETH/SOL allocation, which is itself a compositional vector (three shares summing to one); if a future hypothesis claims the vol-targeted weight rotation across those three assets is "different" from some counterfactual allocation, this is the correct estimator family rather than testing each asset's weight in isolation. That said, this is speculative — no current active hypothesis in the repo is framed as a compositional-outcome problem, so there's no concrete test to schedule yet.

## Extracted content
No code in the excerpt. One methodological claim preserved: the estimator "recovers the Fréchet barycenter under the Aitchison metric... using a single set of weights across all categories." Numeric claim: natural gas share exceeds its counterfactual by "nearly 60 percentage points by 2022" in the Pennsylvania application (author's empirical result, not a financial-markets number).

## Action proposed
REFERENCE — a genuinely new placebo/counterfactual technique on the same axis as L49/L58, but no active hypothesis in the repo is currently framed as a compositional-share problem, so there is no concrete test path today.
