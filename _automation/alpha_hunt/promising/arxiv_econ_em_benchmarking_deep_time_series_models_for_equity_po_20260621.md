# Benchmarking 15 Deep Time Series Models for Equity Portfolios: Net Sharpe Negative at 20bps

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.09420
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 4900a0ca1df8b83dc5d4dcd2afa40d16

## Summary
A rigorous benchmark of 15 deep and statistical time-series forecasting architectures (transformers, RNNs, classical models) for daily equity portfolio construction on CRSP data (2018-2024). The benchmark uses stochastic multi-criteria acceptability analysis (SMAA) and a deployment-adjusted index that penalizes models whose per-criteria wins generate high portfolio regret. A constrained quadratic portfolio layer enforces capacity, beta, industry, risk, leverage, and turnover constraints. The main finding: TransEnc-8 has the highest rank-1 acceptability (0.352) but no model exceeds ~0.36 acceptance probability. Critically, at 20 basis points transaction costs, the baseline constrained-QP net Sharpe is negative for every model.

## Why it might be useful
This is the strongest existing evidence against deep learning for daily equity portfolio construction at retail transaction costs — directly relevant to the archived `jt_momentum_cs` (equities CS Sharpe -0.026, SKIP), which found similar results. The SMAA methodology is superior to simple Sharpe comparison for model selection because it integrates preference uncertainty; this could be applied to our WF fold evaluation in Strategy C/D analysis instead of reporting single-point Sharpe. The Deployment Adjusted Acceptability Index (DAAI, a Gibbs-form entropic update from the SMAA prior) is interesting for comparing D3 vs D5 vs D3+D5 portfolio model performance in `Futures/research/active/strategy_d/`. Most important takeaway: if costs are ≥20bps, no deep learning model generates positive net Sharpe — confirms L43 (retail FX intraday flat is cost-dead) at a broader level.

## Extracted content
"No architecture dominates the raw benchmark: TransEnc-8 has the largest rank-1 acceptability, 0.352, and no model exceeds about 0.36."

"The baseline constrained-QP net Sharpe at 20 bps is negative for every promoted model."

No code in excerpt. Benchmark dataset: CRSP.

## Action proposed
REFERENCE

Valuable negative result confirming cost-is-king for equity DL. SMAA methodology interesting for Strategy D model comparison but not urgent — only needed when D3/D5 combination has positive results to compare.
