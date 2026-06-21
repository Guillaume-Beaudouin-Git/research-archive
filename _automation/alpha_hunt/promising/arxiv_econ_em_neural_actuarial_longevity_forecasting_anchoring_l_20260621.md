# Neural-Actuarial Longevity Forecasting with LSTM Anchored to Li-Lee

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.06438
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 9f22fd27dea07aa399cf7cc7e0c2cefe

## Summary
A hybrid actuarial-ML framework for mortality rate forecasting that anchors hierarchical LSTM networks with a Mean-Bias Correction (MBC) mechanism to a classical Li-Lee multi-population model. The approach selectively outperforms Li-Lee (by 17% in Sweden, 13% in West Germany) while remaining comparable in near-linear regimes (Switzerland, Japan). The governance suite includes SHAP-based influence mapping and a dual uncertainty framework for regulatory capital calibration under SST/Solvency II. The key diagnosis: classical Li-Lee fails when country-specific mortality residuals have unit roots (Sweden, Germany), which the LSTM captures as persistent nonlinear dynamics.

## Why it might be useful
Longevity/mortality forecasting is entirely outside our strategy universe (crypto/equities/futures). The LSTM anchoring methodology is generically interesting — anchoring a neural network to a classical model's structure to improve OOS stability — and this technique could in principle be applied to anchor TSMOM signals to a CAPM prior. However, the mortality context is too distant from financial returns for the specifics to transfer. The "stationarity paradox" finding (unit root in residuals despite mean-reversion assumption) is a methodological warning parallel to the bond index study (`1533e0fc`): always check unit root before applying mean-reversion-based methods.

## Extracted content
"We identify a stationarity paradox where mortality residuals in countries like Sweden and West Germany exhibit persistent unit roots, leading to a systematic mispricing of longevity risk in linear models."

"The framework exhibits selective superiority on out-of-sample validation (2012-2020): it outperforms Li-Lee by 17.40% in Sweden and 12.57% in West Germany."

## Action proposed
REFERENCE

Actuarial longevity forecasting. Not applicable to financial markets strategies. The unit-root warning is a useful methodological note but widely known.
