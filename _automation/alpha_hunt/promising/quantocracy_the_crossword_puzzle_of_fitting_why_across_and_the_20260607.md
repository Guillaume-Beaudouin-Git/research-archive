# Portfolio Fitting Order Matters: Why "Across Then Down" Beats "Down Then Across"

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=qSZoWWW7bW&source=feedburner
**Captured**: 2026-06-07 06:04 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 8e651225469902d36717cb181e7e1ed6

## Summary
Part of a planned series on backtesting by the Investment Idiocy blog (Rob Carver), this post uses the analogy of solving a crossword puzzle to argue that parameter fitting should proceed "across" instruments before fitting "down" through time — not the reverse. The core claim is that fitting across many instruments before time-series fitting reduces the degrees of freedom consumed per parameter and produces more robust estimates. The post frames this as the opening argument for a forthcoming book on backtesting methodology, suggesting it will cover systematic procedures for avoiding in-sample bias in multi-asset optimization contexts.

## Why it might be useful
This is directly relevant to the walk-forward discipline in CLAUDE.md (≥5 folds, expanding window). The "across then down" argument maps onto the cross-sectional-before-time-series fitting order that would apply to any future cross-sectional strategy (e.g., Strategy D's regime filter calibration, or the Commodities XS Basis+TSMOM phase under `Commodities/research/active/xs_basis_tsmom/`). More concretely: if the series covers how to split in-sample from out-of-sample when fitting both asset-level and portfolio-level parameters, it could inform the parameter budget for Strategy D — currently at 0/3 modifications consumed but entering a joint D3+D5 portfolio combination phase where fitting order will matter. Also cross-checks the archived multi-asset TSMOM failure (Sharpe 0.21 corrected): that strategy used a single expansion fold — this post may explain structurally why cross-sectional fitting first would not have saved it given α_t=-1.31.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

The post is methodological background for backtesting discipline. No immediate test path, but worth reading before embarking on the D3+D5 joint portfolio fitting phase, where fitting order (cross-asset first vs time-series first) will directly affect the parameter count and DSR adjustment.
