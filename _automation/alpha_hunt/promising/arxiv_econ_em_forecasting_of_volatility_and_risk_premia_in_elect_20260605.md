# Forecasting of Volatility and Risk Premia in Electricity Markets via Matrix-HAR Models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.05991v1
**Captured**: 2026-06-05 08:02 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 9bb7daf90d6f766c37becfea0367b356

## Summary
The paper proposes a matrix-valued HAR (Heterogeneous Autoregressive) model to forecast realized covariance matrices in electricity markets. Unlike scalar volatility models, this captures the full second-moment structure across multiple price series simultaneously, using daily, weekly, and monthly realized covariation lags in a parsimonious specification. One-week-ahead forecasting tests show that incorporating longer historical horizons and renewable generation data adds meaningful predictive power beyond short-memory models. The key applied finding: variance forecasts from the matrix-HAR model yield substantially improved predictions of spread risk premia in electricity forward markets, outperforming backward-looking volatility baselines.

## Why it might be useful
The matrix-HAR approach is a direct methodology candidate for improving Strategy A (TSMOM v3) vol targeting, which currently uses a fixed 28-bar rolling window of log returns with no lag-structure. A univariate HAR(1,5,22) specification — regressing daily realized vol on its 1-day, 5-day, and 22-day moving averages — is a low-cost extension testable on BTC/ETH/SOL with existing Binance daily data. Strategy A is currently frozen (Propr breach), but this would be worth benchmarking before any reactivation or pivot (e.g., Apex alternative referenced in PropFirms/comparison.md). The variance→risk-premia forecasting link is also directly applicable to the active Commodities xs_basis_tsmom research (`Commodities/research/active/xs_basis_tsmom/`): the basis signal includes a forward risk premium component, and improved vol forecasts could sharpen basis signal scaling. Note that HAR coefficient estimates require HAC standard errors (Newey-West lag-6, already mandatory in the toolkit) due to serial correlation in realized variance.

## Extracted content
No code in the excerpt. Core model structure implied by description:

**Matrix-HAR specification (scalar analogy):**
```
RV_t = β0 + β1·RV_{t-1} + β2·RV_{t-1:5}^(w) + β3·RV_{t-1:22}^(m) + ε_t
```
where `RV_{t-1:k}^(*)` denotes the k-period average of realized variance. In the paper, each scalar term is replaced by a matrix-valued realized covariance, enabling multivariate forecasting.

**Claim (paraphrased):** The authors report that adding renewable generation regressors and longer lags produces "substantially improved forecasts of spread risk premia compared to standard methods relying on backward looking volatility." No specific Sharpe or RMSE improvement numbers are given in the abstract.

## Action proposed
TEST_LATER

The HAR vol model improvement is genuinely applicable to Strategy A and the Commodities research, but Strategy A is frozen and Commodities Phase A (data fetch + roll validation) is not yet complete. Revisit when: (a) Strategy A pivot to Apex is evaluated, or (b) Commodities xs_basis_tsmom reaches Phase B. Implementation cost ≈ 0.5 day; all data available from Binance daily klines. Specific file to modify if executed: `strategies/tsmom_v2_propfirm/signal.py` (vol_28d computation at line 13).
