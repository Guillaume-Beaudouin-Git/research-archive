# Derivative-Informed Operator Learning for Finance: On-the-Fly Greeks and Risk Management

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.05900
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology, macro_trading], L2_OK
**Hash**: 422d398478f1ea950b8e56c2c99af547

## Summary
This paper formulates a framework where a learned neural operator simultaneously computes prices and their derivatives (Greeks, curve sensitivities, credit-spread sensitivities, XVA) with rigorous error bounds. The key insight is that downstream tasks (hedging, portfolio optimization, XVA) depend on the derivatives of prices, not just prices themselves — so a surrogate that only reproduces prices fails on hedge ratios. The derivative-informed operator achieves lower hedging error than price-only surrogates, and the on-the-fly Greeks computation enables real-time risk management without finite-difference approximation overhead.

## Why it might be useful
The Voie B FTMO research (`Futures/research/active/voie_b_ftmo/`) involves MT5-based execution on CFD instruments. If FTMO's CFD pricing model is modeled, computing Greeks on-the-fly (using this framework's operator approach) would be needed for delta hedging. However, the current Voie B research is about MT5 EA signal logic, not options pricing. This paper is relevant only if Voie B evolves into an options-on-CFD strategy, which is not the current direction. File as a methodological reference for derivative-heavy risk management.

## Extracted content
"Financial decision systems require fast surrogate models for pricing, calibration, hedging, XVA, stress testing, and portfolio optimization." "Downstream tasks depend as much on derivatives: deltas, vegas, curve and credit-spread sensitivities." Neural operator achieves "lower hedging error than price-only surrogates." On-the-fly Greeks without finite-difference approximation.

## Action proposed
REFERENCE

Not actionable for current research directions (A/B/D are non-options strategies). File as reference if Voie B or future strategies involve option Greeks. Lower priority given FTMO's confirmed non-support for CME options (L22c).
