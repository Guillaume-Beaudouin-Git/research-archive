# Financially Guided Deep Portfolio Optimization: End-to-End Sharpe/CVaR/Risk-Parity

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.28853
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: e9bcecbc459b34d79bd4cc0afdb84f9c

## Summary
This paper proposes an end-to-end deep learning framework that directly optimizes differentiable surrogates of financial metrics — Sharpe ratio, Omega ratio, Conditional Value-at-Risk (CVaR), and Risk Parity — rather than first predicting returns and then optimizing. The framework bypasses the predict-then-optimize error-compounding problem by backpropagating through the portfolio objective function itself. Results on historical data show that the Sharpe surrogate objective outperforms mean-variance and naive baselines under regime shifts, while the Risk Parity surrogate converges to the closed-form ERC solution when the network is properly initialized.

## Why it might be useful
The Risk Parity surrogate's convergence to ERC is directly relevant to the A+B book's current ERC allocation (`Portfolio/state/portfolio_state.py`). The finding that end-to-end Sharpe optimization outperforms mean-variance under regime shifts is worth noting when book D is eventually added (new strategy D gate: SR > 1.10 × 2.31 = 2.54). However, this framework requires differentiable portfolio construction — straightforward for a continuous-weight book (A+B) but more complex with the propfirm constraints (FTMO daily caps, Propr DD limits). The end-to-end approach also requires a stationary return distribution for training, which is problematic for the non-stationary crypto/futures environment.

## Extracted content
"Directly optimizes differentiable surrogates of key financial metrics — Sharpe ratio, Omega ratio, Conditional Value-at-Risk (CVaR), and Risk Parity." "Portfolio optimization in real-world financial markets is notoriously difficult due to non-stationarity, noisy data, and high transaction costs." The Risk Parity surrogate "converges to the closed-form ERC solution when the network is properly initialized."

## Action proposed
REFERENCE

The ERC convergence result confirms the theoretical basis for the current A+B ERC allocation. The Sharpe surrogate approach could inform future book-level optimization when Strategy D is added, but requires stationary return assumptions. Cross-reference with `Portfolio/risk/propfirm_canonical.py` for implementation constraints.
