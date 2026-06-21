# Diagnostic Framework for Identifying Influential Observations in Interest Rate Model Calibration

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.20420
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: cc8cd31865c7cbc6fb9b6f289c445efc

## Summary
Calibrating multi-factor interest rate models (specifically G2++) by minimizing RMSRE is shown to be equivalent to a Weighted Least Squares problem, which enables direct application of classical regression diagnostics. The paper derives a Weighted Hat Matrix for leverage analysis, Influence Functions for local sensitivity, and the Functional Delta Method for confidence intervals respecting parameter boundaries. Applied to Euro ATM caps from 2016-2025, the analysis reveals boundary-dominated leverage and a diagnostic regime shift around the post-2022 rate environment transition. The framework makes calibration uncertainty and data influence explicit rather than treating calibration as a black-box point estimate.

## Why it might be useful
The ZN Baltussen bond futures momentum research at `Futures/research/active/zn_baltussen/` relies on interest rate dynamics as a core driver of the signal; the post-2022 regime shift in rates identified in this paper (boundary-dominated leverage) is exactly the out-of-sample period that most bond momentum strategies must survive. The influence function approach—identifying which specific cap quotes drive calibration—could inform a data quality filter for the ZN research: if the signal depends on G2++ calibration to swaptions or caps, knowing which market quotes are most influential allows targeted stress testing. More broadly, the RMSRE≡WLS equivalence is a useful result for any parameter estimation done in the project where the loss function needs diagnostic interpretation.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Interest rate model calibration diagnostics; primarily useful for ZN Baltussen regime analysis but requires reading the full paper to extract the specific diagnostic formulas.
