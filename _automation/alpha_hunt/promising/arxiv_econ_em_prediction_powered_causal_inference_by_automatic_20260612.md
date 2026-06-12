# Semi-Supervised Causal Inference with Debiased ML: Lower Variance via Auxiliary Unlabeled Data

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.12892v1
**Captured**: 2026-06-12 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: fc60a97fc97964a391c0c832b971fda5

## Summary

This paper extends the Debiased Machine Learning (DML) framework to a semi-supervised setting where unlabeled auxiliary regressors are available alongside labeled outcome-regressor pairs. The central theoretical result is that incorporating auxiliary unlabeled data in the efficient influence function can strictly reduce asymptotic variance below the labeled-data-only efficiency bound — a non-trivial gain when labeled observations are scarce. Two estimators are proposed: EE-DML-PPCI (estimating equations) and TMLE-DML-PPCI (targeted learning), both shown to achieve the new semi-supervised efficiency bound. A key technical contribution is semi-supervised generalized Riesz regression with proven convergence rates, which is needed to estimate the Riesz representer component of the efficient influence function. Coverage extends to semiparametric causal parameters including average treatment effects and structural coefficients under Neyman orthogonality.

## Why it might be useful

One concrete methodological link. The HAC/DML estimation chain used across this repo for IC feasibility checks (`sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})`) already exploits Neyman orthogonality in spirit. The DML-PPCI extension becomes specifically relevant in the label-scarcity regime: Strategy B has N<250 testnet fills (L14), which makes standard IC t-statistics unreliable — the labeled sample is sparse while a much larger pool of unlabeled HL market observations (price, funding, order book snapshots) is available alongside them. In principle, the PPCI framework could tighten confidence intervals on B's IC estimates without waiting for more live fills, by treating unlabeled market microstructure snapshots as auxiliary regressors in the causal model for carry returns. This is not a near-term implementation — it requires building the semi-supervised Riesz regression infrastructure — but it is the correct theoretical reference if the L14 label-scarcity problem in B's IC estimation is ever revisited formally. Also relevant to sector_hothand_propfirm (`Equities/research/active/sector_hothand_propfirm/`) where the suspiciously high t_HAC=10.38 warrants a DSR/causal audit; DML orthogonal scores could be used to cleanly separate the causal treatment effect from confounding sector momentum.

## Extracted content

No code in the excerpt. No specific Sharpe or return claims; this is a theoretical econometrics paper. Key formal result cited: "the asymptotic variances of both estimators match our derived efficiency bound" (the semi-supervised bound, strictly lower than the labeled-only bound when auxiliary regressors are informative). The Riesz representer convergence rate guarantee is stated but not quantified in the excerpt.

## Action proposed

REFERENCE
