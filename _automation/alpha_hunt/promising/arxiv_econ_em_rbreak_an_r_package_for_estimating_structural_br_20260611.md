# rbreak — Structural Break Estimation with Linear Restrictions and Regression Trees

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.12261v1
**Captured**: 2026-06-11 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: ae40c16c730689b4bb01b0fc835d7713

## Summary

The `rbreak` R package implements structural break detection for linear regression models subject to general linear restrictions, supporting both within-regime and cross-regime constraint forms. Break-date estimation comes with confidence intervals, and the package provides a restricted sup-F test for the null of no structural change. Monte Carlo critical-value simulation handles non-standard distributions that arise under restrictions. A bootstrap restart procedure guards against convergence to spurious local optima. The package also implements a "linear model tree" — a generalized regression tree where each leaf holds a full regression model rather than a constant, enabling regime-conditional slope estimation.

## Why it might be useful

The core contribution — break detection under linear constraints — is directly relevant to Strategy D's regime-filter design (D3 morning mid-fade, D5 afternoon BB squeeze): both are tested with a regime overlay "under study" per CLAUDE.md, and a formal sup-F structural break test would replace the current ad-hoc regime split with a statistically grounded break date. The linear model tree extension maps onto the slope-heterogeneity question across NQ trading regimes (pre/post-FOMC, macro announcement days — see L42 in the L-registry). For the ZN Baltussen active research thread, bond futures momentum is inherently rate-regime-conditional; a restricted break test with cross-regime constraints directly implements the null "momentum coefficient is constant across rate regimes" vs. the alternative of a structural shift. Concretely, the Python equivalent would be `statsmodels.stats.diagnostic.breaks_cusumolsresid` or the `ruptures` library — neither supports linear restrictions natively, so `rbreak` fills a methodological gap if a restricted-coefficients regime model is ever needed. No direct test today since the project stack is Python-only, but the linear model tree concept should inform how regime filters are parameterized in D3/D5.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

The methodology is sound and the linear-restrictions angle fills a gap not covered by standard Python tools (`ruptures`, `statsmodels` Chow test). No direct implementation path today — the project is Python-only and the immediate D3/D5 work uses simpler regime splits. Revisit if the ZN Baltussen or D strategy regime work reaches a point where restricted coefficient-stability tests are needed.
