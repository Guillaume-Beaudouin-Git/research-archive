# Do Better Volatility Forecasts Lead to Better Portfolios? Evidence from Graph Neural Networks

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.19278
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 7a018511cc7da7809f02ba9b64777fa1

## Summary
This paper directly tests whether better volatility forecasts translate to better portfolio performance, using 465 S&P 500 equities from 2015–2025. GraphSAGE models built on rolling correlation, sector, and Granger-causal graphs are compared against HAR (Heterogeneous Autoregressive) and LSTM baselines for weekly realized volatility prediction. The empirical finding: the model with the lowest forecast MSE (GraphSAGE-Granger) does NOT produce the best portfolio, and HAR — despite higher forecast error — produces superior risk-adjusted returns when used for volatility targeting. The paper attributes this disconnect to model overfitting on the volatility forecast objective while ignoring portfolio-relevant structure.

## Why it might be useful
This directly validates the vol-targeting design choice in Strategy A. The `signal.py:13` uses a simple 28-bar rolling vol (equivalent to a simplified HAR without AR terms) — and this paper's finding that HAR outperforms GNN for portfolio purposes supports that simple approach. The study also confirms the daily vol-targeting mandatory rule in CLAUDE.md: sophisticated vol forecasts don't help if they're optimized for forecast MSE rather than portfolio performance. For the `Do Better Volatility Forecasts` context: this paper says "no, not automatically." Before any vol estimation upgrade in Strategy A or B, read this paper to assess whether the upgrade would actually improve portfolio Sharpe or just forecast accuracy.

## Extracted content
"The model with the lowest forecast MSE, the GraphSAGE-Granger model, does NOT produce the best portfolio." HAR baseline "produces superior risk-adjusted returns" despite higher MSE. Data: 465 S&P 500 equities, weekly realized vol, 2015–2025. The disconnect is attributed to "overfitting on the volatility forecast objective while ignoring portfolio-relevant structure."

## Action proposed
REFERENCE

Validates the current 28-bar rolling vol approach in Strategy A. Cross-reference if vol estimation upgrade is ever proposed. Key insight: optimize vol models for portfolio Sharpe, not forecast MSE. Methodology applicable to Strategy D vol targeting design.
