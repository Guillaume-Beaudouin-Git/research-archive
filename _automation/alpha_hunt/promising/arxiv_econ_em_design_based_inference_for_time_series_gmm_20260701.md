# Design-Based Inference for Time-Series GMM

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.31685v1
**Captured**: 2026-07-01 03:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 7158b583533f510618c073a831e41517

## Summary

The paper reframes time-series GMM inference as design-based: instead of treating the sample as one random draw from a hypothetical population, it conditions on the realized historical path and asks about alternative realizations of shocks/instruments within that history. Under this framing, the moment condition has a "design" long-run variance Ω_R that determines the correct sandwich covariance, while conventional HAC estimators converge to a strictly larger quantity Ω_R⁺ = Ω_R + Ω_μ — meaning standard HAC standard errors are systematically conservative (too wide, t-stats biased toward zero) relative to the design-correct benchmark. The authors show a projection adjustment using predetermined covariates can shrink this HAC gap, and demonstrate the effect size in a monetary-policy application via Monte Carlo.

## Why it might be useful

Directly bears on CLAUDE.md's hard-wired methodology: "Excess returns, HAC lag-6" and `sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})` are used as the default inference tool everywhere in this repo. This paper's claim — that conventional HAC is conservative, not anti-conservative — cuts directly against a common overfitting worry. It's relevant to the sector_hothand_propfirm audit currently flagged as mandatory in CLAUDE.md (`t_HAC alpha=10.38` red flag, "audit obligatoire avant promotion", `_audit/sector_hothand_audit_2026-05-30.md`): if standard HAC is conservative per this paper, an already-high t=10.38 computed via standard HAC is if anything an understatement relative to the design-correct SE, which argues the anomaly is either genuinely strong or the audit needs to look elsewhere (data snooping, AMTP, look-ahead) rather than at HAC SE choice itself. Also relevant to L12b (autocorrelation HAC deflation, ETH netflow case) as a companion result — that lesson is about HAC deflating an inflated raw t-stat for persistent-regime signals, while this paper is about HAC being conservative for the finite-history estimand; both point at HAC magnitude/direction issues worth being precise about in the next audit write-up.

## Extracted content

The paper claims a specific decomposition: **Ω_R⁺ = Ω_R + Ω_μ**, where Ω_μ ⪰ 0 is the long-run variance of the centered mean-moment path, and states "HAC inference is therefore conservative for scalar functions of the finite-history estimand." No numeric Monte Carlo results are given in the excerpt beyond this qualitative claim.

## Action proposed

TEST_LATER

Directly relevant to the pending sector_hothand_propfirm audit, but this is a methodological refinement to an inference framework, not a strategy test — read the full paper before finalizing the audit's HAC-related conclusions (medium cost: understanding + potentially implementing the projection adjustment is a 1-3 day task, not urgent enough to preempt the audit already scheduled).
