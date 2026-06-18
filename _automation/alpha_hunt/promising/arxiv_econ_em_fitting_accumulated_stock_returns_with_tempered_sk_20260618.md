# Fitting Accumulated Stock Returns with Tempered Skew t-Distribution

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.19318v1
**Captured**: 2026-06-18 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 8dd0482bc3f33d039b40530d9f94e47a

## Summary
This paper fits historical S&P 500 multi-day return distributions (accumulation windows 20–120 days) and documents that power-law tails visibly temper as the holding period grows — the distribution converges toward something with finite moments rather than diverging Pareto behavior. The authors model this via a "capped Inverse Gamma" stationary distribution for stochastic volatility, which generates a "tempered Student-t" for returns, further augmented by a Jones-Faddy asymmetry mechanism to produce a "tempered Skew-t." The resulting fits capture the empirically observed positive mean (drift), negative skew (asymmetric drawdown risk), and the near-linear variance scaling in the number of accumulation days.

## Why it might be useful
This connects directly to two active problems. First: `Portfolio/risk/trailing_dd_simulator.py` for FTMO propfirm challenges models the daily-return distribution to estimate pass probability against a symmetric trailing drawdown barrier. The current simulator uses a calibrated trade-based generator. The tempered Skew-t provides a parametric alternative that explicitly models the negative-skew / finite-tail regime that FTMO's 5% daily + 10% total barrier structure exploits — L24 identifies that lumpy strategies (positive skew, low WR) have a structural 44% ceiling; a high-frequency mean-reversion strategy with negative daily skew would face a different barrier-crossing profile that the tempered Skew-t captures better than a Gaussian. Second: L39 (daily vs monthly skew dissociation) is empirically documented here — the authors find negative skew is persistent across 20–120 day windows, which validates running both the daily-skew (FTMO daily barrier) and monthly-skew (personal book) checks as distinct constraints. To test: fit a tempered Skew-t to Strategy A's or B's daily return series and compare FTMO pass probability estimates against the existing trade-based generator.

## Extracted content
The authors report the following (attributed claims from abstract):
- "With the increase of the number of days of accumulation, we observe clear tempering of power-law tails toward a seemingly finite value."
- "This distribution provides rather good fits to the distributions of accumulated multi-day S&P500 returns, which exhibit symmetry breaking between gains and losses — as reflected by positive mean and negative skew."
- "Tempered Skew-t fits are also consistent with near perfect linear dependence on the number of days of accumulation of the mean values and, even more so, of the variances (mean squared realized volatility) of the distributions."

No code in excerpt.

## Action proposed
TEST_LATER — Fit the tempered Skew-t to Strategy A/B daily PnL series and re-run `trailing_dd_simulator.py` with the parametric distribution to get a second opinion on FTMO pass probability. Requires reading the full paper for the parameter-estimation procedure (no closed-form MLE visible in abstract). Estimate: 0.5 day once paper is available.
