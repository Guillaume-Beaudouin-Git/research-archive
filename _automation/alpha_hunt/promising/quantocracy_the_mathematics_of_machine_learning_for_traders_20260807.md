# The Mathematics of Machine Learning, for Traders

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=19kOH9VJAb&source=feedburner
**Captured**: 2026-08-07 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: bc9d47f0cbb34ec8a80e9a7aada373c1

## Summary
This is a continuation of an educational series that previously walked readers from a single decision tree through random forests to gradient boosting ("From One Tree to Forests to Boosting"), with prior installments also covering how a decision tree engineers features. This entry appears to move from the applied/intuitive treatment of those models to their underlying mathematics. No specific dataset, trading application, or performance claim is present in the excerpt — it reads as general ML pedagogy, not a strategy write-up.

## Why it might be useful
None of the three active strategies (A's tanh-based TSMOM signal, B's funding-carry threshold, C's ORB rule set) currently uses a fitted ML model — all are hand-specified rules — so there's no direct hook into an existing signal. The relevance is methodological risk management: if any future hypothesis in `_automation/feasibility/`'s Generic handler ever proposes a tree/boosting-based signal, L20 ("DSR obligatoire dès N_mod ≥ 2") becomes far more binding for ML models than for simple rule-based ones, since hyperparameter search and feature engineering choices each effectively count as additional trials against the DSR budget — this article would be useful background on the model family's internals before any such hypothesis is scored through the 3-level gate pipeline (A: IC; B: WF+bootstrap+DSR; C: sanity checks).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
