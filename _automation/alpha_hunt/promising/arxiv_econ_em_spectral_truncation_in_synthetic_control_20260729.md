# Spectral Truncation in Synthetic Control

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.25074v1
**Captured**: 2026-07-29 03:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 3d34b1d68220a4085e5a83f9d42da874

## Summary
Synthetic control (SC) normally matches a treated unit to a weighted blend of donor units
using their raw pre-treatment time paths. This paper tests a variant, "Spectral SC," that
instead matches in a reduced coordinate system built from the leading singular vectors of
the donor panel, plus a hybrid estimator that blends raw-path and spectral matching. The
authors prove the hybrid collapses to plain SC at full rank, show that exact matching on K
spectral dimensions with more than K+1 donors is mathematically underdetermined (leaving a
whole affine family of solutions), and derive how that leftover imbalance translates into
treatment-effect bias. Testing across 11 simulated data-generating regimes (400 replications
each), they find truncated Spectral SC has meaningfully higher error than tuned raw-path SC
in every regime (differences of 4-11 Monte Carlo standard errors), the hybrid mostly just
reverts to raw-path SC, and the spectral approach's disadvantage shrinks dramatically once
unit/time fixed effects are removed before the spectral decomposition — the paper's overall
message is a caution against spectral truncation rather than an endorsement of it.

## Why it might be useful
This is a synthetic-control estimator comparison, and this repo currently runs no
synthetic-control-style event studies (no active strategy uses SC), so there is no live
methodology consumer — the honest call is background reference. If the repo ever adopted a
synthetic-control approach for an event-study-style hypothesis (e.g., isolating an
idiosyncratic shock's effect on one instrument against a donor pool of correlated
instruments), this paper's finding is directly actionable: it says NOT to truncate to
leading spectral components and to prefer tuned raw-path matching, which would save a
data-mining detour. It has no bearing on Strategy A/B/C's current blocking issues.

## Extracted content
No code or formulas in the excerpt. Numeric claims preserved: 11 data-generating regimes,
400 replications per regime; truncated Spectral SC RMSE exceeds tuned raw-path SC by 4 to 11
Monte Carlo standard errors in every regime tested.

## Action proposed
REFERENCE — no synthetic-control pipeline currently exists in this repo to apply the
finding to; kept in case an event-study/SC hypothesis is ever built.
