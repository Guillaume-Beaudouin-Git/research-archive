# Quantifying the Risk-Return Tradeoff in Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.09712v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 35d9c8a4c63381dba1eed41ab4459fe0

## Summary
The paper argues that average forecast accuracy — measured by RMSE or MAE — conflates reliable prediction with volatile prediction that happens to average out. The author treats forecast loss differentials relative to a benchmark as a return series and applies finance-style risk metrics: Sharpe ratio, Sortino ratio, Omega ratio, and drawdown-based measures. An "Edge Ratio" is introduced to capture how often a model delivers uniquely informative predictions versus the forecasting frontier. Applied to US macroeconomic forecasting, professional forecasters prove hard to beat on a risk-adjusted basis even when machine learning models dominate on mean accuracy alone, because the professionals rarely produce catastrophic forecast failures.

## Why it might be useful
The risk-adjusted forecast evaluation framework maps directly onto strategy validation in Algo_claude. CLAUDE.md mandates Sharpe (not just return) and MaxDD (not just mean) for strategy gates. This paper applies the same logic one level up: the strategy's own signal accuracy should also be evaluated risk-adjusted, not just on average IC. Concretely, applying the Sortino ratio and drawdown metrics to the per-fold IC distribution in Strategy C's walk-forward (9 folds, 7/9 pass) would reveal whether the 2 failing folds were catastrophic tail events (bad forecast) or minor underperformance. A fold Sharpe below -1.0 on the IC series would flag a fragile signal even if the pass count is 7/9. This complements the Walk Forward Correlation metric from the Tinsley article (item 04) and could be added to the analysis notebooks in `Futures/research/active/nq_intraday/analysis/`.

## Extracted content
The author describes metrics including "Sharpe ratio, Sortino ratio, Omega ratio, and drawdown-based metrics" applied to forecast loss differentials. The "Edge Ratio" captures model uniqueness relative to the forecasting frontier. Specific numeric results from the US macro application are not in the excerpt.

## Action proposed
TEST_LATER — Implement the IC-as-return-series Sortino + drawdown diagnostics on Strategy C's 9-fold walk-forward and Strategy D's future folds. Add to fold analysis notebook alongside existing pass-rate calculation. Half-day effort.
