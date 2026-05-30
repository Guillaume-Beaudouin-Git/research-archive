# Regime-Based Portfolio Allocation via 3-State HMM and Reinforcement Learning

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.27848v1
**Captured**: 2026-05-30 18:06 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 72b9af0a64b0e184a1d1ff773a4fb957

## Summary
This paper builds a regime-aware allocation framework on daily SPY/TLT/GLD data from 2004-2025. A 3-state Gaussian HMM (low-volatility, transitional, high-volatility) is selected over 2-state alternatives via BIC. State-conditional analysis confirms that SPY dominates returns in stable regimes, while TLT and GLD provide drawdown protection in stressed states. A reinforcement learning policy is then trained on top of HMM regime labels to dynamically adjust allocations across the three assets. Both the rule-based and RL-based HMM strategies outperform a passive SPY benchmark on a 30% OOS window with a one-day execution lag, with the RL variant achieving the best risk-adjusted returns. Sensitivity analysis confirms the 3-state specification is robustly superior to the 2-state alternative.

## Why it might be useful
Two concrete links to Algo_claude. First, Strategy D (D3+D5 portfolio, NQ intraday, active research, 0/3 modifications consumed) has "regime filter under study" explicitly noted in CLAUDE.md as one of the proposed paths to recovering from D3 (Sharpe=-1.08) and D5 (Sharpe=-1.32) failing individually. This paper's 3-state HMM is directly implementable as a regime gate on NQ 1-min data (Dataset_NQ_1min_2022_2025.csv, available locally): fit HMM on realized volatility or return variance over a rolling window, restrict D3 entries to low-volatility regime and D5 entries to transitional/high-volatility regime. This consumes modification #1 on D3 or D5, within the 3-mod budget. Second, L15 in CLAUDE.md warns that regime overlays on high-Sharpe (SR>1.0) strategies yield sub-threshold lift (~1.7%/yr, Δ=+0.022%/day) — but that lesson applies to overlays on profitable baselines. D3+D5 have negative Sharpes, so the regime filter acts as a trade-count reducer rather than an overlay; the L15 ceiling does not apply here. Skip the RL layer for the initial test: HMM-only is the testable, interpretable component that fits within the modification budget.

## Extracted content
The authors claim the RL policy achieves "the highest risk-adjusted performance, delivering the strongest Sharpe ratio and materially lower drawdowns" relative to both rule-based HMM allocation and passive SPY benchmark (2004-2025 daily, 30% OOS ≈ 2019-2025). Three HMM states characterized as low-volatility, transitional, and high-volatility, with "strong persistence" (high self-transition probabilities). State-conditional dynamics: SPY dominates stable regimes; TLT and GLD provide protection during stressed periods. BIC selects 3-state over 2-state; sensitivity analysis confirms robustness of this choice. No specific Sharpe or MaxDD values reported in the abstract.

## Action proposed
TEST_LATER — HMM regime gating is testable on local NQ 1-min data and is one of the candidate modifications for Strategy D. Requires reading the full paper to extract HMM covariance parameterization and initialization approach before translating to NQ intraday. Estimated implementation: 0.5 day. Block: do this only after the D3+D5 combined portfolio baseline is established in `Futures/research/active/nq_intraday/analysis/`.
