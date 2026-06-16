# Estimating Sloppy Directions via KDE: The Case of Kirman's Ants

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.14887v1
**Captured**: 2026-06-16 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e09dc432af1fd246d234abdbf80f2025

## Summary
Nonlinear stochastic models are typically "sloppy": their predictions are sensitive to only a few parameter combinations (stiff directions) while most directions are poorly constrained (sloppy). The information-geometric framework captures this via the Fisher Information Matrix (FIM) and its eigenvectors. Previous applications required analytically known distributions. This paper demonstrates that KDE-estimated distributions converge to the analytical FIM eigenvectors and eigenvalues at simulation budgets that are computationally tractable in practice. The illustration uses Kirman's ant recruitment model — a two-state Markov system that switches between unimodal and bimodal regimes — with closed-form Hessian derivations confirming numerical convergence.

## Why it might be useful
The sloppy/stiff decomposition is a principled alternative to the implicit parameter sensitivity analysis already embedded in the CLAUDE.md methodology (DSR at n_mod≥2, max 3 modifications). In Strategy B (delta-neutral carry on HL), the key parameters are CARRY_FLOOR_8H, MIN_VOL_USD, and NOTIONAL_USD — a FIM analysis over the backtest objective would identify whether these parameters are genuinely constrained (stiff) or whether the Sharpe 4.10 backtest is robust to wide variation (sloppy, meaning overfitting risk is low). The Kirman regime-switching angle is structurally analogous to the regime detection problem in Strategy D (D3+D5 portfolio, regime filter under study) — the unimodal ↔ bimodal transition maps onto trending ↔ ranging NQ intraday sessions. However, the technique requires implementing KDE-based FIM estimation on top of existing strategy code, with no off-the-shelf statsmodels equivalent; the benefit over a simple Sharpe heatmap grid search over the parameter space is unclear without a full read. File as methodology background if Strategy B mainnet parametrization review is undertaken (~2026-07-17).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Theoretically relevant to backtest parameter robustness and the "3 modifications max" constraint interpretation, but the KDE-FIM implementation overhead is high relative to simpler grid-search Sharpe sensitivity analysis that could answer the same question in existing research code.
