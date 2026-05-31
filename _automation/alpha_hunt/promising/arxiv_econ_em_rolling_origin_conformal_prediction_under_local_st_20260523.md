# Rolling-Origin Conformal Prediction under Local Stationarity and Weak Dependence

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.08422v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 960449911f312d54de5b5e94c5ae3268

## Summary
Rolling-origin conformal prediction calibrates prediction interval width against the m most recent pseudo-out-of-sample forecast errors, adapting dynamically to serial dependence, volatility clustering, and distributional drift. The method provides finite-sample marginal coverage guarantees under local stationarity and alpha-mixing. The optimal calibration window is shown to be m* ∝ T^{2β/(2β+1)}, and an oracle inequality formalizes a rolling cross-validation window selector. Validation on six real series and 93 M4 competition series shows rolling-origin calibration outperforms full-history calibration in 86% of comparisons with a median 12.3% Winkler score improvement.

## Why it might be useful
The rolling-origin framework solves the same problem that CLAUDE.md's expanding walk-forward addresses: non-stationarity invalidates full-history calibration. The connection to Algo_claude is twofold. First, Strategy C (NQ ORB, 9 WF folds, 7/9 pass): if the NQ 1-min data exhibits distributional drift (as is likely post-2022 market structure changes), a rolling calibration window for the WF folds would produce more honest OOS estimates than the current fixed-history expanding window. Second, the trailing_dd_simulator.py used for Tradeify propfirm Monte Carlo (L22) generates trade P&L distributions — if those distributions are non-stationary (L21 caution: backtest SR >2× category range requires audit), rolling conformal intervals would bound the deployment risk more tightly than the Gaussian generator. The 86% improvement finding from M4 data is a quantitative backing for upgrading the WF calibration approach.

## Extracted content
The authors report: rolling-origin calibration outperforms full-history calibration in "86% of comparisons" with "median Winkler improvement 12.3%", and maintains coverage within "±2% of the 90% target at short and medium horizons." The optimal window m* ∝ T^{2β/(2β+1)} with coverage-error rate O(T^{-β/(2β+1)}).

## Action proposed
TEST_LATER — Implement rolling-origin calibration for Strategy C's WF fold IC distribution before paper trading. Add an adaptive window selector to the WF analysis notebook in `Futures/research/active/nq_intraday/analysis/`. 1-day effort; directly improves WF honesty claim before Tradeify deployment.
