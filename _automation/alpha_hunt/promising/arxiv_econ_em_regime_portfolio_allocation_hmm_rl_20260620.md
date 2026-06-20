# Regime-Based Portfolio Allocation Using Hidden Markov Models and Reinforcement Learning

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.27848
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: d7f27c0a2cce2c89e0b7273c38de4ec6

## Summary
This paper builds a regime-aware allocation system that combines Hidden Markov Models (HMM) for regime identification with Reinforcement Learning (RL) for dynamic portfolio weights across SPY (equity), TLT (long bonds), and GLD (gold), using daily ETF data from 2004–2025. A 3-state Gaussian HMM selected via BIC identifies low-volatility, transitional, and high-volatility regimes. The RL agent then learns regime-conditional allocations that adapt to regime changes identified by the HMM. The study compares this hybrid against static 60/40 and full HMM-only baselines, finding meaningful improvement in risk-adjusted performance during transition periods.

## Why it might be useful
The book-level (A+B) Sharpe of 2.31 relies on a static ERC 50/50 split between strategies. A regime-conditional overlay — suppressing A (frozen) during high-crypto-volatility regimes or adjusting B's notional — is a potential future book-level improvement. The 3-state HMM framework here is directly applicable using daily BTC/ETH/SOL returns already in `data/raw/`. However, L15 warns: regime overlays on high-Sharpe strategies (SR > 1.0) provide sub-threshold lift (~1.7%/yr, Δ = +0.022%/day). Read Section 3 to check whether the reported improvement exceeds this L15 threshold before pursuing. The Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) could benefit from regime conditioning as a Phase B enhancement.

## Extracted content
The paper compares: (1) 60/40 static, (2) pure HMM-conditional weights, (3) HMM + RL hybrid. Three regimes: "low-volatility, transitional, and high-volatility" selected by BIC on a 3-state Gaussian HMM. Uses SPY/TLT/GLD daily ETF data 2004–2025. No specific Sharpe numbers given in the abstract. Full results in Table 2 (mentioned in the paper).

## Action proposed
TEST_LATER

Read Section 3 (regime identification) and Table 2 (performance comparison). If Sharpe improvement > L15 threshold (1.7%/yr), consider implementing as a portfolio-level regime filter for the A+B book. Data available locally (daily returns). Priority: after B mainnet (~2026-07-17) and book recalc. Budget: 1-2 days for HMM estimation on BTC/ETH/SOL returns.
