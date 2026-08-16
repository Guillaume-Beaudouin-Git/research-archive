# When Predictions Become Regressors: A Split-Sample Correction for Biases in Downstream Inference

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.02909v1
**Captured**: 2026-08-05 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 40e2d79ee74eb7193bcd140aacb7cdb7

## Summary
When a researcher builds a measure with a prediction model (an LLM or other ML classifier —
e.g., scoring policy positions from text) and then uses that predicted measure as an
explanatory variable in a regression, the prediction error creates classic
measurement-error bias in the downstream coefficient. The authors propose fixing this with
an instrumental-variables approach: generate two independent predicted measures from
separate splits of the training data, then use one as an instrument for the other in the
regression. This requires no new data collection, is simple to implement, and their
simulations show it recovers estimates close to the true coefficient even in small samples,
where the naive plug-in approach can be badly biased. They demonstrate it on two political-
science applications (gendered speech and legislative outcomes in the German Parliament;
political risk and poverty-alleviation programs in China).

## Why it might be useful
This is the one item in the batch with a genuine, concrete methodology tie: it addresses
attenuation/measurement-error bias whenever a machine-learning-predicted quantity is later
used as a regressor — directly relevant if this repo ever regresses returns or a signal on
an ML-predicted feature (e.g., an LLM-scored sentiment measure, a predicted funding-rate
regime, or any output of `_automation/feasibility`'s handler classifiers) rather than on a
directly observed variable. Right now, however, no active strategy (A, B, or C) or
feasibility-gate handler regresses on a split-generated ML prediction — the toolkit's bias
concerns are currently HAC/AMTP/DSR on observed return series, not measurement error in a
predicted regressor — so there is no live implementation target today, only a well-defined
future one if predicted-signal regressions get added.

## Extracted content
No code or formulas in the excerpt. No finance-specific numeric claims; the two illustrative
applications (German Parliament gendered speech, China poverty-alleviation political risk)
are political-science, not financial. Full article needed for the IV construction details.

## Action proposed
REFERENCE — real, well-scoped bias-correction technique for predictions-used-as-regressors,
but no current strategy or feasibility-gate step actually regresses on an ML-predicted
variable, so there is nothing to apply it to yet; revisit if that changes.
