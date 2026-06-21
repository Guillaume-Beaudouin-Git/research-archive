# Hybrid Student-t VAR + LSTM for Nonlinear Predictability in Energy ETFs

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.26890
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 98873daedacf3116ca5460050ef723a4

## Summary
A two-stage hybrid forecasting pipeline: (1) a Student-t VAR model that captures heavy-tailed linear dynamics among six ETFs (broad market, fossil energy, renewable energy, technology, utilities, plus a transition-sensitive sector), removing the Gaussian-linear component; (2) an LSTM trained on the VAR residuals to capture remaining nonlinear structure. Out-of-sample experiments show the hybrid outperforms standalone VAR, standalone ML, and alternative hybrids during macro-financial stress periods (COVID-19, Ukraine energy shock), while gains are moderate in calm regimes. The key finding is that remaining nonlinearity after linear fat-tail filtering is stress-period-localized.

## Why it might be useful
The "Student-t VAR on residuals, then LSTM" pipeline is methodologically sound and directly applicable to our A+B multi-asset book. Strategy A (TSMOM v3) uses a 28-day vol window on log returns; adding a Student-t VAR residual component for BTC/ETH/SOL return forecasting could improve vol estimation accuracy in stress periods without changing the core signal. The stress-period localization finding is important context for the portfolio MaxDD measurement ("MaxDD book: à mesurer sur ≥60j live B mainnet"): it suggests that correlation spikes between A and B will concentrate in macro stress events, which aligns with the L50 finding on funding-extremes-momentum clustering. Importantly, this paper supports using Student-t innovations rather than Gaussian for the crypto tail-risk model in `Portfolio/risk/propfirm_canonical.py` — the existing model may underestimate tail dependencies during Ukraine/COVID-type shocks. Commodities XS arc also benefits: transition-sensitive sectors show stronger nonlinearity, supporting the theoretical basis for the Basis+TSMOM signal.

## Extracted content
"The results reveal substantial departures from Gaussian-linear behavior, including excess kurtosis, volatility clustering, and remaining nonlinear dependence after econometric filtering. Out-of-sample forecasting experiments show that the proposed framework consistently improves predictive accuracy relative to conventional VAR models, standalone machine-learning methods, and alternative hybrid specifications."

"The forecasting gains become more pronounced during periods of macro-financial stress, particularly during the COVID-19 crisis and the Ukraine-related energy shock."

No code or specific numeric claims in excerpt. Full paper needed for VAR specification.

## Action proposed
TEST_LATER

Phase 1 (1 day): Apply Student-t VAR to BTC/ETH/SOL daily returns from Strategy A data, test whether residuals show significant LSTM-capturable nonlinearity (Portmanteau test on squared residuals). If yes, Phase 2: fit shallow LSTM on residuals for vol-scaling adjustment. Full implementation requires reading the paper for the VAR order selection and LSTM architecture. LATER because the TSMOM signal is frozen (Propr breach), so vol model improvements don't currently affect live P&L. Revisit when Propr account is reinstated.
