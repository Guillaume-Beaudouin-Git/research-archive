# ReSGA: A Large Retrieval-Enhanced Autoencoder for VaR and Expected Shortfall

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.04576
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 2e42e98254ad6c69487b5d6cc2794524

## Summary
ReSGA (Retrieval-Enhanced Self-Grouping Autoencoder) is a large neural model for estimating Value-at-Risk and Expected Shortfall, using cross-sectional and temporal dependencies across many assets simultaneously. The model uses a retrieval mechanism to identify similar historical episodes and a self-grouping autoencoder to capture latent risk factors. The paper positions ReSGA as an alternative to standard GARCH-family and historical simulation approaches, exploiting "the rich cross-sectional dependence and long-term temporal dynamics" of a large asset universe.

## Why it might be useful
The `Portfolio/risk/propfirm_canonical.py` uses FTMO 5/10 parametric VaR for propfirm pass simulation. A cross-sectional ES estimator like ReSGA would be relevant if the propfirm simulation is upgraded from parametric to empirical tail estimation. However, implementing a large neural model for this purpose is disproportionate to the current book size (A+B, 3 assets). More relevantly, the sector_hothand_propfirm research uses MDD metrics — a ES-based risk measure could replace the MDD gate for propfirm compliance testing. But the t_HAC alpha=10.38 issue in sector_hothand must be resolved first. File as future reference for portfolio-level tail risk estimation.

## Extracted content
ReSGA = "Retrieval-Enhanced Self-Grouping Autoencoder." Designed for VaR + ES estimation. Uses "cross-sectional dependence and long-term temporal dynamics of assets." Positioned as alternative to GARCH-family models.

## Action proposed
REFERENCE

Not actionable at current book size (3 assets, simple parametric VaR sufficient). Revisit if the book expands to N≥10 instruments or if propfirm simulation is upgraded to empirical tail estimation. Cross-reference with `Portfolio/risk/trailing_dd_simulator.py` for current VaR implementation.
