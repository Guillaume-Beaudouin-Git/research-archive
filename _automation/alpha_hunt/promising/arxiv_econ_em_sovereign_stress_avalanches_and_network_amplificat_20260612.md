# Sovereign Stress Avalanches and Network Contagion in Latin American EM Credit

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.12460v1
**Captured**: 2026-06-12 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 33b1b20c8df128a542e58639db8d681f

## Summary

The paper examines whether sovereign credit stress events in Latin American markets propagate through conditional regional networks or arise primarily from common global shocks. Using J.P. Morgan EMBI spreads for 11 sovereigns over 2007-2026, stress events are defined as positive log-spread innovations above country-specific volatility thresholds, and regional "avalanches" count the number of simultaneously stressed countries in each month. Avalanche sizes follow a heavy-tailed distribution with estimated power-law exponent 1.77, and a reshuffling placebo confirms synchronization far above independent timing (p<0.001). The critical finding: raw-correlation network density rises sharply during large avalanches, but after partial-correlation filtering this amplification disappears — the apparent network effect is entirely explained by shared global risk premia rather than conditional bilateral contagion. Network metrics therefore describe concurrent stress regimes but provide no early-warning signal.

## Why it might be useful

Two concrete links to Algo_claude. First, the archived Network Momentum GMOM strategy (`Multi_Asset/research/archived/network_momentum/`) failed partly because graph density collapsed to 1.0, making all MST edges equivalent and rendering network momentum degenerate. This paper provides the theoretical mechanism: in a common-factor-dominated universe, raw correlations saturate during stress, which is exactly the degenerate case. The verdict is correct but the *why* was previously unlabeled; any future attempt at a network-based cross-sectional strategy must pre-specify partial-correlation (rather than raw-correlation) networks to avoid the same failure mode. Second, the Commodities XS Basis+TSMOM research (`Commodities/research/active/xs_basis_tsmom/`) will eventually need a macro stress regime filter to condition cross-sectional signals. The avalanche synchronization framework here — defining stress regimes by the count of simultaneously breaching assets — is directly adaptable using commodity curve spreads instead of sovereign spreads, and the partial-correlation isolation step maps cleanly onto removing the common commodity demand factor before measuring cross-sectional basis dispersion.

## Extracted content

No code or trading signals in the excerpt. Specific quantitative claims: power-law exponent for avalanche sizes = 1.77; reshuffling placebo p-value < 0.001 for synchronization; network amplification (elevated spectral radius during large avalanches) is fully absorbed by partial-correlation filtering, leaving no residual conditional bilateral propagation signal.

## Action proposed

REFERENCE
