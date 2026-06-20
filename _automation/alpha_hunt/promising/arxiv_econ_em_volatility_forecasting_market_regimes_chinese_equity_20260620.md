# Regime-Augmented Volatility Forecasting and Return Prediction in High-Frequency Chinese Equities

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.09478
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: e0de61060302c2b877f956f389dac745

## Summary
This paper develops a two-stage framework for jointly predicting realized volatility and returns in Chinese equity markets. The first stage uses regime-augmented HARQ (HAR with quarticity) combined with Markov-switching GJR-GARCH to capture regime-dependent volatility dynamics. The second stage applies ML models (XGBoost, random forest, LSTM) conditioned on the estimated regime state to predict next-period returns. Evaluated on CSI 300 Index data from 2005–2023 using expanding-window walk-forward validation, the combined framework improves both volatility forecast MSE and economic strategy performance over single-regime benchmarks.

## Why it might be useful
The Markov-switching GJR-GARCH component is relevant to Strategy A's volatility estimation. Strategy A uses a 28-bar rolling log return vol (hard-coded at `signal.py:13`); a regime-augmented vol estimator could improve signal quality. However, L15 warns that regime overlays on high-Sharpe strategies provide sub-threshold lift. The more direct application is to the Commodities XS pipeline: commodity futures exhibit strong regime dependence (backwardation vs. contango cycles), and a two-stage framework (vol regime → return prediction) could serve as Phase B conditioning. The paper also demonstrates the expanding-window WF approach (matching CLAUDE.md's ≥5-fold mandate), making it a useful methodological template.

## Extracted content
Two-stage framework: Stage 1 = HARQ + Markov-switching GJR-GARCH. Stage 2 = XGBoost/RF/LSTM conditioned on regime state. Data: CSI 300 Index, high-frequency, 2005–2023. Method: expanding-window walk-forward. "Improving both statistical forecasting performance and economic strategy outcomes."

## Action proposed
REFERENCE

Use the Markov-switching GJR-GARCH specification (Stage 1) as a reference architecture for vol regime estimation in Commodities XS (Phase B). The CSI 300 domain limits direct transferability, but the framework generalizes. Cross-reference with L15 before applying to Strategy A. See also paper d7f27c0a (HMM + RL) for complementary regime approach.
