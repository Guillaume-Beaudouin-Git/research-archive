# Double Descent and Benign Overfitting in Macroeconomic Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.15358v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 15ddde80a83b18571895c53ccb5b7a3f

## Summary
The paper documents that double-descent risk curves arise in standard macroeconomic factor datasets (FRED-MD, FRED-QD), and characterizes the conditions under which benign overfitting holds. The key insight is that macroeconomic panels have moderate N/T ratios that don't naturally satisfy the overparameterization needed, so the authors augment the data with synthetic copies from an estimated factor model, effectively constructing a kernel ridge regression with a factor-structured kernel. The resulting estimator consistently outperforms the Stock-Watson factor model for point forecasting, with gains increasing at longer horizons. The interpretation: benign overfitting succeeds because overparameterization implicitly builds a well-structured kernel, not because overfitting is intrinsically desirable.

## Why it might be useful
The finding that benign overfitting works through implicit kernel construction has a direct implication for Strategy D research: if NQ intraday features (realized vol, overnight gap, pre-market volume) have a latent factor structure, adding synthetic data copies via a factor model could improve regime classification before the HMM is fitted. More importantly for CLAUDE.md methodology: the paper explains why some strategies that appear overfit (high in-sample Sharpe from complex models with many features) still generalize — but only when the overparameterization acts as kernel regularization, not arbitrary parameter search. This formalizes the intuition behind the DSR (Deflated Sharpe Ratio) requirement for strategies with N_mod > 5: without this regularization interpretation, adding parameters is pure noise mining. No direct implementation path without reading the full paper.

## Extracted content
No code in excerpt. The authors report that augmentation with synthetic copies "consistently outperforms the Stock-Watson factor model for point forecasting across all series and horizons, with gains that are pervasive, statistically significant, and increasing with the forecast horizon."

## Action proposed
REFERENCE — Theoretical background on overfitting in factor models. Reinforces the DSR/AMTP framework already in CLAUDE.md. No direct test path without a macro forecasting application.
