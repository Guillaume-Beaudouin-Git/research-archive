# Split-Session Cluster GARCH for Overnight and Intraday Returns

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.03669v1
**Captured**: 2026-07-07 03:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 0ce73b02844f1ae5c81f4d626d18e082

## Summary

The paper splits daily equity returns into overnight and intraday components and models each with its own tail-thickness parameter inside a multivariate GARCH framework, rather than assuming one common heavy-tailed distribution for the whole day. It further lets tail behavior vary by economic sector and imposes a block structure on the correlation matrix to keep the model tractable at scale. Tested on 6-asset and 100-asset US equity universes, the session-specific tail model fits meaningfully better than a single shared-tail specification, and the improvement from sector-level tail splitting shows up mostly in the overnight leg. At the 100-asset scale, allowing tail heterogeneity per asset also improves out-of-sample likelihood and global minimum-variance portfolio performance.

## Why it might be useful

This is a direct hit on two methodology axes: daily vol targeting (CLAUDE.md mandatory rule) and the overnight/intraday split that is structurally embedded in Strategy C's NQ ORB signal (gap filter <1.2%, computed off the overnight session, feeds into the $400 SL sizing). The paper's core finding — that overnight tail risk behaves differently from intraday tail risk and needs its own parameter — is exactly the kind of thing that would justify (or refute) treating gap magnitude as a separate vol regime rather than folding it into the same realized-vol estimator used for Strategy A's 28-bar window. It also speaks to the Commodities XS cross-sectional research (`Commodities/research/active/xs_basis_tsmom/`, 24 continuous contracts, still in Phase A data-fetch): a block-structured, sector-clustered covariance matrix is a cheap upgrade over a naive sample covariance once that pipeline reaches portfolio construction, and matches the "N≥30 instruments" cross-sectional discipline already required by CLAUDE.md lesson 6.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt beyond the qualitative fit comparison (session-specific > shared-tail; sector splitting gains concentrated in overnight leg). Full paper needed for the actual likelihood/backtest numbers and the GARCH parameterization.

## Action proposed

REFERENCE

Interesting risk-modeling background but no direct signal or immediate strategy change — Strategy C's propfirm vehicle is cancelled (2026-06-10) so refining its gap filter isn't a live priority, and Commodities XS hasn't reached the portfolio-construction stage yet. Revisit when Commodities XS clears Phase A.
