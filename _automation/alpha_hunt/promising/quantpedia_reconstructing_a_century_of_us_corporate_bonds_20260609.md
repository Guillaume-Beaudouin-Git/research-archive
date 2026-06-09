# Reconstructing a Century of U.S. Corporate Bond Returns (Ghaderi et al., 2026)

**Source**: quantpedia
**URL**: https://quantpedia.com/reconstructing-a-century-of-u-s-corporate-bonds/
**Captured**: 2026-06-09 16:04 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 32159d9371a5d426a1e225e6fa7c611b

## Summary
Ghaderi, Plante, Roussanov, and Seo (2026) extend the empirical coverage of U.S. corporate bond markets back to 1895 by hand-digitizing monthly price quotes from the Commercial and Financial Chronicle, S&P Bond Guide, and Mergent/Moody's Bond Record. The resulting 127-year panel dwarfs the standard post-2002 TRACE dataset that most credit-risk and return-predictability research has relied on. The long-run sample covers multiple credit-cycle regimes — pre-Depression, wartime, stagflation, post-GFC — that are structurally absent from modern fixed-income datasets. The QuantPedia page is a teaser; no factor loadings, Sharpe ratios, or predictability estimates are disclosed in the excerpt.

## Why it might be useful
The primary connection is **ZN Baltussen (active research, CLAUDE.md)**: that branch is studying bond futures momentum on the 10Y Treasury. Although ZN is a government bond and this paper covers corporates, the core hypothesis is the same — whether momentum/carry premia in fixed income are robust across long and diverse macro regimes, or are TRACE-era artifacts. A 127-year corporate bond sample that shows persistent or collapsing momentum across the 1929 crash, WWII, 1970s inflation, and GFC would directly update the prior on ZN momentum viability. If the paper finds that bond momentum is regime-conditional rather than secular, that is a signal to add a macro-regime filter in ZN Baltussen before committing to a full walk-forward.

Methodologically, the item is parallel to `quantpedia_an_index_of_commodity_futures_returns_since_1871` (already in promising/): both use hand-collected historical panels to test whether factor premia documented on short samples survive over a century. That commodity item was flagged TEST_LATER for Commodities XS Basis+TSMOM; the same reasoning applies here for ZN Baltussen.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — No test feasible with locally available data (the 1895-2022 corporate bond panel is not in the local stack). Read the full Ghaderi et al. (2026) paper (check SSRN or the authors' pages at Wharton/Fed) when ZN Baltussen enters the hypothesis-validation phase. The key questions to pull from it: (a) does cross-sectional momentum IC remain positive post-WWII and post-GFC? (b) is the credit spread (basis) a stronger predictor than momentum in any regime? Answers directly inform whether ZN Baltussen needs a regime filter before walk-forward.
