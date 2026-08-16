# Modeling the Dynamic Relationship Between Brent Crude Oil Prices and the Nepal Stock Exchange: An Integrated Econometric and Explainable Machine Learning Approach

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.11922v1
**Captured**: 2026-07-15 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: c132fd8e8cde28f1fba520b5d58464e7

## Summary
Studies the relationship between Brent crude oil prices and the Nepal Stock Exchange (NEPSE) over 2013-2026 using Granger causality, EGARCH, and DCC-GARCH alongside Random Forest/LightGBM/XGBoost with SHAP-based explainability. Finds a statistically significant one-directional Granger causality from oil to NEPSE with a four-day lag, high volatility persistence in both series, weak but time-varying conditional correlation, and — via the ML explainability layer — that NEPSE's own momentum/short-term volatility dominates its behavior, with oil only a minor, method-dependent contributor.

## Why it might be useful
Weak direct tie — Nepal Stock Exchange is not a tradable instrument for this project and the oil-equity link found is explicitly "minor." The transferable point is methodological: pairing classical Granger/GARCH econometrics with an ML explainability layer (SHAP) to check whether a classical significance result is actually driving out-of-sample behavior is a useful template for validating any future macro-cross-asset signal (e.g., an oil-driven overlay on commodity-linked equities or FX), consistent with the project's own preference for direct diagnostics (dir accuracy, quintile monotonicity) over pure in-sample significance.

## Extracted content
Numeric claim (author's): "unidirectional Granger causality from Brent crude oil to NEPSE with a four-day lag." No code/formulas reproduced.

## Action proposed
REFERENCE.
