# Specification Testing for Dyadic Regression Models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.26366v1
**Captured**: 2026-07-30 01:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: f525aeb439c1699c3c2e211bb9047fa7

## Summary
Develops omnibus specification tests for linear models on undirected dyadic (pairwise) data, handling the shared-node dependence structure by reducing the dyadic process to latent first-order node projections. Shows a naive node-multiplier bootstrap double-counts variation when dyads are actually independent, and proposes a corrected Gaussian bootstrap valid under both dependence regimes; the resulting Kolmogorov-Smirnov/Cramer-von Mises tests are applied to a law-firm social network, rejecting simple additive specifications but finding no misspecification once an economically relevant interaction term is included.

## Why it might be useful
Weak direct tie — no Algo_claude strategy currently models pairwise (dyadic) relationships between instruments in a way this would apply to (e.g., a cointegrated-pair or correlation-network model). The one plausible future link: if a pairs-trading or correlation-network research thread is ever opened (none currently active; the closest historical attempt is the archived CIP-EOQ FX pair work), a model built on pairwise instrument relationships would have exactly the shared-node dependence structure this paper addresses, and the corrected-bootstrap warning (naive bootstrap double-counts variation under independence) would directly apply.

## Extracted content
No code/formulas, no finance-specific numeric claims (applied to a law-firm social network).

## Action proposed
REFERENCE.
