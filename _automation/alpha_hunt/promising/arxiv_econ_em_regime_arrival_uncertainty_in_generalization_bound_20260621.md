# Regime-Arrival Uncertainty: OOS Generalization Bounds under Markov-Switching Shifts

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.02657
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: d463e72554d4fc4d09d2d9176fbd86ed

## Summary
A framework for generalization bounds when the training/deployment regime composition (fraction of calm vs crisis periods) differs. The decomposition separates regime mismatch from regime sensitivity; extends to β-mixing data using effective sample size corrected for spectral gap; and proves a minimax lower bound validated on 25 years of global equity indices. The key finding: the proposed penalty (regime mismatch) is an ex post realized generalization gap, while the training-only estimator shows no significant correlation with it — meaning you cannot forecast the regime composition of the future deployment period from past data, so the bound is diagnostic but not predictive.

## Why it might be useful
This directly formalizes the "walk-forward ≥5 folds" requirement from our methodology (L2): in a regime-switching environment, a single train-test split will have different regime composition in train vs test, leading to misestimated generalization. The effective sample size corrected for spectral gap (β-mixing) is directly applicable to HAC SE computation: our HAC lag-6 assumption may undercount the effective sample when regimes have long autocorrelation (long calm → long crisis). For Strategy D regime filter specifically: the regime-arrival-uncertainty framework warns against calibrating D3/D5 regime gates on in-sample regime composition and expecting it to hold OOS — the regime future is unknowable, so the gate should be based on real-time observable signals (VIX, ATR), not historical regime membership.

## Extracted content
"The proposed penalty is an ex post realized generalization gap, whereas the training-only estimator does not show significant correlation: the feature geometry of crises can be detected, but not the temporal arrival."

"We extend the bound to beta-mixing data using the effective sample size corrected for the spectral gap."

Validated on "25 years of global equity indices."

## Action proposed
REFERENCE

Theoretical generalization bounds. The key practical lesson is already captured in our L2 methodology (WF ≥5 folds) and HAC SE (lag-6 corrects for autocorrelation). No new implementation needed, but useful as formal justification for our WF methodology against regime-aware critics.
