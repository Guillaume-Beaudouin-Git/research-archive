# Monotonicity and Rigidity in Gaussian Inverse Regression: The One-Period Kyle Model Has a Unique Equilibrium

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.23585v2
**Captured**: 2026-08-04 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b6c114fc355b92939ca0d358f39c0383

## Summary
Proves, using a purely probabilistic argument (an exchangeable-pair coupling from the market maker's posterior), that the classical one-period Kyle (1985) insider-trading model has a unique equilibrium: the informed trader's affine (linear-in-signal) order-flow strategy and the market maker's linear pricing rule are the only best-response pair, with no smoothness assumption needed beyond Borel measurability. Settles a long-standing open question in market microstructure theory, previously only established under extra regularity conditions by Boulatov-Kyle-Livdan and McLennan-Monteiro-Tourky.

## Why it might be useful
The Kyle (1985) model is the canonical theoretical foundation for market-impact/adverse-selection cost in execution research — this uniqueness result doesn't change any number the project uses, but it formally justifies treating "linear price impact from order flow" as the right functional form rather than one candidate among several, directly relevant to Strategy C's execution-cost modeling (L19's asymmetric slippage stress-testing, sizing_analysis.py) and any future work estimating market impact for the smaller-cap perps in Strategy B's VIABLE_ASSETS universe (thinner order books sit closer to a literal Kyle-model setting than large-cap BTC/ETH). Second link: pure theory with nothing to backtest, filed as REFERENCE rather than TEST_LATER — it justifies an already-used functional form, it does not add a new one.

## Extracted content
Formula (paraphrased): the paper's central claim is phi(v) is the maximizer over x of x*v - x*F(x) for every real v if and only if phi is the identity function, where F(x) is the Gaussian-smoothed inverse regression of the best-response condition — this is the Kyle-equilibrium best-response condition. No numeric/Sharpe claims (pure math).

## Action proposed
REFERENCE — note this arXiv v2 (retitled "Monotonicity and Rigidity...") and ba793ad4fa31b5e1da1044e6f0c148ab (arXiv v1, "The One-Period Kyle (1985) Model Has a Unique Equilibrium", captured 2026-07-28) are the same paper/proof under two titles; read either, not both.
