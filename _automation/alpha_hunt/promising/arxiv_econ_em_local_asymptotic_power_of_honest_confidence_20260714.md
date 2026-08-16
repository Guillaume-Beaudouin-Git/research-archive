# Local Asymptotic Power of Honest Confidence Intervals

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.10558v1
**Captured**: 2026-07-14 01:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 064f2c098cebb14643e41dc281618af5

## Summary
The paper characterizes how much statistical power is lost when using "honest" (bias-aware) confidence intervals — the now-standard approach in DiD, IV, RD, and factor-model settings that stays conservative against an untestable bias bound rather than assuming the bias is zero. It shows three regimes depending on how the bias bound shrinks relative to the standard error: when the bound shrinks faster, conservatism is essentially free; when the two shrink at the same rate, it costs a specific bounded amount; and in the typical parametric-rate case, where the bound dominates, the honest test has exactly zero local power — it will fail to reject nearby true alternatives with probability approaching one, a loss the paper proves via a minimax argument is intrinsic to honesty itself, not fixable by a better construction. The practical recommendation is to always report the half-width of this power "dead zone" alongside any bias-aware interval.

## Why it might be useful
This is a direct, actionable warning for how this repo already reports interval-based results under the HAC methodology axis: Strategy A's headline number is reported as IC95 [-0.50, 1.63] (contains zero), and the `_automation/feasibility/` Level-A gate is explicitly IC-threshold-based (HAC t>2.5). If any of those intervals are constructed in a bias-aware/conservative way (as opposed to a plain HAC-SE interval), this paper's result says the interval could have literally zero local power against economically meaningful nearby alternatives at the parametric rate — meaning "IC95 contains zero" could reflect an intrinsically underpowered test rather than a true null, which changes how that finding should be communicated. The concrete, low-cost action is to adopt the paper's exact recommendation: compute and report the half-width of the power dead zone alongside any bias-aware/HAC interval the Level-A feasibility gate already produces, so a contains-zero result can be labeled UNDERPOWERED vs. genuinely REJECTED (the same distinction the repo's own re-opening policy already draws for archived families).

## Extracted content
Formula/claim preserved: three power regimes are governed by "the rate of the bias bound relative to the sampling rate" — bound shrinking faster than SE (conservatism free), same order (bounded explicit cost), bound dominating at the parametric rate (zero local power). No specific numeric claim beyond the regime characterization; author's practical recommendation is quoted: "report the half-width of the power 'dead zone' alongside bias-aware intervals."

## Action proposed
TEST_LATER — adding a power-dead-zone half-width diagnostic to the `_automation/feasibility/` Level-A IC gate (and to how Strategy A's IC95 [-0.50,1.63] result is characterized) is a concrete, contained methodology addition, estimated at 1-2 days, worth scheduling but not blocking anything today.
