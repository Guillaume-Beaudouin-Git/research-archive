# Inference for Group Interaction Experiments

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.02385v1
**Captured**: 2026-07-03 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 85e6db0afe9eb3e9197b793b6638d7ba

## Summary
The paper develops design-based inference for experiments where individuals are randomized into interacting groups under different group-level treatments, covering both fixed and randomly-formed groups and both no-interference and interference regimes. It characterizes, for each scenario, the correct causal estimand and shows that cluster-robust standard errors remain valid under interference (delivering correct inference on marginalized exposure effects), while individual-level heteroskedasticity-robust inference suffices once interference is absent and groups are randomly formed. The technical contribution is a coupling argument used to derive the asymptotic distribution of the standard estimators in this setting.

## Why it might be useful
This is pure experimental-design econometrics (randomized group treatments) with no direct trading application — it does not fit any active strategy (A/B/C) or any theme currently tracked in `_automation/synthesis/_state.json`. The one legitimate link is methodological: the paper's core problem — getting valid standard errors when observations are correlated through a shared group/cluster structure rather than i.i.d. — is the same structural issue CLAUDE.md already flags twice: HAC lag-6 correction for autocorrelated returns, and the requirement to use block bootstrap (never i.i.d.) whenever trade clusters exist. It's a reminder that "cluster-robust ≠ automatically correct" — the estimand and inference method must be matched to the actual dependence structure, which is the same discipline underlying the walk-forward/AMTP rigor this repo already enforces. No second, more concrete tie exists in this excerpt.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Background reading on design-based/cluster-robust inference discipline; no path to any active or archived strategy test.
