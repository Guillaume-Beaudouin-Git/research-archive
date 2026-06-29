# Systematic FX Trading via Regression Learning with Sequential Transaction Cost Analysis

**Source**: quantocracy (via Macrosynergy)
**URL**: https://quantocracy.com/redirect.php?key=E9YWRT0VBz&source=feedburner
**Captured**: 2026-06-29 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 860bedd376713870134ad21de6d94edb

## Summary
This article presents a systematic FX approach using regression-based statistical learning to combine multiple trading factors into a composite signal. The key methodological contribution appears to be sequential learning — updating the regression coefficients as new data arrives rather than re-estimating on a fixed window — paired with explicit transaction cost analysis at the signal aggregation stage. The framework positions itself as transparent and interpretable relative to black-box ML approaches.

## Why it might be useful
Per L43 (retail FX intraday-flat is cost-dead, sub-bps gross vs ~2-5 bps CFD RT) and the FX intraday deepdive closure (`Forex/research/active/fx_intraday_deepdive/`), the trading signal proposed here is unlikely to survive retail cost tiers. However, the methodological contribution — sequential regression for factor combination with online cost adjustment — is applicable to non-FX contexts. Specifically, for the `_automation/feasibility/` pipeline, the sequential learning approach could improve how the generic feasibility handler combines L0/L1/L2 filter scores into a composite priority signal, without requiring a full refit on each new item batch. The transaction cost integration at the signal level (rather than post-hoc) is also the correct approach per L33/L33b.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — FX trading edge unlikely to survive cost gate (L43). The sequential regression methodology is a minor reference for pipeline tooling, not for a new trading strategy.
