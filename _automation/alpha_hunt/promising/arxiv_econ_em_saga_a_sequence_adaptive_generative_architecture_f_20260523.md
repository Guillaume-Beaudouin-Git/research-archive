# SAGA: Decoder-Only Transformer for Multi-Horizon Probabilistic Forecasting of Lifetime Earnings

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.19014v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 97bfdd8b3fcf3d74f3fd1e9d7c8e22c5

## Summary
SAGA is a decoder-only transformer architecture for irregular tabular panel sequences (missing observations, variable-length histories), combined with split conformal calibration to produce individual-level prediction intervals with finite-sample marginal coverage guarantees. Trained on 33 years of Swedish longitudinal labor earnings data covering 2.1 million individuals, SAGA reduces CRPS by 31.9% at 10-year horizon and MAE by 37.7% at 20-year horizon relative to the canonical Guvenen-Karahan-Ozkan-Song parametric benchmark. Conformal intervals achieve nominal coverage within 0.4 percentage points marginally and within 2.4 percentage points on worst-case demographic subgroups.

## Why it might be useful
SAGA's application is public policy microsimulation for labor economics, not financial markets. The topic_relevance L1 match reflects that panel sequence forecasting and conformal prediction intervals are methodologically adjacent to walk-forward strategy evaluation. The conformal calibration wrapper — which provides honest coverage guarantees under distributional drift — is the transferable component. In Algo_claude context, applying split conformal intervals to Strategy C's walk-forward Sharpe distribution would produce honest confidence intervals around the 1.52 Sharpe estimate with fewer assumptions than HAC inference. The rolling-origin conformal prediction item (item P3-06) in this run is a more targeted implementation of the same core idea and is more directly actionable.

## Extracted content
The authors claim: SAGA "reduces continuous ranked probability score by 31.9 percent at the ten-year horizon and mean absolute error by 37.7 percent at the twenty-year horizon" relative to the GKOS parametric process. Conformal intervals achieve "nominal coverage to within 0.4 percentage points marginally."

## Action proposed
REFERENCE — Labor economics panel forecasting with no direct path to active strategies. The conformal calibration idea is better pursued via the rolling-origin conformal prediction item (arxiv_econ_em_rolling_origin_conformal_prediction_under_local_st_20260523.md) which is designed specifically for time-series trading forecasts.
