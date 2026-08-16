# Can Machines Learn Weak Signals? Ridge > Zero > Lasso

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=h6OyCHcWeW&amp;source=feedburner
**Captured**: 2026-07-22 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e7114e3042f92acf661bcd7ee7e547ee

## Summary
The post (via Aligrithm) reports feeding roughly 920 firm characteristics into a Lasso regression to predict next-month stock returns, and finds Lasso underperforms the trivial "predict zero" baseline — the sparse estimator actively destroys value relative to doing nothing. The implied argument is that Ridge, which shrinks all coefficients toward zero rather than selecting a sparse subset, beats both Lasso and the zero baseline, suggesting true cross-sectional predictive signal in a large characteristic set is diffuse and dense rather than concentrated in a handful of features. This is a methodological point about estimator choice under weak, dense signal-to-noise conditions, not a specific tradable strategy.

## Why it might be useful
This is a pure equities factor-zoo result (920 US firm characteristics) with no direct crypto or futures analog in this repo's active strategies, so there's no near-term data or implementation path. Its value is methodological: it's a concrete empirical illustration of the same overfitting risk the repo already guards against via DSR/AMTP (L20 — DSR mandatory once n_mod>=2) — a sparse, aggressively-selected model (Lasso) that looks reasonable in-sample can be strictly worse than doing nothing once weak/dense signal structure is mismatched to the estimator's selection bias. It's a useful cautionary reference for the `_automation/feasibility/` Level-B handlers (walk-forward + bootstrap + DSR) if any future cross-sectional hypothesis (e.g. a multi-feature extension of Strategy A's single momentum signal) is ever built with feature selection rather than a single hand-specified formula.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt beyond "920 firm characteristics" and the qualitative Ridge > Zero > Lasso ranking. Full article needed for further extraction (actual Sharpe/IC numbers not in the captured excerpt).

## Action proposed
REFERENCE — equities factor-zoo ML result, no local data pipeline or active-strategy fit; useful as a methodological cautionary note on estimator choice under weak/dense signal conditions, not a test candidate.
