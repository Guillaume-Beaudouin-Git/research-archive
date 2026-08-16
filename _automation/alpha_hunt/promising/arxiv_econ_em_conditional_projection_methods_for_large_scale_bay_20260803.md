# Conditional Projection Methods for Large-Scale Bayesian VARs

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.29215v1
**Captured**: 2026-08-03 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 38bd7ddd1a5f6855de4c9d1e81a866d9

## Summary
The authors present a faster computational method for conditional forecasting and
scenario analysis in large Bayesian vector autoregressions (VARs). By imposing a factor
structure on the reduced-form errors, they enable equation-by-equation estimation that
scales cubically only in the number of imposed restrictions rather than in the full system
size, letting the model handle dozens of variables cheaply. They demonstrate it on a
33-variable macro-financial VAR with ten identified structural shocks, generating
counterfactual oil-price scenarios for a hypothetical 2026 Strait of Hormuz closure and
showing the same oil-price path is consistent with outcomes ranging from mild to
stagflationary depending on which shocks are assumed to deliver it.

## Why it might be useful
This is a computational-econometrics paper about scaling Bayesian VAR scenario analysis, not
a signal or trading edge. None of the three active strategies (A: crypto TSMOM long-only
beta problem; B: delta-neutral carry rotation/WF-folds problem; C: cancelled futures vehicle
problem) involve macro-VAR scenario forecasting, and the repo's toolkit doesn't currently
build large multi-asset VARs for regime/scenario conditioning — the closest thing is the
per-strategy walk-forward and HAC significance machinery, which this paper doesn't touch.
The oil-scenario application is macro-narrative color, not a testable signal on any
instrument the repo trades. No concrete tie exists today.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt beyond the stated model
dimensions (33 macro-financial variables, ten structural shocks). Full article needed for
further extraction.

## Action proposed
REFERENCE — Bayesian VAR computation/scenario methodology with no active strategy or
toolkit tie; kept for background only.
