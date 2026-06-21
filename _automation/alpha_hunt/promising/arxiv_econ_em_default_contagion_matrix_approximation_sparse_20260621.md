# Default Contagion and Systemic Risk Control in Sparse Financial Networks

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.24833
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: b33e035b9d98e9909a060f5bfffca2ec

## Summary
This paper develops a multi-population McKean-Vlasov model for distance-to-default dynamics in sparse financial networks, incorporating common noise, bounded state-dependent killing, loss feedback, and regulatory intervention. The second contribution characterizes when a sparse interconnection matrix can be approximated by a dense one without changing tail-risk behavior—directly relevant to stress testing with partial network information. The framework bridges systemic risk modeling and stochastic control, enabling the design of regulatory interventions that prevent cascade failures in sparse networks.

## Why it might be useful
The sparse-vs-dense approximation result is indirectly relevant to the reverse stress testing paper (id=2606.09274) applied to the A+B portfolio: if the stress scenario reconstruction assumes dense cross-asset dependence when the actual dependence structure is sparse (particularly relevant for HMSTR vs. BTC/ETH), the stress scenarios may be systematically biased. For the Commodities XS strategy (`Commodities/research/active/xs_basis_tsmom/`), where 24 contracts have heterogeneous liquidity and correlation structure, the McKean-Vlasov limit with sparse exposures is more realistic than a dense correlation matrix—particularly for the agricultural vs. energy sub-clusters which have structurally different co-movement patterns. However, this is a systemic risk paper designed for banking regulation rather than trading strategy design.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Systemic risk modeling paper for banking networks; no direct strategy test path. Methodology for sparse network approximation is theoretically relevant to multi-asset portfolio construction but too far from current priorities.
