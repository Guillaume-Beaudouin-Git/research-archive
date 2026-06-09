# Inference on TSLS Estimand under Weak Instruments and Heterogeneous Treatment Effects

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.07871v1
**Captured**: 2026-06-09 06:04 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 3069e73dd4239a24a78945fe450a96b2

## Summary
Standard IV regression inference (TSLS coefficient) breaks down when instruments are weak, inflating type-I error. Classic remedies — the Anderson-Rubin AR test, Kleibergen-Moreira LM, and Moreira CLR tests — are valid under homogeneous treatment effects or a single instrument, but fail in the over-identified heterogeneous-effects case. This paper introduces a TSLS likelihood ratio (TLR) statistic combined with a two-step Berger-Boos procedure, which achieves uniform validity across weak- and strong-instrument regimes while recovering the standard Wald test in the strong-instrument limit. The two-step level adjustment can be made small enough that the test is numerically near-identical to Wald when instruments are strong.

## Why it might be useful
The direct trading application is thin, but this matters for the methodology stack. When testing causal claims in strategy research — e.g., whether a macro variable (credit spread, FOMC surprise) *causes* returns rather than merely correlates — IV-based tests arise naturally and the weak-instrument problem is endemic with macro instruments (low first-stage F is common with monthly data). The TLR approach could replace ad hoc Wald inference in causal robustness checks for future macro-overlaid strategies. This does not open a new test on A/B/C directly, but is a methodological upgrade for any future strategy using instrumental variables (e.g., a ZN Baltussen bond-momentum variant using surprise-rate as an instrument, currently active in `Futures/research/active/zn_baltussen/`). If that research reaches causal attribution testing, apply TLR rather than naive Wald with potentially-weak instruments.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
