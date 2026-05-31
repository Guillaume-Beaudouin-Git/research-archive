# Heavy Tails and Predictive Ability Testing

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.16866v2
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 1a87ff5086de4d958134dcf4ac814a46

## Summary
When forecast error loss differentials exhibit heavy tails (specifically, infinite variance), the Diebold-Mariano test statistic converges to a non-Gaussian stable random variable rather than the normal distribution assumed by classical critical values. This causes severe size distortion: a nominal 5% test may reject a true null up to 70% of the time. The paper develops a stable limit theorem for strongly mixing, infinite-variance time series and proposes subsampling-based inference that is valid regardless of tail heaviness without requiring estimation of long-run variances or tail indices. An application to emerging market exchange rate forecasting shows that accounting for heavy tails substantially reverses conclusions about which models are superior.

## Why it might be useful
This paper is directly relevant to CLAUDE.md's HAC-based significance testing. Strategy C (NQ ORB) and the sector_hothand research both rely on HAC-corrected t-stats. NQ intraday returns exhibit fat tails — the opening auction and first 5 minutes can produce extreme returns that would qualify as heavy-tailed loss differentials. If the error distribution has infinite variance, HAC lag-6 critical values are invalid and the t > 2.5 threshold is meaningless. Concretely: before declaring Strategy C's IC_t significant, run a tail index test (Hill estimator or Pickands estimator) on the fold-level Sharpe differences. If the tail index α < 2 (infinite variance regime), switch to subsampling-based inference for the WF validation. The sector_hothand's t_HAC=10.38 (red flag per CLAUDE.md audit) should also receive this diagnostic before promotion.

## Extracted content
The authors report: "a nominal 5% test may reject a true null as often as 70% of the time" when loss differentials have infinite variance. Subsampling-based inference "remains valid irrespective of tail-heaviness and requires no estimation of long-run variances or tail indices." Application to emerging market FX shows conclusions "can substantially alter" relative to standard procedures.

## Action proposed
TEST_LATER — Add a tail index diagnostic (Hill estimator) to the Strategy C and sector_hothand validation notebooks. If tail index < 2, replace HAC critical values with subsampling bounds. 1-day effort. Addresses the sector_hothand audit red flag from a different statistical angle.
