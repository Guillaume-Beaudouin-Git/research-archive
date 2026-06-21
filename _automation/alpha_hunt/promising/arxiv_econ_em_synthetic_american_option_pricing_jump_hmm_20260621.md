# Synthetic Option Pricing via Jump-HMM-Driven Heston to Break the IV Circularity

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.13998
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 2f9cad0a306fbc8894777cb608b534b4

## Summary
Generating synthetic options data for ML training requires implied volatility as an input, yet IV is derived from observed option prices—a circular dependency. This paper breaks the circularity by constructing a pipeline where IV emerges as an output: a Jump Hidden Markov Model first generates multi-asset price paths with realistic regime-switching and cross-asset correlation, then drives a Heston stochastic vol model that outputs option prices and IV. The resulting synthetic data are reported to be statistically indistinguishable from empirical data across several tests. The approach enables generation of unlimited realistic option surfaces for machine-learning and risk-management applications without requiring live market data.

## Why it might be useful
The Jump-HMM component of this pipeline is directly applicable to the FinStressTS diagnostic framework (id=2606.03184 in this batch) and to stress-testing Strategy A's vol estimator under regime-switching conditions. More concretely, if the sector_hothand strategy in `Equities/research/active/sector_hothand_propfirm/` is modified to include an options overlay (e.g., downside protection given MDD -13.3% breaching the FTMO 10% floor), this synthetic pipeline would provide training data for calibrating the overlay without requiring paid options data subscriptions. The HMM regime identification component also overlaps with the regime filter currently under study for Strategy D (`Futures/research/active/strategy_d/hypotheses_preregistered.md`).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Primarily useful for options data generation; current strategies do not trade options. The HMM regime component is interesting for Strategy D but that research track has more direct references already.
