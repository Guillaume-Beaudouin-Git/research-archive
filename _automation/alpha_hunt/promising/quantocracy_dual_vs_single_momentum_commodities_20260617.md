# Dual vs. Single Momentum in Commodities: Enhancing Risk-Adjusted Returns

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=vsHJKWDSH1&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: fac8c4a30e00ab1996f9790d7f3433cb

## Summary
The paper compares single momentum (cross-sectional relative ranking) against dual momentum (combining absolute time-series momentum with cross-sectional relative momentum, à la Antonacci 2014) applied to commodity futures. The argument is that dual momentum improves risk-adjusted returns by adding an absolute filter: assets with negative time-series momentum are excluded even if they rank well cross-sectionally, preventing the strategy from holding losing positions just because they're "least bad." Commodities are the test bed, likely using continuous front-month contracts with monthly rebalancing.

## Why it might be useful
This is a direct hit on the active research: Commodities XS (`Commodities/research/active/xs_basis_tsmom/`) is testing S_TSMOM (Moskowitz 2012) and S_BASIS (Erb-Harvey 2006) on 24 continuous contracts with monthly CS IC scan. The current design uses cross-sectional momentum only (S_TSMOM). Adding a dual-momentum absolute filter — exclude any contract with negative 12-month return regardless of CS rank — is a one-line modification to the signal construction that could meaningfully reduce max drawdown (excluded the worst momentum phases of commodity cycles like 2014-2016 and 2020 oil crash). The data required (yfinance =F tickers, continuous front-month) is already identified in CLAUDE.md. Estimated implementation: < 4 hours to add the absolute-momentum filter as a variant inside xs_basis_tsmom, run walk-forward comparison, and report the Sharpe/DD delta. Cost gate for commodities is 0.015% RT (CLAUDE.md), much lower than crypto/equities, making the signal economically viable at much lower IC.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_NOW

The Commodities XS research is active and Phase A (data fetch + roll validation) is not yet complete. Adding the dual-momentum absolute filter as a design variant now — before running the full WF — costs zero extra tests if pre-registered alongside S_TSMOM and S_BASIS. Pre-register: "H_dual: |ret_12m| > 0 filter applied before CS ranking; expected direction = positive Sharpe delta vs S_TSMOM." This is the lowest-cost moment to add this variant.
