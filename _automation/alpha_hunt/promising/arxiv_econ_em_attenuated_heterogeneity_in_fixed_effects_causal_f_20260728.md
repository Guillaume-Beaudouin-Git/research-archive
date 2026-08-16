# Attenuated Heterogeneity in Fixed-Effects Causal Forests, and a Cross-Fitted Correction

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.22896v1
**Captured**: 2026-07-28 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a94f38cb453fe1efebea6b89ab9c816a

## Summary
Shows that causal forests estimating conditional average treatment effects (CATEs) in fixed-effects panel settings systematically shrink (attenuate) the estimated heterogeneity toward the average effect — the raw prediction behaves like a + b*tau(x) with slope b < 1 — and that the usual additive recentering used to report an unbiased ATE does not fix this compression. Proposes an out-of-bag "de-attenuation" calibration (adapting Chernozhukov et al.'s best-linear-predictor approach) that cuts CATE mean-squared error 25-42% in simulation, shipped as a Python package (`causalfe`).

## Why it might be useful
No current strategy uses causal forests, but this is directly relevant if any future cross-sectional research tries to estimate heterogeneous treatment effects across instruments — the exact shape of L44's cross-sectional IC contrast or L49's calendar-effect placebo tests, which implicitly estimate CATE-like heterogeneity across a panel of assets with instrument fixed effects. The paper's warning that naive heterogeneity estimates are systematically compressed, and that simple recentering does not fix it, is a concrete pre-registered caveat to apply before citing any future heterogeneous-effect result.

## Extracted content
No code (package name only: `causalfe`). Numeric claim (author's): the proposed calibration "cuts CATE mean-squared error by 25-42% relative to the recentering default" in simulation.

## Action proposed
REFERENCE.
