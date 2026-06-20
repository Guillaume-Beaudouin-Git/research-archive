# Hybrid Gaussian Process Regression for Stable Volatility-Covariance Estimation

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.17275
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 00365fd6d61ae49315326d4c60f2e921

## Summary
This paper proposes a hybrid Gaussian Process Regression (GPR) framework for covariance matrix estimation, motivated by the instability of GARCH-family models under stress scenarios. Standard GARCH and EWMA approaches systematically underestimate tail covariances during crises because they assume parametric distributional forms. The hybrid GPR blends a mean-function prior (structural model) with a GP posterior update (non-parametric correction), producing covariance forecasts that are more stable under stress while retaining interpretability. Evaluated on global equity indices, the hybrid outperforms GARCH and EWMA on realized covariance error during 4 major stress events (2008, 2011, 2015, 2020).

## Why it might be useful
The A+B portfolio's MaxDD estimate ("to be measured on ≥60 days live B mainnet" per CLAUDE.md) requires a covariance model for A+B joint risk. Currently, the `_audit/portfolio_recalc_2026-06-10.md` notes the MaxDD is unmeasured due to Strategy B backtest's 92% zero-return days. A GPR-based covariance model that handles sparse return series (Strategy B's high zero frequency) could improve the A+B MaxDD estimation. The hybrid approach is also relevant if the portfolio eventually expands to N≥10 instruments — GARCH instability under stress is manageable for 3 assets but becomes more problematic with larger covariance matrices.

## Extracted content
"Traditional econometric models, including GARCH-family and EWMA approaches, suffer from parametric rigidity, distributional assumptions, and numerical instability under stress, leading to systematic underestimation of tail risks." Hybrid GPR blends structural prior with GP correction. Tested on "ICAAP and CCAR" stress scenarios. Outperforms on 4 stress events: 2008, 2011, 2015, 2020.

## Action proposed
REFERENCE

File for future A+B MaxDD estimation upgrade, particularly relevant when Strategy B's live data accumulates (~60 days post-mainnet). The GP correction for sparse return series (B's 92% zero-return days) requires adaptation before direct use. Lower priority than operational issues.
