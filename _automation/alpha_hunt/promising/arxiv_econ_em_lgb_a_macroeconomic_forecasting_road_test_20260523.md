# LGB+: A Hybrid Linear-Tree Boosting Algorithm for Macroeconomic Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.09740v1
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[macro_trading], L2_OK
**Hash**: 9437dc082e2dfae29663266728a68759

## Summary
LGB+ is a gradient boosting variant that evaluates both a tree split and a linear correction at each boosting step, selecting the winner against out-of-bag data. The simpler LGB^A+ alternates on a fixed schedule: tree updates followed by a greedy linear correction. The motivation is that standard tree-based boosters are wasteful in small samples with predominantly linear dynamics — a common situation in macro forecasting. On quarterly US macroeconomic data, LGB+ shows gains over the Stock-Watson factor model for targets with pronounced autoregressive dynamics or mixed linear/nonlinear signals. Forecasts decompose naturally into linear and nonlinear contributions, aiding interpretability.

## Why it might be useful
The `macro_trading` L1 match reflects the macro forecasting application; the algorithm itself could be used in any small-to-medium-sample time series context. For Algo_claude, the most concrete application is the active Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`): the monthly cross-sectional IC scan uses ~24 contracts × 240 months, a dataset size where LGB+'s efficiency in small samples matters. A linear-tree ensemble predicting monthly commodity returns from basis and momentum features could improve on simple OLS IC estimation. However, Phase A (data fetch + roll validation) is not yet complete, making this premature. No fit to active NQ strategies (daily data, adequate sample size for pure tree methods).

## Extracted content
No code in excerpt. The paper describes LGB+ as "evaluating a tree and a linear candidate at each step against out-of-bag data; only the winner advances." LGB^A+ "alternates on a fixed schedule: a block of tree updates, then a greedy linear correction." R package not mentioned; Python implementation status unclear.

## Action proposed
REFERENCE — Interesting for future Commodities XS Phase B signal construction. Not applicable until Phase A (data + roll validation) is complete. Low priority relative to active NQ research.
