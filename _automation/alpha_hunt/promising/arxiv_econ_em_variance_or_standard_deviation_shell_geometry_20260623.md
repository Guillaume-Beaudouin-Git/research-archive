# Variance vs. Standard Deviation as Default Prior: Implications for High-Dimensional Shrinkage

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.23509v1
**Captured**: 2026-06-23 03:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 941fe868726e38ae0b7ed0b0e6433c73

## Summary

This paper examines how the choice of scale parameterization — variance vs. standard deviation — for a global-scale prior fundamentally changes shrinkage behavior in high-dimensional settings. The authors show that SD-flat and variance-flat priors place very different probability mass near the zero-signal boundary, causing divergent risk profiles: SD-flat priors carry a one-unit asymptotic risk advantage near the origin but eventually converge for strong signals. For sparse signals (many near-zero) the prior shape at the origin dominates estimation risk. The result extends to mixtures and bounded coordinate-multiplier shrinkage, and the key classifier is the near-zero exponent of the standard-deviation-scale density.

## Why it might be useful

This is directly relevant to any shrinkage-based covariance estimation used in portfolio sizing, particularly for Strategy B (delta-neutral carry) where the signal is sparse and carried on a handful of assets. The CLAUDE.md methodology requires daily vol targeting (5 mandatory fixes item 3) and HAC-robust estimation — both implicitly depend on how variances/correlations are estimated when asset counts are small or signals are near-zero. In practice, most quant toolkits default to variance-scale priors (e.g., Ridge, Ledoit-Wolf) without justifying the choice against SD-scale alternatives; this paper gives a principled criterion. It also speaks to AMTP correction: when running multiple strategy tests (n_tests=321 global), the estimator used to normalize Sharpe ratios under the null matters — an SD-flat prior will shrink weak signals more aggressively, which aligns better with conservative DSR requirements. Concrete action: check whether `Portfolio/risk/propfirm_canonical.py` covariance defaults use variance-scale or SD-scale shrinkage, and note whether switching would tighten the MaxDD estimate for A+B book.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

Background prior-selection theory; no direct tradable edge but informs covariance estimation choices in sizing code. Useful when revisiting the ERC weighting of A+B book or expanding to a Strategy D universe with sparse signals.
