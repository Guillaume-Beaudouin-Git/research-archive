# Trend-Conditioned Volatility and Correlation Forecasting for Financial Markets

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.20145
**Captured**: 2026-06-20 10:02 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 74b2ad8cb2e7def414f1453a261316a2

## Summary

Safari & Schmidhuber show that both realized volatility and cross-asset correlations can be forecast from current trend strength using simple quadratic polynomial functions. The empirical pattern: during strong up- or down-trends, volatility and correlations tend to increase day-over-day, with the effect particularly pronounced in down-trends. This quadratic correction refines standard mean-reversion volatility models (e.g., GARCH-family) by conditioning on market state. The authors also argue the findings support a "lattice gas near critical point" model of financial markets, where trending regimes increase systemic connectedness. Experiments appear to cover multiple instruments (paper is empirical across several financial markets).

## Why it might be useful

Strategy A (TSMOM v3) uses a 28-bar rolling log-return standard deviation for vol targeting with sqrt(365) annualization. The paper's finding — that vol is elevated during strong trends — is directly relevant to the vol estimator in `strategies/tsmom_v2_propfirm/signal.py`. However, Strategy A is FROZEN (2026-05-30), so this is not actionable there. The real value is for Strategy D design: any new cross-sectional or time-series momentum strategy should condition its vol target on trend strength, not just use a trailing window. Concretely, if the signal (e.g., cumret / vol) is large (i.e., strong trend), a trend-conditioned vol target would shrink position size relative to a naive trailing estimator — a natural way to reduce drawdown in trending regimes that are also high-volatility regimes. This is synergistic with the L39 lesson (daily vs. monthly skew dissociation on trend strategies) and with the book-level SR 2.31 computation where MaxDD is "to be measured on ≥60d live B mainnet." If Strategy A ever gets unfrozen, this is a natural low-modification improvement (it counts as 1 of 3 max mods).

## Extracted content

From the abstract:
- "we observe that volatilities and correlations tend to increase day after day in times of strong up- or down-trends. This effect is particularly pronounced in down-trends."
- "It can be accurately quantified by quadratic polynomials of today's trend strengths, which refine common mean-reversion models of volatilities and correlations."
- "Our results improve the prediction of market risk by accounting for market trends."
- Authors also provide: "They also support a recent proposal to model financial markets by a lattice gas near its critical point."

No code in excerpt. Full article needed for the polynomial specification and empirical coefficients.

## Action proposed

TEST_LATER

Implementation requires: (1) read the paper to extract the quadratic polynomial specification; (2) apply to crypto daily data in `data/raw/` (BTC/ETH/SOL klines already available); (3) compare trend-conditioned vol vs. 28-bar trailing vol against true realized vol for OOS predictive accuracy. Cost: ~1 day of analysis. Not TEST_NOW because Strategy A is frozen and there is no active strategy under development that would directly absorb this improvement right now. Flag for Strategy D design phase.
