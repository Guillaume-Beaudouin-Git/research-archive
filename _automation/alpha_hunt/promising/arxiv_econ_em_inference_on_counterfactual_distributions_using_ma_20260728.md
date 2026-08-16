# Inference on counterfactual distributions using martingale posteriors

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.24143v1
**Captured**: 2026-07-28 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c4ce3c6a9ecd6db283185e221574dff6

## Summary
Proposes a Bayesian "martingale posterior" method for estimating full counterfactual outcome distributions (not just average treatment effects), built on a nonparametric Dirichlet process mixture model, that coherently quantifies epistemic uncertainty on densities, CDFs, and quantiles, extends to instrumental-variables settings, and is fast to compute. Illustrated on medical/economic causal examples (zinc lozenges and cold duration, vitamin A and child survival, job-training effects).

## Why it might be useful
No direct tie to a live strategy, filed honestly as background methodology only. The transferable point: this is a Bayesian alternative to the bootstrap-CI machinery the project uses throughout (block bootstrap, Politis-Romano) for characterizing a full outcome distribution rather than a point estimate plus standard error — relevant if the project ever wants distributional (not just mean/Sharpe) walk-forward validation, e.g. reporting full OOS return-distribution uncertainty for Strategy A rather than a single Sharpe plus IC95, though it would require adopting a Bayesian nonparametric framework the project does not currently use.

## Extracted content
No code. No finance-specific numeric claims (illustrated on medical/labor examples, not finance).

## Action proposed
REFERENCE.
