# Getting the Target Right in Return Prediction (Quantpedia, on Cakici & Zaremba)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=IKnSI8CvHY&amp;source=feedburner
**Captured**: 2026-07-24 07:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 56ebc017a6616340f9eadd3900c4a521

## Summary
A Quantpedia writeup of research by Cakici and Zaremba arguing that in machine-learning equity return prediction, the choice of *prediction target* (the dependent variable the model is trained to output) matters as much as model architecture or feature set. The implication is that many published ML-for-returns results may be sensitive to an under-scrutinized modeling decision — e.g. predicting raw next-period return versus a risk-adjusted or ranked transform of it — rather than to the features or algorithm typically credited with the edge. The excerpt is a teaser and does not give the paper's actual target definitions or performance deltas.

## Why it might be useful
This is directly relevant to how signal targets are specified across the repo's methodology toolkit: Strategy A's signal itself is a deliberately transformed target (`tanh(cumret_28d/(vol_28d*sqrt(28))).clip(lower=0)`, not raw momentum), which is exactly the kind of target-engineering choice this paper says is under-examined — worth a note when Strategy A is eventually revisited post-freeze. More concretely, it maps onto `_automation/feasibility`'s Level A IC-test step, which implicitly picks a return target for every new hypothesis; a target-definition audit (raw vs. vol-scaled vs. excess vs. ranked) could be added there to catch false negatives/positives before a candidate reaches Level B (walk-forward + DSR).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no immediate fit to an active crypto/futures strategy (this is an equities-ML methodology point), but worth folding into the `_automation/feasibility` Level A target-definition step once the full paper is read; medium cost since it requires designing and documenting a target-choice audit rather than a same-day check.
