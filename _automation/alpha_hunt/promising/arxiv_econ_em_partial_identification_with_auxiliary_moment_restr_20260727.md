# Partial Identification with Auxiliary Moment Restrictions

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.21807v1
**Captured**: 2026-07-27 04:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: d37ffe6f235abbb7e09f4ba37174ccbd

## Summary
Shows that when survey/administrative data reports an outcome only as a bracketed/top-coded interval (for privacy or reporting reasons), the same data custodian typically still publishes an accurate aggregate statistic of that outcome — and this aggregate, used as an auxiliary moment restriction, can sharply narrow the partial-identification region for the outcome's best linear predictor without adding any new assumption. Characterizes the geometric effect of different restriction types and validates on interval-valued CPS wage data, recovering "a substantial share" of the identifying power normally thought lost to coarsening.

## Why it might be useful
Weak direct tie to Algo_claude — no live strategy currently works with interval-censored/bracketed data. The transferable idea is narrow but real: any future work using a coarsely-reported macro series (a survey-based sentiment index, or a regulatory dataset with top-coded/bracketed fields) should check for a published aggregate moment before discarding the coarse variable as unusable, per this paper's method — filed as background for the `_automation/arxiv/` and `_automation/synthesis/` scraping pipeline's own future data-sourcing decisions rather than for any current strategy.

## Extracted content
No code/formulas. No finance-specific numeric claims (illustrated on CPS wage data).

## Action proposed
REFERENCE.
