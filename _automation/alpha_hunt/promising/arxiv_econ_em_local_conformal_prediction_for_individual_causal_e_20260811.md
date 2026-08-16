# Local conformal prediction for individual causal effects

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.09612v1
**Captured**: 2026-08-11 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: c855b5c28cc3d5809931450e693dd350

## Summary
Proposes "Individualized Causal Prediction" (ICP), a method for building finite-sample-valid conformal prediction intervals for one specific unit's individual causal effect (not just the average), by localizing calibration to a causally-relevant neighborhood (via causal-forest-weighted cosine similarity), augmenting small local samples synthetically, and using doubly-robust AIPW conformity scores. Shows on synthetic and IHDP benchmark data that it improves point accuracy over global conformal baselines while maintaining nominal coverage.

## Why it might be useful
No current strategy estimates individual (unit-level) treatment effects, so the direct fit is weak. The transferable idea, honestly filed as background: conformal prediction more generally is a candidate way to put a calibrated, distribution-free confidence band around a per-instrument signal score (e.g., a single asset's TSMOM signal strength) rather than relying on a pooled cross-sectional HAC estimate — relevant if the project ever wants per-instrument (not just book-level) uncertainty bands, but no active research thread currently needs unit-level rather than book-level inference.

## Extracted content
No code. No finance-specific numeric claims (validated on synthetic data and the IHDP medical benchmark, not financial data).

## Action proposed
REFERENCE.
