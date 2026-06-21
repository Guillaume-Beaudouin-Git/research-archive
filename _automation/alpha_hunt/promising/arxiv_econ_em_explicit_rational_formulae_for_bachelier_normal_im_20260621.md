# LFK-2026: Fast Rational Formulae for Bachelier Normal Implied Volatility

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.18343
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 6a6541171562be9d85026de55085118c

## Summary
Two explicit non-iterative rational formulae for Bachelier (normal distribution) implied volatility, both based on the LFK-4 branch structure but using absolute forward-strike difference divided by tail time value as the near-the-money variable (simpler than a logarithm). LFK-2026 is accuracy-oriented; LFK-2026C splits the near-the-money branch for faster scalar computation. Both achieve near-machine-precision errors in double precision against the expanded Jäckel reference, with LFK-2026C being faster on current benchmarks.

## Why it might be useful
Bachelier implied vol is relevant for fixed income options (normal distribution assumption is standard for rates) and for NQ futures options where a normal return distribution might be preferred. However, we have no active options strategies, and the archived VRP/options work is closed. This is a computational utility paper (faster IV solver) rather than a trading edge. Not connected to Strategies A/B/C/D.

## Extracted content
"LFK-2026 is the accuracy-oriented formula and approximates reciprocal absolute standardized moneyness directly in the far tail. LFK-2026C keeps the same shifted out-of-the-money rational tail approximation, but splits the near-the-money branch into a very small low-u rational and a mid-range rational."

No code in excerpt; mathematical formulas in full paper.

## Action proposed
REFERENCE

Computational tool for Bachelier IV. No current options strategy to apply it to.
