# Self-Normalized Tests for Multistep Conditional Predictive Ability

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.07404v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[methodology], L2_OK
**Hash**: e26b10da3f258deb9d85db33b0584861

## Summary
The paper proposes self-normalized tests for comparing predictive ability at multiple forecast horizons simultaneously. By normalizing the mean loss differential via CUSUM-based functionals — an adjusted-range normalizer for scalars, a matrix normalizer for vectors — the approach avoids estimating the long-run covariance matrix (which requires bandwidth and kernel selection). The asymptotic theory establishes pivotal null distributions and consistency. Monte Carlo simulations show that the self-normalized tests reduce finite-sample size distortions relative to traditional HAC-based methods, while retaining power against conditional predictability alternatives.

## Why it might be useful
CLAUDE.md mandates HAC Newey-West (lag-6) as the standard significance test. This paper proposes an alternative that avoids the ad-hoc bandwidth choice inherent in HAC — a known limitation especially on small samples. The most concrete application is Strategy C walk-forward IC testing: the 9-fold, 346-trade dataset is marginal for HAC reliability (T=346 gives N_eff of perhaps 50-100 after HAC deflation). Self-normalized tests would provide an honesty check on whether HAC lag-6 inference is inflated by the bandwidth choice. For the active sector_hothand research (t_HAC=10.38, audit flagged), a self-normalized test would help determine whether the extreme t-stat reflects a genuine edge or HAC lag selection artifacts. The CUSUM-based normalization is implementable via statsmodels or from scratch in Python.

## Extracted content
The paper demonstrates that "self-normalized tests effectively mitigate finite-sample size distortions associated with traditional HAC methods, while retaining strong empirical power." No specific rejection rates or numerical comparisons are reported in the abstract.

## Action proposed
TEST_LATER — Apply the self-normalized test as a robustness check alongside HAC lag-6 in the Strategy C WF IC analysis and the sector_hothand audit. Directly addresses the "t_HAC=10.38 red flag" flagged in CLAUDE.md. 1-day effort to implement from the paper's CUSUM normalizer formula.
